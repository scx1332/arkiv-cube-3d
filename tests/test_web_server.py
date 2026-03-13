import unittest

import arkiv_cube_3d.render_cube as render_cube
from arkiv_cube_3d.render_cube import FULL_RES_RENDER_PARAMETERS, PREVIEW_RENDER_PARAMETERS
from arkiv_cube_3d.web_server import build_render_parameters, hex_to_rgba


class WebServerTests(unittest.TestCase):
    def test_hex_to_rgba_converts_html_color(self):
        self.assertEqual(hex_to_rgba("#cc5a00"), (0.8, 0.35294117647058826, 0.0, 1.0))

    def test_build_render_parameters_preview_profile(self):
        params = build_render_parameters({}, profile="preview")

        self.assertEqual(params.samples, PREVIEW_RENDER_PARAMETERS.samples)
        self.assertEqual(params.resolution_x, PREVIEW_RENDER_PARAMETERS.resolution_x)
        self.assertEqual(params.resolution_y, PREVIEW_RENDER_PARAMETERS.resolution_y)

    def test_build_render_parameters_full_profile_with_clamping(self):
        params = build_render_parameters(
            {
                "box_color": "#ffffff",
                "box_roughness": "1.5",
                "box_metallic": "-2",
                "box_specular": "0.25",
                "box_emission_strength": "6.0",
                "world_strength": "4.5",
            },
            profile="full",
        )

        self.assertEqual(params.samples, FULL_RES_RENDER_PARAMETERS.samples)
        self.assertEqual(params.resolution_x, FULL_RES_RENDER_PARAMETERS.resolution_x)
        self.assertEqual(params.resolution_y, FULL_RES_RENDER_PARAMETERS.resolution_y)
        self.assertEqual(params.box_color, (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(params.box_roughness, 1.0)
        self.assertEqual(params.box_metallic, 0.0)
        self.assertEqual(params.box_specular, 0.25)
        self.assertEqual(params.box_emission_strength, 5.0)
        self.assertEqual(params.world_strength, 4.5)

    def test_build_render_parameters_rejects_unknown_profile(self):
        with self.assertRaises(ValueError):
            build_render_parameters({}, profile="draft")

    def test_is_bpy_available_matches_module_state(self):
        self.assertEqual(render_cube.is_bpy_available(), render_cube.bpy is not None)

    def test_set_material_input_updates_first_matching_socket(self):
        class Socket:
            def __init__(self):
                self.default_value = None

        class Inputs:
            def __init__(self, sockets):
                self._sockets = sockets

            def get(self, name):
                return self._sockets.get(name)

        class Bsdf:
            def __init__(self):
                self.inputs = Inputs({"Roughness": Socket()})

        bsdf = Bsdf()
        render_cube.set_material_input(bsdf, ["Specular", "Roughness"], 0.75)

        self.assertEqual(bsdf.inputs.get("Roughness").default_value, 0.75)

    def test_get_active_object_falls_back_to_context_object(self):
        sentinel = object()

        class Context:
            object = sentinel

        original_bpy = render_cube.bpy
        render_cube.bpy = type("Bpy", (), {"context": Context()})()
        self.addCleanup(setattr, render_cube, "bpy", original_bpy)

        self.assertIs(render_cube.get_active_object(), sentinel)

    def test_create_floor_uses_fallback_active_object_lookup(self):
        class Socket:
            def __init__(self):
                self.default_value = None

        class Inputs(dict):
            def get(self, name):
                return super().get(name)

        class Bsdf:
            def __init__(self):
                self.inputs = Inputs({"Base Color": Socket(), "Roughness": Socket()})

        class Nodes(dict):
            def get(self, name):
                return super().get(name)

        class NodeTree:
            def __init__(self):
                self.nodes = Nodes({"Principled BSDF": Bsdf()})

        class Material:
            def __init__(self):
                self.use_nodes = False
                self.node_tree = NodeTree()

        class Materials:
            def new(self, name):
                return Material()

        class MeshData:
            def __init__(self):
                self.materials = []

        class Floor:
            def __init__(self):
                self.name = None
                self.data = MeshData()

        floor = Floor()

        class Context:
            object = floor

        class MeshOps:
            def primitive_plane_add(self, **kwargs):
                return None

        blender = type(
            "Bpy",
            (),
            {
                "context": Context(),
                "ops": type("Ops", (), {"mesh": MeshOps()})(),
                "data": type("Data", (), {"materials": Materials()})(),
            },
        )()

        original_bpy = render_cube.bpy
        render_cube.bpy = blender
        self.addCleanup(setattr, render_cube, "bpy", original_bpy)

        created_floor = render_cube.create_floor()

        self.assertIs(created_floor, floor)
        self.assertEqual(created_floor.name, "Floor")
        self.assertEqual(len(created_floor.data.materials), 1)


if __name__ == "__main__":
    unittest.main()
