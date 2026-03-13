# arkiv-cube-3d

Render a 3D orange cube on a white background with nice lighting and Cycles ray tracing using Blender.

## Prerequisites

- Python 3.11+
- [Blender](https://www.blender.org/) installed on your machine

## Installation

```bash
pip install bpy
```

## Run with Docker

Build and start the web server with Docker Compose:

```bash
docker compose up --build
```

Then open http://127.0.0.1:8000.

The container uses Python 3.11 to match the project's Blender / `bpy` requirements.

## Usage

You can also run the package directly with Python's -m switch which dispatches to a small CLI. By default this starts the local web control panel (safe when bpy is unavailable):

```bash
python -m arkiv_cube_3d
# or explicitly:
python -m arkiv_cube_3d web
python -m arkiv_cube_3d render  # requires bpy / Blender
python -m arkiv_cube_3d render --input cubes.json
```

If you're running from a source checkout and want a simple script instead of `-m`, use:

```bash
python start_web.py
```

If you prefer Docker without Compose:

```bash
docker build -t arkiv-cube-3d .
docker run --rm -p 8000:8000 arkiv-cube-3d
```

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

To render cubes from a JSON input file, pass the file to the render command:

```bash
python -m arkiv_cube_3d render --input cubes.json
```

Example `cubes.json`:

```json
{
  "count": 3,
  "positions": [
    [0, -10, 1.0],
    [0, -6, 1.0],
    [-10, 0, 1.0]
  ]
}
```

### Run the local web control panel

You can also start a lightweight local web server for tweaking the cube material and lighting in the browser:

```bash
render-cube-web
# or from a source checkout:
python start_web.py
```

Then open <http://127.0.0.1:8000> and use the panel to:

- tweak cube color, roughness, metallic/specular/emission and scene lighting
- click **Draw preview** for a quick lower-sample render
- click **Draw full resolution** for a 1920×1080 render
- download the generated `.blend` scene file for the latest render

## GitHub Actions

A workflow is included that automatically renders the cube on push/PR to `main`. It:

1. Sets up Python 3.11
2. Installs Blender and bpy via apt and pip
3. Runs the render script
4. Uploads the rendered image and `.blend` scene as build artifacts

## Output

The script renders `orange_cube.png` (1920×1080) and saves the matching scene as `orange_cube.blend` in the current directory — an orange cube on a white background with three-point area lighting and Cycles ray tracing (128 samples with denoising).
