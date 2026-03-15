import os
import subprocess


RENDER_COMMAND = ["python", "-m", "arkiv_cube_3d", "render"]
INPUT_IMAGE = r".\letters\1_A.png"
OUTPUT_DIR = "frames"
OUTPUT_PREFIX = "out"


def _calculate_height(start_height, end_height, step_index, total_frames):
    progress = step_index / (total_frames - 1)
    return start_height + (end_height - start_height) * progress


def _render_loop(
    *,
    num_steps,
    start_height,
    end_height,
    height_value,
    move_x_value,
    start_frame=0,
    override_white=None,
    print_frame=False,
):
    env = os.environ.copy()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Calculate total frames for a full round trip (0 -> 100 -> 0)
    # We subtract 2 to prevent duplicate frames at the peak (100) and the loop point (0)
    total_frames = num_steps

    print(f"Starting render of {total_frames} frames for a full loop...")

    for i in range(total_frames):
        # Calculate the current percentage for this frame.
        current_height = _calculate_height(start_height, end_height, i, total_frames)

        env["HEIGHT_PERCENTAGE"] = height_value(current_height)
        env["MOVE_X_PERCENTAGE"] = move_x_value(current_height)

        if override_white is not None:
            env["OVERRIDE_WHITE"] = override_white

        frame_no = start_frame + i
        output_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_{frame_no:04d}.png")
        command = [*RENDER_COMMAND, "--image", INPUT_IMAGE, "--output", output_path]

        if print_frame:
            print(
                f"Frame {i:04d}/{total_frames-1} | Height: {current_height:.2f} | "
                f"Dir: {'UP' if i < num_steps else 'DOWN'}"
            )

        try:
            subprocess.run(command, env=env, check=True)
        except subprocess.CalledProcessError as error:
            print(f"Error at frame {i}: {error}")
            break

    print("Looping render complete!")


def loop1():
    # --- Configuration ---
    # Number of frames for ONE WAY (0 to 100).
    # The total animation will be (NUM_STEPS * 2) - 2 frames.
    _render_loop(
        num_steps=10,
        start_height=100.0,
        end_height=0.0,
        height_value=lambda current_height: "-100.0",
        move_x_value=lambda current_height: f"{current_height:.2f}",
        start_frame=10,
    )


def loop2():
    # --- Configuration ---
    # Number of frames for ONE WAY (0 to 100).
    # The total animation will be (NUM_STEPS * 2) - 2 frames.
    _render_loop(
        num_steps=20,
        start_height=-100.0,
        end_height=100.0,
        height_value=lambda current_height: f"{current_height:.2f}",
        move_x_value=lambda current_height: "0",
        start_frame=20,
    )


def loop3():
    # --- Configuration ---
    # Number of frames for ONE WAY (0 to 100).
    # The total animation will be (NUM_STEPS * 2) - 2 frames.
    _render_loop(
        num_steps=10,
        start_height=0.0,
        end_height=-100.0,
        height_value=lambda current_height: f"{current_height:.2f}",
        move_x_value=lambda current_height: "0",
        override_white="0",
        print_frame=True,
    )


def main():
    loop3()
    loop1()
    loop2()


if __name__ == "__main__":
    main()
