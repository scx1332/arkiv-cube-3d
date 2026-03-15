"""Render boxes on a white floor with lighting and ray tracing using Blender."""

import binascii
from dataclasses import dataclass, replace
import os
import struct
import zlib

from .geometry import create_box_geometry, create_floor_geometry, create_box_configs
import bpy


@dataclass(frozen=True)
class RenderParameters:
    """Configurable scene and material settings."""

    box_color: tuple[float, float, float, float] = (0.8, 0.35, 0.0, 1.0)
    box_roughness: float = 0.4
    box_metallic: float = 0.0
    box_specular: float = 0.5
    box_emission_strength: float = 0.0
    floor_roughness: float = 0.5
    world_strength: float = 0.1
    key_light_energy: float = 100.0
    fill_light_energy: float = 4500.0
    rim_light_energy: float = 100.0
    samples: int = 64
    resolution_x: int = 400
    resolution_y: int = 400


DEFAULT_RENDER_PARAMETERS = RenderParameters()
PREVIEW_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, samples=16, resolution_x=400, resolution_y=400)
FULL_RES_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, resolution_x=2000, resolution_y=2000)
HEIGHTMAP_IMAGE_SIZE = 23
HEIGHTMAP_BOX_SIZE = 0.55
SOFT_BORDER_COLOR = (0.9, 0.9, 0.9, 1.0)
SOFT_BORDER_RATIO = 0.03
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def is_bpy_available():
    """Return whether Blender's Python API is available."""
    return bpy is not None


def require_bpy():
    """Return the bpy module or raise a helpful error."""
    if bpy is None:
        raise RuntimeError(
            "bpy is required to render. Run this project through Blender or install the bpy package first."
        )
    return bpy


def set_material_input(bsdf, names, value):
    """Set a Principled BSDF input using the first available input name."""
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return


def remove_unused_data_blocks(collection):
    """Remove orphaned Blender data blocks from a collection."""
    for item in tuple(collection):
        if item.users == 0:
            collection.remove(item)


def remove_data_block(collection, block):
    """Remove a Blender data block, tolerating simple test doubles."""
    try:
        collection.remove(block, do_unlink=True)
    except TypeError:
        collection.remove(block)


def clear_scene():
    """Remove all objects and data directly without relying on UI context."""
    blender = require_bpy()

    # 1. Delete all objects from the scene directly when possible.
    objects = getattr(blender.data, "objects", None)
    use_orphan_cleanup = False
    if objects is not None:
        for obj in list(objects):
            remove_data_block(objects, obj)
    elif hasattr(blender, "ops") and hasattr(blender.ops, "object"):
        blender.ops.object.select_all(action="SELECT")
        blender.ops.object.delete(use_global=False)
        use_orphan_cleanup = True

    # 2. Nuke the underlying data blocks since we rebuild them every run
    collections_to_clear = [
        blender.data.meshes,
        blender.data.materials,
        blender.data.lights,
        blender.data.cameras,
    ]

    for collection in collections_to_clear:
        if use_orphan_cleanup:
            remove_unused_data_blocks(collection)
            continue

        for block in list(collection):
            remove_data_block(collection, block)


