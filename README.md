# arkiv-cube-3d

Render a 3D orange cube on a white background with nice lighting and Cycles ray tracing using Blender.

## Prerequisites

- Python 3.10+
- [Blender](https://www.blender.org/) installed on your machine
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

```bash
poetry install
```

## Usage

### Run via Blender CLI (recommended)

Since the script uses the `bpy` module, the simplest way to run it is through Blender's built-in Python:

```bash
blender --background --python arkiv_cube_3d/render_cube.py
```

### Run via Poetry (requires `bpy` PyPI package)

If the `bpy` package installs successfully in your environment:

```bash
poetry run render-cube
```

## Output

The script renders `orange_cube.png` (1920×1080) in the current directory — an orange cube on a white background with three-point area lighting and Cycles ray tracing (128 samples with denoising).
