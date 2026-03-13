import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from arkiv_cube_3d import __main__ as cli
from arkiv_cube_3d.geometry import BOX_DEFAULT_SIZE


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
    def test_render_command_reads_cube_positions_from_json_input(self, is_bpy_available, render_fast):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "cubes.json"
            input_path.write_text(
                json.dumps({"count": 2, "positions": [[1, 2, 3], [4, 5, 6]]}),
                encoding="utf-8",
            )

            self.assertEqual(cli.main(["render", "--input", str(input_path)]), 0)

        render_fast.assert_called_once_with(
            box_configs=[
                ("Box_1", (1.0, 2.0, 3.0), BOX_DEFAULT_SIZE),
                ("Box_2", (4.0, 5.0, 6.0), BOX_DEFAULT_SIZE),
            ]
        )


if __name__ == "__main__":
    unittest.main()
