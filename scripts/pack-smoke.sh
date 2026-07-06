#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NJ_REPO="${NJ_REPO:-$(cd "${ROOT}/../neural-junkie" && pwd)}"
FIXTURE="${ROOT}/scenarios/fixtures/minimal-site"
HUB_URL="${HUB_URL:-http://127.0.0.1:8080}"

export NJ_BROWSER_SMOKE_FIXTURE="${FIXTURE}"
export NEURAL_JUNKIE_SCENARIO_REPO="${FIXTURE}"

echo "==> pack-smoke: sidecar health"
HUB_URL="${HUB_URL}" "${ROOT}/scripts/pack-smoke.sh"

if [[ -d "${NJ_REPO}/scripts" ]]; then
  echo "==> pack-smoke: browser-preview-smoke scenario"
  NJ_PACK_SCENARIOS_DIR="${ROOT}/scenarios/collab" \
    python3 "${NJ_REPO}/scripts/collab-scenarios.py" \
    --hub "${HUB_URL}" \
    --scenario browser-preview-smoke \
    --pack-dir "${ROOT}" \
    || {
      echo "pack-smoke: scenario skipped (hub/agents may be offline)" >&2
    }
fi

echo "pack-smoke: done"
