"""Simple browser UI for tweaking render parameters."""

from dataclasses import asdict, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from .render_cube import (
    DEFAULT_RENDER_PARAMETERS,
    FULL_RES_RENDER_PARAMETERS,
    PREVIEW_RENDER_PARAMETERS,
    RenderParameters,
    is_bpy_available,
    render_scene,
)

RENDER_OUTPUT_DIR = Path.cwd() / "web_renders"


def clamp(value, lower, upper):
    """Clamp a numeric value to a range."""
    return max(lower, min(upper, value))


def hex_to_rgba(color_value):
    """Convert a #RRGGBB value to Blender RGBA floats."""
    color_value = color_value.strip().lstrip("#")
    if len(color_value) != 6:
        raise ValueError("Color must be in #RRGGBB format.")

    channels = [int(color_value[index : index + 2], 16) / 255.0 for index in range(0, 6, 2)]
    return (channels[0], channels[1], channels[2], 1.0)


def build_render_parameters(payload, profile="preview"):
    """Build render parameters from the request payload and render profile."""
    if profile not in {"preview", "full"}:
        raise ValueError("Profile must be either 'preview' or 'full'.")

    base = PREVIEW_RENDER_PARAMETERS if profile == "preview" else FULL_RES_RENDER_PARAMETERS
    return replace(
        base,
        box_color=hex_to_rgba(payload.get("box_color", "#cc5a00")),
        box_roughness=clamp(float(payload.get("box_roughness", base.box_roughness)), 0.0, 1.0),
        box_metallic=clamp(float(payload.get("box_metallic", base.box_metallic)), 0.0, 1.0),
        box_specular=clamp(float(payload.get("box_specular", base.box_specular)), 0.0, 1.0),
        box_emission_strength=clamp(float(payload.get("box_emission_strength", base.box_emission_strength)), 0.0, 5.0),
        floor_roughness=clamp(float(payload.get("floor_roughness", base.floor_roughness)), 0.0, 1.0),
        world_strength=clamp(float(payload.get("world_strength", base.world_strength)), 0.0, 5.0),
        key_light_energy=clamp(float(payload.get("key_light_energy", base.key_light_energy)), 0.0, 5000.0),
        fill_light_energy=clamp(float(payload.get("fill_light_energy", base.fill_light_energy)), 1500.0, 5000.0),
        rim_light_energy=clamp(float(payload.get("rim_light_energy", base.rim_light_energy)), 0.0, 5000.0),
    )


def render_with_profile(payload, profile):
    """Render with the supplied profile and return the image path."""
    params = build_render_parameters(payload, profile=profile)
    RENDER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{profile}-{int(time.time() * 1000)}.png"
    output_path = RENDER_OUTPUT_DIR / file_name
    render_scene(params, output_path=str(output_path))
    return file_name, output_path.with_suffix(".blend").name, params


def default_form_values():
    """Return the initial values for the browser form."""
    params = asdict(DEFAULT_RENDER_PARAMETERS)
    params["box_color"] = "#cc5a00"
    return params


