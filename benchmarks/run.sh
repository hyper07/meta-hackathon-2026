#!/usr/bin/env bash
# Run Watch Me's benchmarks again (see benchmarks/README.md). Alerts are always a dry run here.
#
#   ./benchmarks/run.sh            the phrase-list baseline, on the scenes and on their scripts (no keys)
#   ./benchmarks/run.sh --agents   also the Muse agents (live and with perfect hearing) and the
#                                  Notice reviewer on the 40 public cases and our 16 (MODEL_API_KEY)
set -euo pipefail
cd "$(dirname "$0")/../app"

uv sync --frozen --all-groups
if [[ ! -f scenarios/out/manifest.json ]]; then
  echo "Rendering the 22 scenes (first run only)..."
  uv run python -m scenarios.build
fi

uv run python -m scenarios.evaluate --phrases-only
uv run python -m scenarios.evaluate --phrases-only --hearing=script

if [[ "${1:-}" == "--agents" ]]; then
  uv run python -m scenarios.evaluate
  uv run python -m scenarios.evaluate --hearing=script
  uv run python -m scenarios.notice_eval --training
  uv run python -m scenarios.notice_eval
fi

echo "Results: app/scenarios/results/ (newest files)"
