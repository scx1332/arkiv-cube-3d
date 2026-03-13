FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY arkiv_cube_3d /app/arkiv_cube_3d
COPY start_web.py /app/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "arkiv_cube_3d", "web", "--host", "0.0.0.0", "--port", "8000"]
