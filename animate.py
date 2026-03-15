import math
import os
import subprocess

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


def create_render_environment():
    """Return a copy of the current environment for rendering."""
    return os.environ.copy()


def ensure_output_dir():
    """Create the output directory if it does not already exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output folder '{OUTPUT_DIR}' is ready.")


def calculate_progress(frame_index: int) -> float:
    """Return the current frame progress as a value between 0.0 and 1.0."""
    return frame_index / (NUM_FRAMES - 1) if NUM_FRAMES > 1 else 1.0


def calculate_height_percentage(frame_index: int) -> float:
    """Return the current HEIGHT_PERCENTAGE value for a frame."""
    progress = calculate_progress(frame_index)
    eased_progress = ease_in_out_sine(progress)
    return START_HEIGHT + (END_HEIGHT - START_HEIGHT) * eased_progress


def build_output_path(frame_index: int) -> str:
    """Return the output path for the frame image."""
    output_filename = f"{OUTPUT_PREFIX}_{frame_index:04d}.png"
    return os.path.join(OUTPUT_DIR, output_filename)


def build_render_command(output_path: str) -> list[str]:
    """Return the command used to render a single frame."""
    return [
        "python", "-m", "arkiv_cube_3d", "render",
        "--image", INPUT_IMAGE,
        "--output", output_path,
    ]


def render_frame(frame_index: int, env):
    """Render a single frame and return whether it succeeded."""
    current_height = calculate_height_percentage(frame_index)
    env["HEIGHT_PERCENTAGE"] = f"{current_height:.2f}"

    output_path = build_output_path(frame_index)
    command = build_render_command(output_path)

    print(f"Rendering frame {frame_index:04d} / {NUM_FRAMES-1} | HEIGHT_PERCENTAGE: {current_height:.2f}")

    try:
        subprocess.run(command, env=env, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Error rendering frame {frame_index}: {error}")
        return False

    return True


def main():
    env = create_render_environment()
    ensure_output_dir()
    print(f"Starting render of {NUM_FRAMES} frames...")

    for frame_index in range(NUM_FRAMES):
        if not render_frame(frame_index, env):
            break

    print("Rendering complete!")


if __name__ == "__main__":
    main()
