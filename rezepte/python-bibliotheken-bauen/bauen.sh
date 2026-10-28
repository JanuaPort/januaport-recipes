#!/usr/bin/env bash
set -euo pipefail

rezept=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python=${PYTHON:-python3}
exec "$python" "$rezept/bauen.py" "$@"
