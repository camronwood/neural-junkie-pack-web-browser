#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BROWSER_DIR="${HOME}/.neural-junkie/browser"
VENV="${BROWSER_DIR}/venv"
PYTHON="${PYTHON:-python3}"

echo "==> Web browser pack: Playwright setup"
mkdir -p "${BROWSER_DIR}"

if [[ ! -d "${VENV}" ]]; then
  echo "Creating venv at ${VENV}"
  "${PYTHON}" -m venv "${VENV}"
fi

# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install --upgrade pip
pip install playwright pillow

export PLAYWRIGHT_BROWSERS_PATH="${BROWSER_DIR}/playwright-browsers"
mkdir -p "${PLAYWRIGHT_BROWSERS_PATH}"
playwright install chromium

echo ""
echo "OK Playwright ready."
echo "  venv:     ${VENV}"
echo "  browsers: ${PLAYWRIGHT_BROWSERS_PATH}"
echo ""
echo "Set in Domain packs settings (or pack.yaml overlay):"
echo "  python_executable: ${VENV}/bin/python3"
echo "  playwright_browsers_path: ${PLAYWRIGHT_BROWSERS_PATH}"
