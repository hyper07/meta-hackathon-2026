# Watch Me server: the web app, the agents and the local speech models (Whisper, ECAPA), CPU only.
#
#   docker compose up --build        then open http://localhost:8000
#
# Keys come from .env at run time (compose.yaml); they are never copied into the image.
# Without keys it still runs: phrase list, fixed rules and dry-run alerts.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    HF_HOME=/models/huggingface

WORKDIR /srv/app

# Dependencies first, so code changes don't reinstall torch. On Linux the lock pins CPU-only torch.
COPY app/pyproject.toml app/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app/watchme ./watchme
COPY app/static ./static
COPY app/demo_seed ./demo_seed

# The voiceprint model is saved next to the app (.models/ecapa); keep it with Whisper on one volume.
RUN mkdir -p /data /models/ecapa && ln -s /models .models

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["uvicorn", "watchme.main:app", "--host", "0.0.0.0", "--port", "8000"]