def render_page():
    """Return the HTML for the simple control panel."""
    defaults = default_form_values()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>arkiv cube 3d</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Arial, sans-serif;
    }}
    body {{
      margin: 0;
      background: #111827;
      color: #f9fafb;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(320px, 420px) 1fr;
      min-height: 100vh;
    }}
    .panel {{
      padding: 24px;
      background: #1f2937;
      box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.08);
      overflow-y: auto;
    }}
    .panel h1 {{
      margin-top: 0;
      font-size: 1.5rem;
    }}
    .hint {{
      color: #cbd5e1;
      font-size: 0.95rem;
      line-height: 1.5;
    }}
    .field {{
      margin-bottom: 16px;
    }}
    .field label {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-size: 0.95rem;
    }}
    input[type="range"], input[type="color"] {{
      width: 100%;
    }}
    .buttons {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 24px;
    }}
    button {{
      border: none;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .preview-btn {{
      background: #f59e0b;
      color: #111827;
    }}
    .full-btn {{
      background: #38bdf8;
      color: #082f49;
    }}
    .viewer {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: #0f172a;
    }}
    .viewer-inner {{
      width: min(100%, 960px);
    }}
    .status {{
      min-height: 24px;
      margin-bottom: 12px;
      color: #e2e8f0;
    }}
    .download-link {{
      display: none;
      margin-bottom: 12px;
      color: #93c5fd;
      font-weight: 600;
    }}
    img {{
      width: 100%;
      border-radius: 12px;
      background: repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 50% / 24px 24px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
    }}
    @media (max-width: 960px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <section class="panel">
      <h1>Cube material controls</h1>
      <p class="hint">Adjust the material, world, and lighting parameters, then draw a preview or a full-resolution render.</p>

      <div class="field">
        <label for="box_color"><span>Color</span><span id="box_color_value">{defaults["box_color"]}</span></label>
        <input id="box_color" name="box_color" type="color" value="{defaults["box_color"]}">
      </div>
      <div class="field">
        <label for="box_roughness"><span>Roughness</span><span id="box_roughness_value">{defaults["box_roughness"]:.2f}</span></label>
        <input id="box_roughness" name="box_roughness" type="range" min="0" max="1" step="0.01" value="{defaults["box_roughness"]}">
      </div>
      <div class="field">
        <label for="box_metallic"><span>Metallic</span><span id="box_metallic_value">{defaults["box_metallic"]:.2f}</span></label>
        <input id="box_metallic" name="box_metallic" type="range" min="0" max="1" step="0.01" value="{defaults["box_metallic"]}">
      </div>
      <div class="field">
        <label for="box_specular"><span>Specular</span><span id="box_specular_value">{defaults["box_specular"]:.2f}</span></label>
        <input id="box_specular" name="box_specular" type="range" min="0" max="1" step="0.01" value="{defaults["box_specular"]}">
      </div>
      <div class="field">
        <label for="box_emission_strength"><span>Emission</span><span id="box_emission_strength_value">{defaults["box_emission_strength"]:.2f}</span></label>
        <input id="box_emission_strength" name="box_emission_strength" type="range" min="0" max="5" step="0.05" value="{defaults["box_emission_strength"]}">
      </div>
      <div class="field">
        <label for="floor_roughness"><span>Floor roughness</span><span id="floor_roughness_value">{defaults["floor_roughness"]:.2f}</span></label>
        <input id="floor_roughness" name="floor_roughness" type="range" min="0" max="1" step="0.01" value="{defaults["floor_roughness"]}">
      </div>
      <div class="field">
        <label for="world_strength"><span>Background strength</span><span id="world_strength_value">{defaults["world_strength"]:.2f}</span></label>
        <input id="world_strength" name="world_strength" type="range" min="0" max="5" step="0.05" value="{defaults["world_strength"]}">
      </div>
      <div class="field">
        <label for="key_light_energy"><span>Key light</span><span id="key_light_energy_value">{defaults["key_light_energy"]:.0f}</span></label>
        <input id="key_light_energy" name="key_light_energy" type="range" min="0" max="1500" step="10" value="{defaults["key_light_energy"]}">
      </div>
      <div class="field">
        <label for="fill_light_energy"><span>Fill light</span><span id="fill_light_energy_value">{defaults["fill_light_energy"]:.0f}</span></label>
        <input id="fill_light_energy" name="fill_light_energy" type="range" min="0" max="5000" step="10" value="{defaults["fill_light_energy"]}">
      </div>
      <div class="field">
        <label for="rim_light_energy"><span>Rim light</span><span id="rim_light_energy_value">{defaults["rim_light_energy"]:.0f}</span></label>
        <input id="rim_light_energy" name="rim_light_energy" type="range" min="0" max="1500" step="10" value="{defaults["rim_light_energy"]}">
      </div>

      <div class="buttons">
        <button class="preview-btn" id="preview_button" type="button">Draw preview</button>
        <button class="full-btn" id="full_button" type="button">Draw full resolution</button>
      </div>
    </section>

    <section class="viewer">
      <div class="viewer-inner">
        <div class="status" id="status">Ready to render.</div>
        <a class="download-link" id="blend_download" download>Download scene (.blend)</a>
        <img id="rendered_image" alt="Latest render preview" style="display: none;">
      </div>
    </section>
  </div>

  <script>
    const formFields = ["box_color", "box_roughness", "box_metallic", "box_specular", "box_emission_strength", "floor_roughness", "world_strength", "key_light_energy", "fill_light_energy", "rim_light_energy"];

    function updateFieldValue(fieldName) {{
      const input = document.getElementById(fieldName);
      document.getElementById(`${{fieldName}}_value`).textContent = input.value;
    }}

    for (const fieldName of formFields) {{
      const input = document.getElementById(fieldName);
      input.addEventListener("input", () => updateFieldValue(fieldName));
      updateFieldValue(fieldName);
    }}

    async function draw(profile) {{
      const status = document.getElementById("status");
      const image = document.getElementById("rendered_image");
      const blendDownload = document.getElementById("blend_download");
      status.textContent = profile === "preview"
        ? "Rendering preview…"
        : "Rendering full-resolution image…";
      blendDownload.style.display = "none";

      const payload = Object.fromEntries(formFields.map((fieldName) => [fieldName, document.getElementById(fieldName).value]));

      try {{
        const response = await fetch("/api/render", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{profile, params: payload}})
        }});
        const result = await response.json();

        if (!response.ok) {{
          throw new Error(result.error || "Render failed.");
        }}

        image.src = `${{result.image_url}}?ts=${{Date.now()}}`;
        image.style.display = "block";
        blendDownload.style.display = "inline-block";
        status.textContent = result.message;
      }} catch (error) {{
        image.style.display = "none";
        blendDownload.style.display = "none";
        status.textContent = error.message;
      }}
    }}

    document.getElementById("preview_button").addEventListener("click", () => draw("preview"));
    document.getElementById("full_button").addEventListener("click", () => draw("full"));
  </script>
