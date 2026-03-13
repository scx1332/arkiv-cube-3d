"""Render boxes on a white floor with lighting and ray tracing using Blender."""

from dataclasses import dataclass, replace
import os

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
    world_strength: float = 1.0
    key_light_energy: float = 400.0
    fill_light_energy: float = 150.0
    rim_light_energy: float = 200.0
    samples: int = 128
    resolution_x: int = 600
    resolution_y: int = 400


DEFAULT_RENDER_PARAMETERS = RenderParameters()
PREVIEW_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, samples=32, resolution_x=600, resolution_y=400)
FULL_RES_RENDER_PARAMETERS = replace(DEFAULT_RENDER_PARAMETERS, resolution_x=1920, resolution_y=1080)


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


def clear_scene():
    """Remove all default objects and orphaned data from the scene."""
    blender = require_bpy()
    blender.ops.object.select_all(action="SELECT")
    blender.ops.object.delete(use_global=False)
    remove_unused_data_blocks(blender.data.meshes)
    remove_unused_data_blocks(blender.data.materials)
    remove_unused_data_blocks(blender.data.lights)
    remove_unused_data_blocks(blender.data.cameras)


def create_floor(params=DEFAULT_RENDER_PARAMETERS):
    """Create a large white floor plane without relying on UI context."""
    blender = require_bpy()

    # 1. Define the geometry for a 100x100 plane manually
    size = 100.0
    half = size / 2.0
    verts = [
        (-half, -half, 0.0),
        (half, -half, 0.0),
        (half, half, 0.0),
        (-half, half, 0.0)
    ]
    faces = [(0, 1, 2, 3)]

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


def create_boxes(params=DEFAULT_RENDER_PARAMETERS):
    """Create 5 boxes at different locations for lighting tests without UI context."""
    blender = require_bpy()
    boxes = []

    # 1. Fixed unique names for better scene organization
    box_configs = [
        ("Box_Center", (0, 0, 2.0), 2.0),
        ("Box_East",   (5, 0, 2.0), 2.0),
        ("Box_North",  (0, 5, 2.0), 2.0),
        ("Box_West",   (-5, 0, 2.0), 2.0),
        ("Box_South",  (0, -5, 2.0), 2.0),
    ]

    # 2. Optimized: Create the material ONCE before the loop
    mat = blender.data.materials.new(name="BoxTestMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    # Safety check in case the BSDF node isn't found
    if bsdf:
        bsdf.inputs["Base Color"].default_value = params.box_color
        set_material_input(bsdf, ["Roughness"], params.box_roughness)
        set_material_input(bsdf, ["Metallic"], params.box_metallic)
        set_material_input(bsdf, ["Specular IOR Level", "Specular"], params.box_specular)
        set_material_input(bsdf, ["Emission Strength"], params.box_emission_strength)

    # 3. Create the geometry directly in Blender's data blocks
    for name, loc, size in box_configs:

        # Calculate radius from size to define the bounding box limits
        r = size / 2.0

        # Define 8 vertices of a cube
        verts = [
            (-r, -r, -r), ( r, -r, -r), ( r,  r, -r), (-r,  r, -r), # Bottom 4
            (-r, -r,  r), ( r, -r,  r), ( r,  r,  r), (-r,  r,  r)  # Top 4
        ]

        # Define the 6 faces connecting the vertices
        faces = [
            (0, 1, 2, 3), # Bottom
            (7, 6, 5, 4), # Top
            (0, 1, 5, 4), # Front
            (1, 2, 6, 5), # Right
            (2, 3, 7, 6), # Back
            (3, 0, 4, 7)  # Left
        ]

        # Create Mesh and Object data
        mesh = blender.data.meshes.new(name=f"{name}_Mesh")
        mesh.from_pydata(verts, [], faces)
        mesh.update() # Write the new geometry data to the mesh

        box = blender.data.objects.new(name=name, object_data=mesh)
        box.location = loc

        # Link to scene so it is visible/renderable
        blender.context.scene.collection.objects.link(box)

        # Assign the shared material
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
    key_data.size = 5
    key_data.color = (1.0, 0.95, 0.9)

    key_light = blender.data.objects.new(name="KeyLight", object_data=key_data)
    key_light.location = (6, -5, 8)
    scene_collection.objects.link(key_light)

    # --- Fill Light ---
    fill_data = blender.data.lights.new(name="FillLight", type="AREA")
    fill_data.energy = params.fill_light_energy
    fill_data.size = 8
    fill_data.color = (0.9, 0.93, 1.0)

    fill_light = blender.data.objects.new(name="FillLight", object_data=fill_data)
    fill_light.location = (-5, -3, 5)
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
    camera.location = (12, -12, 10)
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

    blender.context.scene.render.filepath = output_path
    blender.ops.render.render(write_still=True)
    print(f"Render saved to: {output_path}")
    return output_path


def render_scene(params=DEFAULT_RENDER_PARAMETERS, output_path=None):
    """Set up the scene and render it with the supplied parameters."""
    clear_scene()
    create_floor(params)
    create_boxes(params)
    setup_lighting(params)
    setup_camera()
    setup_world(params)
    setup_render_settings(params)
    return render(output_path=output_path)


def main():
    """Main entry point: set up the scene and render boxes on a white floor."""
    return render_scene(DEFAULT_RENDER_PARAMETERS)


if __name__ == "__main__":
    main()
