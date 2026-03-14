"""Render boxes on a white floor with lighting and ray tracing using Blender."""

from dataclasses import dataclass, replace
import os
from pathlib import Path

try:
    from .geometry import create_box_geometry, create_floor_geometry, create_box_configs
except ImportError:  # pragma: no cover - supports direct script execution
    from geometry import create_box_geometry, create_floor_geometry

try:
    import bpy
except ImportError:  # pragma: no cover - exercised indirectly by runtime checks
    bpy = None


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
    key_light_energy: float = 600.0
    fill_light_energy: float = 1500.0
    rim_light_energy: float = 100.0
    samples: int = 128
    resolution_x: int = 400
    resolution_y: int = 400


DEFAULT_RENDER_PARAMETERS = RenderParameters()
PREVIEW_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, samples=16, resolution_x=400, resolution_y=400)
FULL_RES_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, resolution_x=2000, resolution_y=2000)
HEIGHTMAP_IMAGE_SIZE = 23
HEIGHTMAP_BOX_SIZE = 0.55


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
        if (width, height) != (HEIGHTMAP_IMAGE_SIZE, HEIGHTMAP_IMAGE_SIZE):
            raise ValueError(
                f"Heightmap image must be {HEIGHTMAP_IMAGE_SIZE}x{HEIGHTMAP_IMAGE_SIZE} pixels; "
                f"got {width}x{height}."
            )

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


def create_boxes(params=DEFAULT_RENDER_PARAMETERS, pixel_grid=None):
    """Create boxes from the configured layout and colors."""
    blender = require_bpy()
    boxes = []
    active_box_configs = create_box_configs(pixel_grid)
    for config in active_box_configs:
        if len(config) == 5:
            name, loc, size, color, height = config
        else:
            name, loc, size, color = config
            height = None

        # 1. Create a UNIQUE material for this specific box
        mat = blender.data.materials.new(name=f"{name}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")

        if bsdf:

            # Apply the unique color
            bsdf.inputs["Base Color"].default_value = color

            # Apply the shared parameters to this specific material
            set_material_input(bsdf, ["Roughness"], params.box_roughness)
            set_material_input(bsdf, ["Metallic"], params.box_metallic)
            set_material_input(bsdf, ["Specular IOR Level", "Specular"], params.box_specular)
            set_material_input(bsdf, ["Emission Strength"], params.box_emission_strength)

        # 3. Create the geometry directly in Blender's data blocks
        verts, faces = create_box_geometry(size)

        # Create Mesh and Object data
        mesh = blender.data.meshes.new(name=f"{name}_Mesh")
        mesh.from_pydata(verts, [], faces)
        mesh.update() # Write the new geometry data to the mesh

        box = blender.data.objects.new(name=name, object_data=mesh)
        box.location = loc

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
    key_data = blender.data.lights.new(name="KeyLight", type="AREA")
    key_data.energy = params.key_light_energy
    key_data.size = 1.5
    key_data.color = (1.0, 1.0, 1.0)

    key_light = blender.data.objects.new(name="KeyLight", object_data=key_data)
    key_light.location = (6, -5, 8)
    scene_collection.objects.link(key_light)

    # --- Fill Light ---
    fill_data = blender.data.lights.new(name="FillLight", type="AREA")
    fill_data.energy = params.fill_light_energy
    fill_data.size = 4.0
    fill_data.color = (1.0, 1.0, 1.0)

    fill_light = blender.data.objects.new(name="FillLight", object_data=fill_data)
    fill_light.location = (-15, -15, 10)
    scene_collection.objects.link(fill_light)

    fill_light = blender.data.objects.new(name="FillLight2", object_data=fill_data)
    fill_light.location = (15, -15, 10)
    scene_collection.objects.link(fill_light)

    fill_light = blender.data.objects.new(name="FillLight3", object_data=fill_data)
    fill_light.location = (-15, 15, 10)
    scene_collection.objects.link(fill_light)

    fill_light = blender.data.objects.new(name="FillLight4", object_data=fill_data)
    fill_light.location = (15, 15, 10)
    scene_collection.objects.link(fill_light)

    # --- Rim Light ---
    rim_data = blender.data.lights.new(name="RimLight", type="AREA")
    rim_data.energy = params.rim_light_energy
    rim_data.size = 4
    rim_data.color = (1.0, 1.0, 1.0)

    rim_light = blender.data.objects.new(name="RimLight", object_data=rim_data)
    rim_light.location = (-2, 6, 6)
    scene_collection.objects.link(rim_light)


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
    camera.location = (0, -0.01, 30)
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
    world = blender.data.worlds.get("World")
    if world is None:
        world = blender.data.worlds.new("World")
    blender.context.scene.world = world

    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    bg_node = tree.nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg_node.inputs["Strength"].default_value = params.world_strength

    output_node = tree.nodes.new(type="ShaderNodeOutputWorld")
    tree.links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


def setup_render_settings(params=DEFAULT_RENDER_PARAMETERS):
    """Configure Cycles ray tracing render settings."""
    blender = require_bpy()
    scene = blender.context.scene

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = params.samples
    scene.cycles.use_denoising = True

    scene.render.resolution_x = params.resolution_x
    scene.render.resolution_y = params.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render(output_path=None):
    """Render the scene to an image file."""
    blender = require_bpy()
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "orange_cube.png")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    blend_path = output_file.with_suffix(".blend")

    blender.context.scene.render.filepath = str(output_file)
    blender.ops.wm.save_as_mainfile(filepath=str(blend_path))
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
    setup_lighting(params)
    setup_camera()
    setup_world(params)
    setup_render_settings(params)
    return render(output_path=output_path)


def render_fast(image_path=None):
    """Main entry point: set up the scene and render boxes on a white floor."""
    return render_scene(DEFAULT_RENDER_PARAMETERS, image_path=image_path)


def render_full(image_path=None):
    """Main entry point: set up the scene and render boxes on a white floor."""
    return render_scene(FULL_RES_RENDER_PARAMETERS, image_path=image_path)


if __name__ == "__main__":
    render_fast()
