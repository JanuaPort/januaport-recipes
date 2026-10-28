#!/usr/bin/env bash
set -euo pipefail
rezept=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REZEPT_BASH=$BASH
if command -v cygpath >/dev/null 2>&1; then
  REZEPT_BASH=$(cygpath -w "$BASH")
fi
export REZEPT_BASH
exec "${PYTHON:-python3}" "$rezept/tests.py" "$@"
