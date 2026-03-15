import io
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import animate


class AnimateTests(unittest.TestCase):
    def test_render_frame_uses_expected_command_and_height(self):
        env = {"BASE": "value"}

        with patch("animate.subprocess.run") as run:
            self.assertTrue(animate.render_frame(1, env))

        run.assert_called_once_with(
            [
                "python",
                "-m",
                "arkiv_cube_3d",
                "render",
                "--image",
                animate.INPUT_IMAGE,
                "--output",
                animate.build_output_path(1),
            ],
            env=env,
            check=True,
        )
        self.assertEqual(env["HEIGHT_PERCENTAGE"], "0.07")

    def test_main_stops_after_render_failure(self):
        calls = []

        def fake_run(command, env, check):
            calls.append((command, dict(env), check))
            if len(calls) == 2:
                raise subprocess.CalledProcessError(returncode=1, cmd=command)

        stdout = io.StringIO()
        with (
            patch("animate.NUM_FRAMES", 4),
            patch("animate.os.environ", {"BASE": "value"}),
            patch("animate.os.makedirs") as makedirs,
            patch("animate.subprocess.run", side_effect=fake_run),
            redirect_stdout(stdout),
        ):
            animate.main()

        makedirs.assert_called_once_with(animate.OUTPUT_DIR, exist_ok=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1]["HEIGHT_PERCENTAGE"], "0.00")
        self.assertEqual(calls[1][1]["HEIGHT_PERCENTAGE"], "25.00")
        output = stdout.getvalue()
        self.assertIn(f"Output folder '{animate.OUTPUT_DIR}' is ready.", output)
        self.assertIn("Starting render of 4 frames...", output)
        self.assertIn("Error rendering frame 1:", output)
        self.assertIn("Rendering complete!", output)


if __name__ == "__main__":
    unittest.main()
