#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
fail() { echo "verify-pack: $*" >&2; exit 1; }
[[ -f pack.yaml ]] || fail "missing pack.yaml"
id="$(grep '^id:' pack.yaml | head -1 | awk '{print $2}')"
ver="$(grep '^version:' pack.yaml | head -1 | awk -F'"' '{print $2}')"
[[ -n "${id}" ]] || fail "pack.yaml missing id"
[[ -n "${ver}" ]] || fail "pack.yaml missing version"
"${ROOT}/scripts/build-pack-zip.sh" >/dev/null
echo "OK pack ${id} ${ver}"
