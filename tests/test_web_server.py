import http.client
import json
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

    def test_load_image_heightmap_reads_grayscale_values_from_11x11_image(self):
        class FakeImage:
            def __init__(self, size, pixels):
                self.size = size
                self.pixels = pixels

        class ImageCollection:
            def __init__(self, image):
                self.image = image
                self.loaded_paths = []
                self.removed = []

            def load(self, *, filepath):
                self.loaded_paths.append(filepath)
                return self.image

            def remove(self, image, do_unlink=True):
                self.removed.append((image, do_unlink))

        width = height = render_cube.HEIGHTMAP_IMAGE_SIZE
        pixels = []
        for row in range(height):
            for column in range(width):
                grayscale = ((height - 1 - row) * width + column) / float(width * height - 1)
                pixels.extend((grayscale, grayscale, grayscale, 1.0))

        image = FakeImage((width, height), pixels)
        images = ImageCollection(image)
        blender = type("Blender", (), {"data": type("Data", (), {"images": images})()})()

        with patch.object(render_cube, "bpy", blender):
            heightmap = render_cube.load_image_heightmap("example.png")

        self.assertEqual(len(heightmap), width)
        self.assertTrue(all(len(row) == height for row in heightmap))
        self.assertEqual(heightmap[0][0], 0.0)
        self.assertEqual(heightmap[-1][-1], 1.0)
        self.assertEqual(images.loaded_paths, [str(Path("example.png").resolve())])
        self.assertEqual(images.removed, [(image, True)])

    def test_load_image_heightmap_rejects_non_11x11_images(self):
        class FakeImage:
            def __init__(self):
                self.size = (10, 11)
                self.pixels = [0.0, 0.0, 0.0, 1.0] * 110

        class ImageCollection:
            def __init__(self):
                self.removed = []

            def load(self, *, filepath):
                return FakeImage()

            def remove(self, image, do_unlink=True):
                self.removed.append((image.size, do_unlink))

        images = ImageCollection()
        blender = type("Blender", (), {"data": type("Data", (), {"images": images})()})()

        with patch.object(render_cube, "bpy", blender):
            with self.assertRaisesRegex(ValueError, "11x11"):
                render_cube.load_image_heightmap("bad.png")

        self.assertEqual(images.removed, [((10, 11), True)])

    def test_create_heightmap_box_configs_creates_fixed_11x11_grid(self):
        heightmap = [[0.0 for _ in range(render_cube.HEIGHTMAP_IMAGE_SIZE)] for _ in range(render_cube.HEIGHTMAP_IMAGE_SIZE)]
        heightmap[0][0] = 0.25
        heightmap[-1][-1] = 0.75

        box_configs = render_cube.create_heightmap_box_configs(heightmap)

        self.assertEqual(len(box_configs), render_cube.HEIGHTMAP_IMAGE_SIZE ** 2)
        first_box = box_configs[0]
        last_box = box_configs[-1]
        self.assertEqual(first_box[0], "Box 1")
        self.assertEqual(first_box[3], (0.25, 0.25, 0.25, 1.0))
        self.assertEqual(first_box[4], 0.25)
        self.assertEqual(last_box[0], "Box 121")
        self.assertEqual(last_box[3], (0.75, 0.75, 0.75, 1.0))
        self.assertEqual(last_box[4], 0.75)

    def test_render_saves_blend_scene_next_to_image(self):
        class WmOps:
            def __init__(self):
                self.saved_paths = []

            def save_as_mainfile(self, *, filepath):
                self.saved_paths.append(filepath)

        class RenderOps:
            def __init__(self):
                self.write_still_calls = []

            def render(self, *, write_still):
                self.write_still_calls.append(write_still)

        blender = type(
            "Blender",
            (),
            {
                "context": type(
                    "Context",
                    (),
                    {"scene": type("Scene", (), {"render": type("Render", (), {"filepath": None})()})()},
                )(),
                "ops": type("Ops", (), {"wm": WmOps(), "render": RenderOps()})(),
            },
        )()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "renders" / "preview.png"
            with patch.object(render_cube, "bpy", blender):
                result = render_cube.render(output_path=str(output_path))

        self.assertEqual(result, str(output_path))
        self.assertEqual(blender.context.scene.render.filepath, str(output_path))
        self.assertEqual(blender.ops.wm.saved_paths, [str(output_path.with_suffix(".blend"))])
        self.assertEqual(blender.ops.render.write_still_calls, [True])

    def test_render_fast_uses_preview_render_parameters(self):
        with patch.object(render_cube, "render_scene", return_value="preview.png") as render_scene:
            result = render_cube.render_fast()

        self.assertEqual(result, "preview.png")
        render_scene.assert_called_once_with(PREVIEW_RENDER_PARAMETERS)

    def test_clear_scene_removes_unused_blender_data_blocks(self):
        class DataCollection(list):
            def __init__(self, items):
                super().__init__(items)
                self.removed = []

            def remove(self, item):
                self.removed.append(item.name)
                super().remove(item)

        class DataBlock:
            def __init__(self, name, users):
                self.name = name
                self.users = users

        class ObjectOps:
            def __init__(self):
                self.select_all_calls = []
                self.delete_calls = []

            def select_all(self, *, action):
                self.select_all_calls.append(action)

            def delete(self, *, use_global):
                self.delete_calls.append(use_global)

        class Blender:
            def __init__(self):
                self.ops = type("Ops", (), {"object": ObjectOps()})()
                self.data = type(
                    "Data",
                    (),
                    {
                        "meshes": DataCollection([DataBlock("unused_mesh", 0), DataBlock("used_mesh", 1)]),
                        "materials": DataCollection([DataBlock("unused_material", 0), DataBlock("used_material", 2)]),
                        "lights": DataCollection([DataBlock("unused_light", 0), DataBlock("used_light", 1)]),
                        "cameras": DataCollection([DataBlock("unused_camera", 0), DataBlock("used_camera", 1)]),
                    },
                )()

        blender = Blender()

        with patch.object(render_cube, "bpy", blender):
            render_cube.clear_scene()

        self.assertEqual(blender.ops.object.select_all_calls, ["SELECT"])
        self.assertEqual(blender.ops.object.delete_calls, [False])
        self.assertEqual(blender.data.meshes.removed, ["unused_mesh"])
        self.assertEqual(blender.data.materials.removed, ["unused_material"])
        self.assertEqual(blender.data.lights.removed, ["unused_light"])
        self.assertEqual(blender.data.cameras.removed, ["unused_camera"])

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

    def test_blend_file_with_cache_busting_query_is_served(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            render_dir = Path(temp_dir)
            blend_name = "preview-test.blend"
            blend_content = b"blend-bytes"
            (render_dir / blend_name).write_bytes(blend_content)

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
                    connection.request("GET", f"/renders/{blend_name}?ts=123")
                    response = connection.getresponse()

                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("Content-Type"), "application/octet-stream")
                    self.assertEqual(response.read(), blend_content)
                finally:
                    if connection is not None:
                        connection.close()
                    if server is not None:
                        server.shutdown()
                        server.server_close()
                    if thread is not None:
                        thread.join()

    @patch("arkiv_cube_3d.web_server.render_with_profile")
    @patch("arkiv_cube_3d.web_server.is_bpy_available", return_value=True)
    def test_render_endpoint_returns_blend_url(self, is_bpy_available, render_with_profile):
        render_with_profile.return_value = ("preview-test.png", "preview-test.blend", PREVIEW_RENDER_PARAMETERS)

        server = None
        thread = None
        connection = None
        try:
            from http.server import ThreadingHTTPServer

            server = ThreadingHTTPServer(("127.0.0.1", 0), RenderRequestHandler)
            thread = threading.Thread(target=server.serve_forever)
            thread.start()

            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            connection.request(
                "POST",
                "/api/render",
                body=json.dumps({"profile": "preview", "params": {}}),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            payload = json.loads(response.read())

            self.assertEqual(response.status, 200)
            self.assertEqual(payload["image_url"], "/renders/preview-test.png")
            self.assertEqual(payload["blend_url"], "/renders/preview-test.blend")
            render_with_profile.assert_called_once_with({}, "preview")
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
