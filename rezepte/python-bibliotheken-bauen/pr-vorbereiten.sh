#!/usr/bin/env bash
# Nur lokalen Commit vorbereiten. Push und PR geschehen ausschließlich im Workflow.
set -euo pipefail
rezept=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ordner=$1
artefakt=$2
zweig=$3
ziel=$4
"${PYTHON:-python3}" "$rezept/bauen.py" --workflow-ordner "$ordner"
"${PYTHON:-python3}" "$rezept/bauen.py" --pr-zweig "$zweig"
# Der Aufrufer bildet den Zweig ausschließlich aus den numerischen Laufkennungen.
git switch -c "$zweig"
mkdir -p -- "$ordner"
rm -rf -- "$ordner/wheels"
cp -R -- "$artefakt/wheels" "$ordner/wheels"
cp -- "$artefakt/requirements.lock" "$ordner/requirements.lock"
bash "$rezept/bauen.sh" --pruefen "$ordner" "$ziel"
git add -f -- "$ordner/requirements.lock" "$ordner/wheels"
if git diff --cached --quiet; then
  printf 'Keine Änderung an Lock und Wheels.\n'
else
  git commit -m "Python-Bibliotheken aktualisieren ($ziel)"
fi
