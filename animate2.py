import subprocess
import os
import math

# --- Configuration ---
# Number of frames for ONE WAY (0 to 100).
# The total animation will be (NUM_STEPS * 2) - 2 frames.
NUM_STEPS = 20
START_HEIGHT = -100.0
END_HEIGHT = 100.0
INPUT_IMAGE = r".\letters\1_A.png"
OUTPUT_DIR = "frames"
OUTPUT_PREFIX = "out"
START_FRAME = 20

def ease_in_out_sine(x: float) -> float:
    """
    Easing function: smooth start and smooth end.
    x should be between 0.0 and 1.0
    """
    return -(math.cos(math.pi * x) - 1.0) / 2.0

def main():
    env = os.environ.copy()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Calculate total frames for a full round trip (0 -> 100 -> 0)
    # We subtract 2 to prevent duplicate frames at the peak (100) and the loop point (0)
    total_frames = NUM_STEPS

    print(f"Starting render of {total_frames} frames for a full loop...")

    for i in range(total_frames):
        # 1. Calculate linear progress (0.0 to 1.0 for the whole animation)
        # However, we want the 'height' to peak at the middle.
        # 2. Apply easing to the oscillating t
        eased_t = i / (total_frames - 1)

        # 3. Calculate current height percentage
        current_height = START_HEIGHT + (END_HEIGHT - START_HEIGHT) * eased_t

        # Update environment
        env["HEIGHT_PERCENTAGE"] = f"{current_height:.2f}"
        env["MOVE_X_PERCENTAGE"] = f"0"
        frame_no = START_FRAME + i

        output_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}_{frame_no:04d}.png")

        command = [
            "python", "-m", "arkiv_cube_3d", "render",
            "--image", INPUT_IMAGE,
            "--output", output_path
        ]

        try:
            subprocess.run(command, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error at frame {i}: {e}")
            break

    print("Looping render complete!")

if __name__ == "__main__":
    main()