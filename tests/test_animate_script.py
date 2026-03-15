import unittest
from unittest.mock import patch

import animate


class AnimateScriptTests(unittest.TestCase):
    def test_loop1_renders_expected_move_x_frames(self):
        captured_calls = []

        def fake_run(command, env, check):
            captured_calls.append(
                {
                    "command": list(command),
                    "env": {
                        "HEIGHT_PERCENTAGE": env["HEIGHT_PERCENTAGE"],
                        "MOVE_X_PERCENTAGE": env["MOVE_X_PERCENTAGE"],
                    },
                    "check": check,
                }
            )

        with patch("animate.os.makedirs") as makedirs, patch(
            "animate.subprocess.run", side_effect=fake_run
        ), patch("builtins.print"):
            animate.loop1()

        makedirs.assert_called_once_with("frames", exist_ok=True)
        self.assertEqual(len(captured_calls), 10)
        self.assertEqual(captured_calls[0]["env"]["HEIGHT_PERCENTAGE"], "-100.0")
        self.assertEqual(captured_calls[0]["env"]["MOVE_X_PERCENTAGE"], "100.00")
        self.assertEqual(captured_calls[-1]["env"]["HEIGHT_PERCENTAGE"], "-100.0")
        self.assertEqual(captured_calls[-1]["env"]["MOVE_X_PERCENTAGE"], "0.00")
        self.assertEqual(captured_calls[0]["command"][-1], "frames/out_0010.png")
        self.assertEqual(captured_calls[-1]["command"][-1], "frames/out_0019.png")
        self.assertTrue(all(call_info["check"] for call_info in captured_calls))

    def test_loop2_renders_expected_height_frames(self):
        captured_calls = []

        def fake_run(command, env, check):
            captured_calls.append(
                {
                    "command": list(command),
                    "env": {
                        "HEIGHT_PERCENTAGE": env["HEIGHT_PERCENTAGE"],
                        "MOVE_X_PERCENTAGE": env["MOVE_X_PERCENTAGE"],
                    },
                    "check": check,
                }
            )

        with patch("animate.os.makedirs"), patch("animate.subprocess.run", side_effect=fake_run), patch(
            "builtins.print"
        ):
            animate.loop2()

        self.assertEqual(len(captured_calls), 20)
        self.assertEqual(captured_calls[0]["env"]["HEIGHT_PERCENTAGE"], "-100.00")
        self.assertEqual(captured_calls[0]["env"]["MOVE_X_PERCENTAGE"], "0")
        self.assertEqual(captured_calls[-1]["env"]["HEIGHT_PERCENTAGE"], "100.00")
        self.assertEqual(captured_calls[-1]["env"]["MOVE_X_PERCENTAGE"], "0")
        self.assertEqual(captured_calls[0]["command"][-1], "frames/out_0020.png")
        self.assertEqual(captured_calls[-1]["command"][-1], "frames/out_0039.png")
        self.assertTrue(all(call_info["check"] for call_info in captured_calls))

    def test_loop3_renders_expected_frames_and_prints_status(self):
        captured_calls = []

        def fake_run(command, env, check):
            captured_calls.append(
                {
                    "command": list(command),
                    "env": {
                        "HEIGHT_PERCENTAGE": env["HEIGHT_PERCENTAGE"],
                        "MOVE_X_PERCENTAGE": env["MOVE_X_PERCENTAGE"],
                        "OVERRIDE_WHITE": env["OVERRIDE_WHITE"],
                    },
                    "check": check,
                }
            )

        with patch("animate.os.makedirs"), patch("animate.subprocess.run", side_effect=fake_run), patch(
            "builtins.print"
        ) as print_mock:
            animate.loop3()

        self.assertEqual(len(captured_calls), 10)
        self.assertEqual(captured_calls[0]["env"]["HEIGHT_PERCENTAGE"], "0.00")
        self.assertEqual(captured_calls[0]["env"]["MOVE_X_PERCENTAGE"], "0")
        self.assertEqual(captured_calls[0]["env"]["OVERRIDE_WHITE"], "0")
        self.assertEqual(captured_calls[-1]["env"]["HEIGHT_PERCENTAGE"], "-100.00")
        self.assertEqual(captured_calls[-1]["env"]["MOVE_X_PERCENTAGE"], "0")
        self.assertEqual(captured_calls[-1]["env"]["OVERRIDE_WHITE"], "0")
        self.assertEqual(captured_calls[0]["command"][-1], "frames/out_0000.png")
        self.assertEqual(captured_calls[-1]["command"][-1], "frames/out_0009.png")
        print_mock.assert_any_call("Starting render of 10 frames for a full loop...")
        print_mock.assert_any_call("Frame 0000/9 | Height: 0.00 | Dir: UP")
        print_mock.assert_any_call("Frame 0009/9 | Height: -100.00 | Dir: UP")
        print_mock.assert_any_call("Looping render complete!")

    def test_main_runs_loops_in_existing_order(self):
        call_order = []

        with patch("animate.loop3", side_effect=lambda: call_order.append("loop3")), patch(
            "animate.loop1", side_effect=lambda: call_order.append("loop1")
        ), patch("animate.loop2", side_effect=lambda: call_order.append("loop2")):
            animate.main()

        self.assertEqual(call_order, ["loop3", "loop1", "loop2"])


if __name__ == "__main__":
    unittest.main()
