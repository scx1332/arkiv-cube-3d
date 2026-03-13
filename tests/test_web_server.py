import unittest

from arkiv_cube_3d.render_cube import FULL_RES_RENDER_PARAMETERS, PREVIEW_RENDER_PARAMETERS
from arkiv_cube_3d.web_server import build_render_parameters, hex_to_rgba


class WebServerTests(unittest.TestCase):
    def test_hex_to_rgba_converts_html_color(self):
        self.assertEqual(hex_to_rgba("#cc5a00"), (0.8, 0.35294117647058826, 0.0, 1.0))

    def test_build_render_parameters_uses_preview_profile_defaults(self):
        params = build_render_parameters({}, profile="preview")

        self.assertEqual(params.samples, PREVIEW_RENDER_PARAMETERS.samples)
        self.assertEqual(params.resolution_x, PREVIEW_RENDER_PARAMETERS.resolution_x)
        self.assertEqual(params.resolution_y, PREVIEW_RENDER_PARAMETERS.resolution_y)

    def test_build_render_parameters_uses_full_profile_defaults_and_clamps(self):
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


if __name__ == "__main__":
    unittest.main()