</body>
</html>"""


class RenderRequestHandler(BaseHTTPRequestHandler):
    """Serve the control panel and render endpoints."""

    def do_GET(self):
        request_path = urlsplit(self.path).path

        if request_path in {"/", "/index.html"}:
            page = render_page().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        if request_path.startswith("/renders/"):
            output_path = (RENDER_OUTPUT_DIR / request_path.removeprefix("/renders/")).resolve()
            if output_path.parent != RENDER_OUTPUT_DIR.resolve() or not output_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "Render not found.")
                return

            content_type = "image/png" if output_path.suffix.lower() == ".png" else "application/octet-stream"
            content = output_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found.")

    def do_POST(self):
        if urlsplit(self.path).path != "/api/render":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found.")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length) or b"{}")
            profile = payload.get("profile", "preview")
            params = payload.get("params", {})

            if not is_bpy_available():
                raise RuntimeError(
                    "bpy is not available in this environment, so rendering cannot start. "
                    "Run the server through Blender or install the bpy package first."
                )

            image_name, blend_name, render_params = render_with_profile(params, profile)
            response = {
                "image_url": f"/renders/{image_name}",
                "blend_url": f"/renders/{blend_name}",
                "message": (
                    f"Finished {profile} render at "
                    f"{render_params.resolution_x}×{render_params.resolution_y} with {render_params.samples} samples."
                ),
            }
            self.respond_json(HTTPStatus.OK, response)
        except (TypeError, ValueError, RuntimeError) as error:
            self.respond_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def log_message(self, format_string, *args):
        """Suppress default HTTP request logging to keep console output clean."""
        return

    def respond_json(self, status, payload):
        """Return a JSON response."""
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main(host="127.0.0.1", port=8000):
    """Run the local parameter-tweaking web server."""
    server = ThreadingHTTPServer((host, port), RenderRequestHandler)
    print(f"Serving control panel at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
