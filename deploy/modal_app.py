"""
The live demo on Modal: the Watch Me server as a public web app, in demo mode.

    MODAL_TOKEN_ID=... MODAL_TOKEN_SECRET=... uvx modal deploy deploy/modal_app.py

Demo mode (app/watchme/config.py, DEMO_MODE=1): one visitor at a time, 10 minutes each; only that
visitor's page may use the API; alerts are always a dry run and no audio is kept, whatever else is
set; everything the visitor left is wiped when they go.

Only the model keys leave this machine: the Meta Model API key (MODEL_API_KEY or META_API_KEY), and, if
set, the Muse Spark Open backup's key (BASETEN_API_KEY, or OPEN_WEIGHTS_API_KEY / MODAL_PROXY_TOKEN). They're
read from the environment or .env and sent to Modal as this app's secret. Twilio, SMTP and any other keys
in .env are never sent, so the demo couldn't text or call anyone even by mistake.

One container serves everyone (max_containers=1), because the demo keeps its one visit in memory.
It runs on the CPU, with Whisper and the voiceprint model baked into the image.
"""
import os
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = "/root/app"


def env_value(*names: str) -> str:
    """One setting from the environment, or from its line in .env; empty if it isn't set."""
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() in names and value.strip():
                return value.strip().strip('"').strip("'")
    return ""


def meta_key() -> str:
    """The Meta Model API key, from the environment or from the one matching line in .env."""
    for name in ("MODEL_API_KEY", "META_API_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() in ("MODEL_API_KEY", "META_API_KEY") and value.strip():
                return value.strip().strip('"').strip("'")
    raise SystemExit("no MODEL_API_KEY or META_API_KEY: the demo needs it for the Muse agents")


def bake_models() -> None:
    """Download Whisper and the ECAPA voiceprint model at build time, so a visit never waits for them."""
    import sys

    sys.path.insert(0, APP_DIR)
    from watchme import speech

    speech.warm_up()


image = (
    modal.Image.debian_slim(python_version="3.12")
    .env({"UV_PROJECT_ENVIRONMENT": "/usr/local", "HF_HOME": "/root/models/huggingface"})
    .uv_sync(str(ROOT / "app"), frozen=True)            # the same lock as Docker: CPU-only torch on Linux
    .add_local_dir(str(ROOT / "app" / "watchme"), f"{APP_DIR}/watchme", copy=True, ignore=["__pycache__"])
    .add_local_dir(str(ROOT / "app" / "static"), f"{APP_DIR}/static", copy=True)
    .add_local_dir(str(ROOT / "app" / "demo_seed"), f"{APP_DIR}/demo_seed", copy=True)
    .run_function(bake_models)
    .env({"DEMO_MODE": "1", "DEMO_VISIT_S": "600", "DATA_DIR": "/tmp/watchme-data", "RECORDING_RULE": "all-party"})
)

app = modal.App("watch-me-demo")
def secrets_for_the_demo() -> dict:
    """The Meta Model API key, and the Muse Spark Open backup's key (Baseten by default) if it's set.
    Nothing else from .env is sent."""
    values = {"MODEL_API_KEY": meta_key()}
    open_key = env_value("OPEN_WEIGHTS_API_KEY", "BASETEN_API_KEY", "MODAL_PROXY_TOKEN")
    if open_key:
        values.update(OPEN_WEIGHTS_API_KEY=open_key,
                      OPEN_WEIGHTS_BASE=env_value("OPEN_WEIGHTS_BASE") or "https://inference.baseten.co/v1",
                      OPEN_WEIGHTS_MODEL=env_value("OPEN_WEIGHTS_MODEL") or "meta-models/muse-spark-open")
    return values


secret = modal.Secret.from_dict(secrets_for_the_demo()) if modal.is_local() else modal.Secret.from_dict({})


@app.function(image=image, secrets=[secret], cpu=2.0, memory=4096, timeout=3600,
              min_containers=1, max_containers=1, scaledown_window=1200)
@modal.concurrent(max_inputs=64)
@modal.asgi_app()
def web():
    import sys

    sys.path.insert(0, APP_DIR)
    from watchme.main import app as watchme_app

    return watchme_app
