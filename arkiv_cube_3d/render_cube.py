"""Render an orange cube on a white background with lighting and ray tracing using Blender."""

import bpy
import os


def clear_scene():
    """Remove all default objects from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def create_cube():
    """Create an orange cube and return the object."""
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    cube = bpy.context.active_object
    cube.name = "OrangeCube"

    # Create orange material
    mat = bpy.data.materials.new(name="OrangeMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    # Orange color (R, G, B, A)
    bsdf.inputs["Base Color"].default_value = (0.8, 0.35, 0.0, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
    bsdf.inputs["Metallic"].default_value = 0.0

    cube.data.materials.append(mat)

    # Slight rotation for a more interesting angle
    cube.rotation_euler = (0.5, 0.0, 0.8)

    return cube


def setup_lighting():
    """Set up three-point lighting for the scene."""
    # Key light - main light source
    bpy.ops.object.light_add(type="AREA", location=(4, -3, 5))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 200
    key_light.data.size = 3
    key_light.data.color = (1.0, 0.95, 0.9)

    # Fill light - softer, from the other side
    bpy.ops.object.light_add(type="AREA", location=(-3, -2, 3))
    fill_light = bpy.context.active_object
    fill_light.name = "FillLight"
    fill_light.data.energy = 80
    fill_light.data.size = 5
    fill_light.data.color = (0.9, 0.93, 1.0)

    # Rim light - from behind for edge definition
    bpy.ops.object.light_add(type="AREA", location=(-1, 4, 4))
    rim_light = bpy.context.active_object
    rim_light.name = "RimLight"
    rim_light.data.energy = 120
    rim_light.data.size = 2
    rim_light.data.color = (1.0, 1.0, 1.0)


def setup_camera():
    """Set up the camera to frame the cube nicely."""
    bpy.ops.object.camera_add(location=(4.5, -4.5, 3.5))
    camera = bpy.context.active_object
    camera.name = "Camera"

    # Point camera at the cube
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = bpy.data.objects["OrangeCube"]
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
    """Main entry point: set up the scene and render an orange cube."""
    clear_scene()
    create_cube()
    setup_lighting()
    setup_camera()
    setup_world()
    setup_render_settings()
    output = render()
    return output


if __name__ == "__main__":
    main()
