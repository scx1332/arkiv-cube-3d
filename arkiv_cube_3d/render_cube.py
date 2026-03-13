"""Render boxes on a white floor with lighting and ray tracing using Blender."""

import bpy
import os


def clear_scene():
    """Remove all default objects from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def create_floor():
    """Create a large white floor plane with low-roughness material for diffused reflections."""
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"

    mat = bpy.data.materials.new(name="FloorMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)  # White
    # Low roughness produces diffused (blurry) reflections of boxes above the floor.
    # Shadows from boxes are cast onto the floor automatically by the Cycles renderer.
    bsdf.inputs["Roughness"].default_value = 0.1

    floor.data.materials.append(mat)
    return floor


def create_boxes():
    """Create 5 boxes at different heights for lighting tests."""
    boxes = []
    box_configs = [
        # (name, location, size, color, roughness)
        # Box sitting on floor
        ("Box1", (0, 0, 1.0), 2.0, (0.8, 0.35, 0.0, 1.0), 0.4),
        # Box half buried in floor
        ("Box2", (-4, 3, -0.5), 1.5, (0.2, 0.5, 0.8, 1.0), 0.3),
        # Box floating mid-air
        ("Box3", (3, 4, 3.0), 1.0, (0.8, 0.2, 0.2, 1.0), 0.5),
        # Box floating high
        ("Box4", (5, -2, 5.0), 1.2, (0.2, 0.7, 0.3, 1.0), 0.4),
        # Box mostly buried in floor
        ("Box5", (-3, -4, -0.8), 1.8, (0.6, 0.3, 0.7, 1.0), 0.35),
    ]

    for name, loc, size, color, roughness in box_configs:
        bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
        box = bpy.context.active_object
        box.name = name

        mat = bpy.data.materials.new(name=f"{name}Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0

        box.data.materials.append(mat)
        boxes.append(box)

    return boxes


def setup_lighting():
    """Set up three-point lighting for the scene."""
    # Key light - main light source
    bpy.ops.object.light_add(type="AREA", location=(6, -5, 8))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 400
    key_light.data.size = 5
    key_light.data.color = (1.0, 0.95, 0.9)

    # Fill light - softer, from the other side
    bpy.ops.object.light_add(type="AREA", location=(-5, -3, 5))
    fill_light = bpy.context.active_object
    fill_light.name = "FillLight"
    fill_light.data.energy = 150
    fill_light.data.size = 8
    fill_light.data.color = (0.9, 0.93, 1.0)

    # Rim light - from behind for edge definition
    bpy.ops.object.light_add(type="AREA", location=(-2, 6, 6))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 200
    rim_light.data.size = 4
    rim_light.data.color = (1.0, 1.0, 1.0)


def setup_camera():
    """Set up the camera to frame the scene with all boxes."""
    bpy.ops.object.camera_add(location=(12, -12, 10))
    camera = bpy.context.active_object
    camera.name = "Camera"

    # Create an empty at the scene center as a camera target
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1))
    target = bpy.context.active_object
    target.name = "CameraTarget"

    # Point camera at the target
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    bpy.context.scene.camera = camera


def setup_world():
    """Set up a white background."""
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    bg_node = tree.nodes.new(type="ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg_node.inputs["Strength"].default_value = 1.0

    output_node = tree.nodes.new(type="ShaderNodeOutputWorld")
    tree.links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])


def setup_render_settings():
    """Configure Cycles ray tracing render settings."""
    scene = bpy.context.scene

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def render(output_path=None):
    """Render the scene to an image file."""
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "orange_cube.png")

    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Render saved to: {output_path}")
    return output_path


def main():
    """Main entry point: set up the scene and render boxes on a white floor."""
    clear_scene()
    create_floor()
    create_boxes()
    setup_lighting()
    setup_camera()
    setup_world()
    setup_render_settings()
    output = render()
    return output


if __name__ == "__main__":
    main()
