# arkiv-cube-3d

Render a 3D orange cube on a white background with nice lighting and Cycles ray tracing using Blender.

## Prerequisites

- Python 3.11+
- [Blender](https://www.blender.org/) installed on your machine

## Installation

```bash
pip install bpy
```

## Usage

### Run via Blender CLI (recommended)

Since the script uses the `bpy` module, the simplest way to run it is through Blender's built-in Python:

```bash
blender --background --python arkiv_cube_3d/render_cube.py
```

### Run directly with pip-installed bpy

If the `bpy` package installs successfully in your environment:

```bash
pip install bpy
python arkiv_cube_3d/render_cube.py
```

## GitHub Actions

A workflow is included that automatically renders the cube on push/PR to `main`. It:

1. Sets up Python 3.11
2. Installs Blender and bpy via apt and pip
3. Runs the render script
4. Uploads the rendered image as a build artifact

## Output

The script renders `orange_cube.png` (1920×1080) in the current directory — an orange cube on a white background with three-point area lighting and Cycles ray tracing (128 samples with denoising).
