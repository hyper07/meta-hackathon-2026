#!/usr/bin/env bash
# Muse Spark Open (open weights, on a Modal shared endpoint) against the hosted Muse models, on the same
# tests: the 22 scenes with perfect hearing (the agents' judgment alone), and the Notice reviewer on the
# 40 public training cases and our 16. Needs MODAL_PROXY_TOKEN and OPEN_WEIGHTS_MODEL in .env.
# Alerts are always a dry run. Results go to app/scenarios/results/ with "open" in the name of the run.
set -euo pipefail
cd "$(dirname "$0")/../app"

# The hosted runs to compare with are already in app/scenarios/results/ (see benchmarks/README.md).
ANALYST_MODEL=open DECIDER_MODEL=open uv run python -m scenarios.evaluate --hearing=script
REVIEWER_MODEL=open uv run python -m scenarios.notice_eval --training
REVIEWER_MODEL=open uv run python -m scenarios.notice_eval
echo "Results: app/scenarios/results/ (newest files)"