def create_floor(params=DEFAULT_RENDER_PARAMETERS):
    """Create a large white floor plane without relying on UI context."""
    blender = require_bpy()

    # 1. Define the geometry for a 100x100 plane manually
    verts, faces = create_floor_geometry()

    # 2. Create the mesh and object directly in Blender's data blocks
    mesh = blender.data.meshes.new(name="FloorMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update() # Important: updates the mesh geometry data

    floor = blender.data.objects.new(name="Floor", object_data=mesh)

    # 3. Link the object to the scene collection so it actually appears
    # (scene.collection is safer than context in background processes,
    # though context.scene usually still works if initialized properly)
    blender.context.scene.collection.objects.link(floor)

    # 4. Material Setup
    mat = blender.data.materials.new(name="FloorMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    if bsdf: # Always safe to check if the node exists
        bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        set_material_input(bsdf, ["Roughness"], params.floor_roughness)

    floor.data.materials.append(mat)

    return floor


def create_height_box_geometry(size, height):
    """Return vertices and faces for a box that starts at z=0 and extends to the given height."""
    radius = size / 2.0
    verts = [
        (-radius, -radius, 0.0),
        (radius, -radius, 0.0),
        (radius, radius, 0.0),
        (-radius, radius, 0.0),
        (-radius, -radius, height),
        (radius, -radius, height),
        (radius, radius, height),
        (-radius, radius, height),
    ]
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return verts, faces


def load_image_heightmap(image_path):
    """Load a fixed 23x23 image through Blender and return pixel colors with height intensities."""
    blender = require_bpy()
    resolved_path = Path(image_path).expanduser().resolve()
    image = blender.data.images.load(filepath=str(resolved_path))

    try:
        width, height = (int(image.size[0]), int(image.size[1]))

        pixels = list(image.pixels[:])
        pixel_grid = []
        for row_index in range(height):
            row = []
            for column_index in range(width):
                pixel_index = (row_index * width + column_index) * 4
                red, green, blue, alpha = pixels[pixel_index : pixel_index + 4]
                brightness = (red + green + blue) / 3.0
                row.append(((red, green, blue, alpha), 1.0 - brightness))
            pixel_grid.append(row)
        return pixel_grid
    finally:
        remove_data_block(blender.data.images, image)


def _paeth_predictor(left, up, up_left):
    """Return the Paeth predictor for PNG filter reconstruction."""
    base = left + up - up_left
    left_distance = abs(base - left)
    up_distance = abs(base - up)
    up_left_distance = abs(base - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def _read_png_rgba(path):
    """Read a non-interlaced 8-bit PNG into RGBA rows."""
    content = Path(path).read_bytes()
    if not content.startswith(PNG_SIGNATURE):
        raise ValueError("Only PNG render outputs are supported for postprocessing.")

    width = height = bit_depth = color_type = None
    chunks = []
    position = len(PNG_SIGNATURE)
    while position < len(content):
        chunk_length = struct.unpack(">I", content[position : position + 4])[0]
        position += 4
        chunk_type = content[position : position + 4]
        position += 4
        chunk_data = content[position : position + chunk_length]
        position += chunk_length + 4  # skip data and CRC

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type not in {2, 6}:
                raise ValueError("Postprocessing only supports 8-bit RGB or RGBA PNG images.")
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("Postprocessing only supports standard non-interlaced PNG images.")
        elif chunk_type == b"IDAT":
            chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError("PNG is missing an IHDR header.")

    bytes_per_pixel = 4 if color_type == 6 else 3
    stride = width * bytes_per_pixel
    decoded = zlib.decompress(b"".join(chunks))
    rows = []
    offset = 0
    previous_row = bytearray(stride)

    for _ in range(height):
        filter_type = decoded[offset]
        offset += 1
        row = bytearray(decoded[offset : offset + stride])
        offset += stride

        if filter_type == 1:
            for index in range(bytes_per_pixel, stride):
                row[index] = (row[index] + row[index - bytes_per_pixel]) & 0xFF
        elif filter_type == 2:
            for index in range(stride):
                row[index] = (row[index] + previous_row[index]) & 0xFF
        elif filter_type == 3:
            for index in range(stride):
                left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                row[index] = (row[index] + ((left + previous_row[index]) // 2)) & 0xFF
        elif filter_type == 4:
            for index in range(stride):
                left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                up = previous_row[index]
                up_left = previous_row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                row[index] = (row[index] + _paeth_predictor(left, up, up_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")

        if color_type == 2:
            rgba_row = bytearray(width * 4)
            for index in range(width):
                source_index = index * 3
                target_index = index * 4
                rgba_row[target_index : target_index + 4] = row[source_index : source_index + 3] + b"\xFF"
            rows.append(rgba_row)
        else:
            rows.append(bytearray(row))
        previous_row = row

    return width, height, rows


def _png_chunk(chunk_type, data):
    """Return a serialized PNG chunk."""
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _write_png_rgba(path, width, height, rows):
    """Write RGBA rows to an 8-bit non-interlaced PNG file."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)

    payload = zlib.compress(bytes(raw))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    Path(path).write_bytes(
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", payload)
        + _png_chunk(b"IEND", b"")
    )


def _smoothstep(value):
    """Return a smooth interpolation curve between 0 and 1."""
    clamped = min(max(value, 0.0), 1.0)
    return clamped * clamped * (3.0 - 2.0 * clamped)


def _rgba_float_to_bytes(color):
    """Convert an RGBA float tuple to 8-bit RGBA bytes."""
    return tuple(max(0, min(255, round(channel * 255))) for channel in color)


def add_soft_border_rgba(width, height, rows, border_width, border_color):
    """Return a new image with a soft solid-color border around the source image."""
    if border_width <= 0:
        return width, height, rows

    output_width = width + border_width * 2
    output_height = height + border_width * 2
    output_rows = []

    for output_y in range(output_height):
        source_y = min(max(output_y - border_width, 0), height - 1)
        source_row = rows[source_y]
        distance_y = 0
        if output_y < border_width:
            distance_y = border_width - output_y
        elif output_y >= border_width + height:
            distance_y = output_y - (border_width + height) + 1

        output_row = bytearray(output_width * 4)
        for output_x in range(output_width):
            source_x = min(max(output_x - border_width, 0), width - 1)
            source_index = source_x * 4
            output_index = output_x * 4

            distance_x = 0
            if output_x < border_width:
                distance_x = border_width - output_x
            elif output_x >= border_width + width:
                distance_x = output_x - (border_width + width) + 1

            if distance_x == 0 and distance_y == 0:
                output_row[output_index : output_index + 4] = source_row[source_index : source_index + 4]
                continue

            blend_amount = _smoothstep(max(distance_x, distance_y) / border_width)
            for channel in range(4):
                source_value = source_row[source_index + channel]
                border_value = border_color[channel]
                output_row[output_index + channel] = round(
                    source_value + (border_value - source_value) * blend_amount
                )
        output_rows.append(output_row)

    return output_width, output_height, output_rows


from pathlib import Path


def create_boxes(params=DEFAULT_RENDER_PARAMETERS, pixel_grid=None):
    """Create boxes from the configured layout and colors."""
    blender = require_bpy()
    boxes = []
    active_box_configs = create_box_configs(pixel_grid)
    for config in active_box_configs:

        # 1. Create a UNIQUE material for this specific box
        mat = blender.data.materials.new(name=f"{config.name}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")

        if bsdf:

            # Apply the unique color
            bsdf.inputs["Base Color"].default_value = config.color

            # Apply the shared parameters to this specific material
            set_material_input(bsdf, ["Roughness"], params.box_roughness)
            set_material_input(bsdf, ["Metallic"], params.box_metallic)
            set_material_input(bsdf, ["Specular IOR Level", "Specular"], params.box_specular)
            set_material_input(bsdf, ["Emission Strength"], params.box_emission_strength)

        # 3. Create the geometry directly in Blender's data blocks
        vertices, faces = create_box_geometry(config.dimensions)

        # Create Mesh and Object data
        mesh = blender.data.meshes.new(name=f"{config.name}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update() # Write the new geometry data to the mesh

        box = blender.data.objects.new(name=config.name, object_data=mesh)
        box.location = config.position

        # Link to scene so it is visible/renderable
        blender.context.scene.collection.objects.link(box)

        # Assign the newly created unique material
        box.data.materials.append(mat)
        boxes.append(box)

    return boxes


def setup_lighting(params=DEFAULT_RENDER_PARAMETERS):
    """Set up three-point lighting for the scene."""
    blender = require_bpy()
    scene_collection = blender.context.scene.collection

    # --- Key Light ---
    #key_data = blender.data.lights.new(name="KeyLight", type="AREA")
    #key_data.energy = params.key_light_energy
    #key_data.size = 1.5
    #key_data.color = (1.0, 1.0, 1.0)

    #key_light = blender.data.objects.new(name="KeyLight", object_data=key_data)
    #key_light.location = (6, -5, 8)
    #scene_collection.objects.link(key_light)

    # --- Fill Light ---


    ceiling_data = bpy.data.lights.new(name="CeilingLightData", type="AREA")

    # 2. Change the shape to a rectangle
    ceiling_data.shape = 'RECTANGLE'

    # 3. Set the width (size) and height (size_y)
    ceiling_data.size = 30.0    # Width in meters
    ceiling_data.size_y = 30.0  # Height in meters

    # 4. Set energy and color
    ceiling_data.energy = params.fill_light_energy
    ceiling_data.color = (1.0, 1.0, 1.0)

    # 5. Create the object and link it to the scene
    ceiling_obj = bpy.data.objects.new(name="CeilingLight", object_data=ceiling_data)
    bpy.context.collection.objects.link(ceiling_obj)

    # 6. Position the light at the ceiling
    # Area lights point straight down (-Z axis) by default
    ceiling_obj.location = (0.0, 0.0, 10) #

    # --- Rim Light ---
    #rim_data = blender.data.lights.new(name="RimLight", type="AREA")
    #rim_data.energy = params.rim_light_energy
    #rim_data.size = 4
    #rim_data.color = (1.0, 1.0, 1.0)

    #rim_light = blender.data.objects.new(name="RimLight", object_data=rim_data)
    #rim_light.location = (-2, 6, 6)
    #scene_collection.objects.link(rim_light)


def setup_camera():
    """Set up the camera to frame the scene with all boxes."""
    blender = require_bpy()
    scene_collection = blender.context.scene.collection

    # --- Camera Target (Empty) ---
    target = blender.data.objects.new("CameraTarget", None)
    target.empty_display_type = "PLAIN_AXES"
    target.location = (0, 0, 1)
    scene_collection.objects.link(target)

    # --- Camera ---
    cam_data = blender.data.cameras.new("Camera")
    camera = blender.data.objects.new("Camera", object_data=cam_data)
    camera.location = (0, -0.01, 28.2)
    scene_collection.objects.link(camera)

    # --- Constraints ---
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    # Set as the scene's active camera
    blender.context.scene.camera = camera


def setup_world(params=DEFAULT_RENDER_PARAMETERS):
    """Set up a white background."""
    blender = require_bpy()
    world = blender.context.scene.world
    if not world:
        world = blender.data.worlds.new("New World")
        blender.context.scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear existing nodes to start fresh
    nodes.clear()

    # 1. Create the necessary nodes
    node_light_path = nodes.new(type='ShaderNodeLightPath')
    node_bg_color = nodes.new(type='ShaderNodeBackground') # For the visual color
    node_bg_dark = nodes.new(type='ShaderNodeBackground')  # For the lighting (darkness)
    node_mix = nodes.new(type='ShaderNodeMixShader')
    node_output = nodes.new(type='ShaderNodeOutputWorld')

    # 2. Set your specific background color here (R, G, B, A)
    # Example: A nice blue background
    node_bg_color.inputs[0].default_value = (0.9, 0.9, 0.9, 1.0)
    node_bg_color.inputs[1].default_value = 1.0 # Visual strength

    # 3. Ensure the lighting background emits absolutely nothing
    node_bg_dark.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0) # Pure Black
    node_bg_dark.inputs[1].default_value = 0.0 # 0 Strength

    # 4. Link the nodes
    # The 'Is Camera Ray' switch: 1 (True) uses the bottom socket, 0 (False) uses the top.
    links.new(node_light_path.outputs['Is Camera Ray'], node_mix.inputs[0])

    # Top socket (False): Used for diffuse, glossy, and shadow rays -> Pure darkness
    links.new(node_bg_dark.outputs[0], node_mix.inputs[1])

    # Bottom socket (True): Used only for the camera's vision -> Your custom color
    links.new(node_bg_color.outputs[0], node_mix.inputs[2])

    # Output to the world
    links.new(node_mix.outputs[0], node_output.inputs[0])


def setup_render_settings(params=DEFAULT_RENDER_PARAMETERS):
    """Configure Cycles ray tracing render settings."""
    blender = require_bpy()
    scene = blender.context.scene

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = params.samples
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"

    scene.render.resolution_x = params.resolution_x
    scene.render.resolution_y = params.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render(output_path=None):
    """Render the scene to an image file."""
    blender = require_bpy()
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "orange_cube")

    output_base = Path(output_path)
    output_file = output_base
    output_file.parent.mkdir(parents=True, exist_ok=True)
    blend_path = output_base.with_suffix(".blend")

    full_output_path = os.path.abspath(output_file)
    blend_output_path = os.path.abspath(blend_path)
    blender.context.scene.render.filepath = str(full_output_path)
    blender.ops.wm.save_as_mainfile(filepath=str(blend_output_path))
    blender.ops.render.render(write_still=True)
    print(f"Render saved to: {output_file}")
    print(f"Blend scene saved to: {blend_path}")
    return str(output_file)


def render_scene(params=DEFAULT_RENDER_PARAMETERS, output_path=None, image_path="example.png"):
    """Set up the scene and render it with the supplied parameters."""
    clear_scene()
    # create_floor(params)
    pixel_grid = None
    if image_path is not None:
        pixel_grid = load_image_heightmap(image_path)
    else:
        pixel_grid = load_image_heightmap("example.png")


    create_boxes(params, pixel_grid=pixel_grid)
    create_floor(params)
    setup_lighting(params)
    setup_camera()
    setup_world(params)
    setup_render_settings(params)
    return render(output_path=output_path)


def render_fast(image_path=None, output_path=None):
    """Main entry point: set up the scene and render boxes on a white floor."""
    return render_scene(DEFAULT_RENDER_PARAMETERS, output_path=output_path, image_path=image_path)


def render_full(image_path=None, output_path=None):
    """Main entry point: set up the scene and render boxes on a white floor."""
    return render_scene(FULL_RES_RENDER_PARAMETERS, output_path=output_path, image_path=image_path)


if __name__ == "__main__":
    render_fast()
