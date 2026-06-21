#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/dist"
mkdir -p "$OUT"
id="$(grep '^id:' "${ROOT}/pack.yaml" | head -1 | awk '{print $2}')"
ver="$(grep '^version:' "${ROOT}/pack.yaml" | head -1 | awk -F'"' '{print $2}')"
artifact="${OUT}/${id}-${ver}.zip"
rm -f "${artifact}"
(cd "${ROOT}" && zip -r "${artifact}" pack.yaml -x '*.DS_Store')
[[ -d "${ROOT}/assets" ]] && (cd "${ROOT}" && zip -ur "${artifact}" assets -x '*.DS_Store')
echo "Wrote ${artifact}"
