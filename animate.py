import subprocess
import os
import math

# --- Configuration ---
NUM_FRAMES = 60           # Total number of frames for the animation
START_HEIGHT = 0.0        # Starting value for HEIGHT_PERCENTAGE
END_HEIGHT = 100.0        # Ending value for HEIGHT_PERCENTAGE
INPUT_IMAGE = r".\letters\1_A.png"
OUTPUT_DIR = "frames"     # Subfolder to store the rendered frames
OUTPUT_PREFIX = "out"

def ease_in_out_sine(x: float) -> float:
    """
    Easing function: smooth start and smooth end.
    x should be between 0.0 and 1.0
    """
    return -(math.cos(math.pi * x) - 1.0) / 2.0

def main():
    # Copy the current environment variables
    env = os.environ.copy()

    # Create the output subfolder if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output folder '{OUTPUT_DIR}' is ready.")
    print(f"Starting render of {NUM_FRAMES} frames...")

    for i in range(NUM_FRAMES):
        # 1. Calculate progress (0.0 to 1.0)
        t = i / (NUM_FRAMES - 1) if NUM_FRAMES > 1 else 1.0

        # 2. Apply easing
        eased_t = ease_in_out_sine(t)

        # 3. Calculate current height percentage
        current_height = START_HEIGHT + (END_HEIGHT - START_HEIGHT) * eased_t

        # Update the environment variable
        env["HEIGHT_PERCENTAGE"] = f"{current_height:.2f}"

        # 4. Format output filename and join with the subfolder path
        output_filename = f"{OUTPUT_PREFIX}_{i:04d}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Build the command
        command = [
            "python", "-m", "arkiv_cube_3d", "render",
            "--image", INPUT_IMAGE,
            "--output", output_path
        ]

        print(f"Rendering frame {i:04d} / {NUM_FRAMES-1} | HEIGHT_PERCENTAGE: {current_height:.2f}")

        # Run the command with the modified environment
        try:
            subprocess.run(command, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error rendering frame {i}: {e}")
            break

    print("Rendering complete!")

if __name__ == "__main__":
    main()