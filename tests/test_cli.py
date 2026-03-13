import io
import sys
import unittest
from contextlib import redirect_stderr
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


if __name__ == "__main__":
    unittest.main()
