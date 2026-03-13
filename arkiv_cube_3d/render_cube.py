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


def clear_scene():
    """Remove all default objects from the scene."""
    blender = require_bpy()
    blender.ops.object.select_all(action="SELECT")
    blender.ops.object.delete(use_global=False)


def get_active_object():
    """Return the active object from the current Blender context."""
    blender = require_bpy()
    context = blender.context
    view_layer = getattr(context, "view_layer", None)
    view_layer_objects = getattr(view_layer, "objects", None)

    for object_ref in (
        getattr(context, "active_object", None),
        getattr(context, "object", None),
        getattr(view_layer_objects, "active", None),
    ):
        if object_ref is not None:
            return object_ref

    selected_objects = getattr(context, "selected_objects", None)
    if selected_objects:
        # As a best-effort fallback, use the most recently selected object when
        # Blender does not expose the new object through active_object/object.
        return selected_objects[-1]

    raise RuntimeError("Blender did not expose an active object after creating one.")


def create_floor(params=DEFAULT_RENDER_PARAMETERS):
    """Create a large white floor plane."""
    blender = require_bpy()
    blender.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
    floor = get_active_object()
    floor.name = "Floor"

    mat = blender.data.materials.new(name="FloorMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    set_material_input(bsdf, ["Roughness"], params.floor_roughness)

    floor.data.materials.append(mat)
    return floor


def create_boxes(params=DEFAULT_RENDER_PARAMETERS):
    """Create 5 boxes at different heights for lighting tests."""
    blender = require_bpy()
    boxes = []
    box_configs = [
        ("Box1", (0, 0, 2.0), 2.0),
        ("Box1", (5, 0, 2.0), 2.0),
        ("Box1", (0, 5, 2.0), 2.0),
        ("Box1", (-5, 0, 2.0), 2.0),
        ("Box1", (0, -5, 2.0), 2.0),
    ]

    for name, loc, size in box_configs:
        blender.ops.mesh.primitive_cube_add(size=size, location=loc)
        box = get_active_object()
        box.name = name

        mat = blender.data.materials.new(name=f"{name}Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = params.box_color
        set_material_input(bsdf, ["Roughness"], params.box_roughness)
        set_material_input(bsdf, ["Metallic"], params.box_metallic)
        set_material_input(bsdf, ["Specular IOR Level", "Specular"], params.box_specular)
        set_material_input(bsdf, ["Emission Strength"], params.box_emission_strength)

        box.data.materials.append(mat)
        boxes.append(box)

    return boxes


def setup_lighting(params=DEFAULT_RENDER_PARAMETERS):
    """Set up three-point lighting for the scene."""
    blender = require_bpy()
    blender.ops.object.light_add(type="AREA", location=(6, -5, 8))
    key_light = get_active_object()
    key_light.name = "KeyLight"
    key_light.data.energy = params.key_light_energy
    key_light.data.size = 5
    key_light.data.color = (1.0, 0.95, 0.9)

    blender.ops.object.light_add(type="AREA", location=(-5, -3, 5))
    fill_light = get_active_object()
    fill_light.name = "FillLight"
    fill_light.data.energy = params.fill_light_energy
    fill_light.data.size = 8
    fill_light.data.color = (0.9, 0.93, 1.0)

    blender.ops.object.light_add(type="AREA", location=(-2, 6, 6))
    rim_light = get_active_object()
    rim_light.name = "RimLight"
    rim_light.data.energy = params.rim_light_energy
    rim_light.data.size = 4
    rim_light.data.color = (1.0, 1.0, 1.0)


def setup_camera():
    """Set up the camera to frame the scene with all boxes."""
    blender = require_bpy()
    blender.ops.object.camera_add(location=(12, -12, 10))
    camera = get_active_object()
    camera.name = "Camera"

    blender.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1))
    target = get_active_object()
    target.name = "CameraTarget"

    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

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
