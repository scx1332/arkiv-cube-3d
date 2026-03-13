import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import arkiv_cube_3d.render_cube as render_cube
from arkiv_cube_3d.render_cube import FULL_RES_RENDER_PARAMETERS, PREVIEW_RENDER_PARAMETERS
from arkiv_cube_3d.web_server import RenderRequestHandler, build_render_parameters, hex_to_rgba


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

    def test_render_file_with_cache_busting_query_is_served(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            render_dir = Path(temp_dir)
            image_name = "preview-test.png"
            image_content = b"png-bytes"
            (render_dir / image_name).write_bytes(image_content)

            with patch("arkiv_cube_3d.web_server.RENDER_OUTPUT_DIR", render_dir):
                server = None
                thread = None
                connection = None
                try:
                    from http.server import ThreadingHTTPServer

                    server = ThreadingHTTPServer(("127.0.0.1", 0), RenderRequestHandler)
                    thread = threading.Thread(target=server.serve_forever)
                    thread.start()

                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                    connection.request("GET", f"/renders/{image_name}?ts=123")
                    response = connection.getresponse()

                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("Content-Type"), "image/png")
                    self.assertEqual(response.read(), image_content)
                finally:
                    if connection is not None:
                        connection.close()
                    if server is not None:
                        server.shutdown()
                        server.server_close()
                    if thread is not None:
                        thread.join()


if __name__ == "__main__":
    unittest.main()
