import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from arkiv_cube_3d import __main__ as cli


class CliTests(unittest.TestCase):
    @patch("arkiv_cube_3d.__main__.web_server.main")
    def test_main_defaults_to_web(self, web_main):
        self.assertEqual(cli.main([]), 0)
        web_main.assert_called_once_with(host="127.0.0.1", port=8000)

    @patch("arkiv_cube_3d.__main__.web_server.main")
    def test_main_ignores_module_path_in_sys_argv(self, web_main):
        with patch.object(sys, "argv", ["C:/scx1332/arkiv-cube-3d/arkiv_cube_3d/__main__.py", "web"]):
            self.assertEqual(cli.main(), 0)
        web_main.assert_called_once_with(host="127.0.0.1", port=8000)

    @patch("arkiv_cube_3d.__main__.web_server.main")
    def test_main_passes_web_options(self, web_main):
        self.assertEqual(cli.main(["web", "--host", "0.0.0.0", "--port", "8765"]), 0)
        web_main.assert_called_once_with(host="0.0.0.0", port=8765)

    def test_main_returns_argparse_error_for_unknown_command(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(cli.main(["unknown"]), 2)

        self.assertIn("invalid choice", stderr.getvalue())

    @patch("arkiv_cube_3d.__main__.render_cube.render_fast", return_value="preview.png")
    @patch("arkiv_cube_3d.__main__.render_cube.is_bpy_available", return_value=True)
    def test_main_passes_image_to_fast_render(self, is_bpy_available, render_fast):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["render", "--image", "example.png"]), 0)

        is_bpy_available.assert_called_once_with()
        render_fast.assert_called_once_with(image_path="example.png")
        self.assertIn("Render completed: preview.png", stdout.getvalue())

    @patch("arkiv_cube_3d.__main__.render_cube.render_full", return_value="full.png")
    @patch("arkiv_cube_3d.__main__.render_cube.is_bpy_available", return_value=True)
    def test_main_passes_image_to_full_render(self, is_bpy_available, render_full):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["render", "--full", "--image", "example.png"]), 0)

        is_bpy_available.assert_called_once_with()
        render_full.assert_called_once_with(image_path="example.png")
        self.assertIn("Render completed: full.png", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
