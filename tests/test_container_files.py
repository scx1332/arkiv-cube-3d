import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class ContainerFilesTests(unittest.TestCase):
    def test_pyproject_requires_python_311(self):
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.11")

    def test_dockerfile_runs_web_server_on_python_311(self):
        dockerfile = (REPO_ROOT / "Dockerfile").read_text()

        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn("EXPOSE 8000", dockerfile)
        self.assertIn('"python", "-m", "arkiv_cube_3d", "web"', dockerfile)
        self.assertIn('"0.0.0.0"', dockerfile)

    def test_docker_compose_exposes_web_server(self):
        compose = (REPO_ROOT / "docker-compose.yml").read_text()

        self.assertIn('ports:', compose)
        self.assertIn('"8000:8000"', compose)
        self.assertIn('command:', compose)
        self.assertIn('arkiv_cube_3d', compose)
        self.assertIn('--host', compose)
        self.assertIn('0.0.0.0', compose)

    def test_dockerignore_ignores_common_build_artifacts(self):
        dockerignore = (REPO_ROOT / ".dockerignore").read_text().splitlines()

        self.assertIn(".git", dockerignore)
        self.assertIn("__pycache__/", dockerignore)
        self.assertIn("dist/", dockerignore)

    def test_render_workflow_uses_matrix_with_unique_outputs(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "render.yml").read_text()

        self.assertIn("letters/1_A.png", workflow)
        self.assertIn("letters/2_R.png", workflow)
        self.assertIn("Render preview for ${{ matrix.image_name }}", workflow)
        self.assertIn("Render full image for ${{ matrix.image_name }}", workflow)
        self.assertIn('python -m arkiv_cube_3d render --image "${{ matrix.image_path }}"', workflow)
        self.assertIn('python -m arkiv_cube_3d render --image "${{ matrix.image_path }}" --full', workflow)
        self.assertIn('mv orange_cube.png "${{ matrix.image_name }}_preview.png"', workflow)
        self.assertIn('mv orange_cube.blend "${{ matrix.image_name }}_preview.blend"', workflow)
        self.assertIn('mv orange_cube.png "${{ matrix.image_name }}_full.png"', workflow)
        self.assertIn('mv orange_cube.blend "${{ matrix.image_name }}_full.blend"', workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", workflow)
        self.assertIn("data:image/png;base64,", workflow)
        self.assertIn("letters-${{ matrix.image_name }}", workflow)


if __name__ == "__main__":
    unittest.main()
