#!/usr/bin/env bash
set -euo pipefail
rezept=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${PYTHON:-python3}" -I -B -m unittest discover -s "$rezept" -p tests.py "$@"
