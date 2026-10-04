#!/usr/bin/env bash
# Regenera las figuras de la memoria a partir de las especificaciones de archify (src/*.<tipo>.json).
# Requisitos: Node >= 18, Python 3 con playwright y Pillow, y archify en $ARCHIFY
# (por defecto ~/.archify-src/archify, commit 9e35d2b0b39b155553ba9fcfe0b4f2a5198dd993 de github.com/tt-a1i/archify).
set -euo pipefail
cd "$(dirname "$0")"
ARCHIFY="${ARCHIFY:-$HOME/.archify-src/archify}"
HTML_DIR="$(mktemp -d)"
names=()
for spec in src/*.json; do
  base="$(basename "$spec" .json)"   # p. ej. ciclo.architecture
  name="${base%.*}"; type="${base##*.}"
  node "$ARCHIFY/bin/archify.mjs" validate "$type" "$PWD/$spec" --quality showcase --json > /dev/null
  node "$ARCHIFY/bin/archify.mjs" deliver "$type" "$PWD/$spec" "$HTML_DIR/$name.html" --quality showcase --json > /dev/null
  names+=("$name")
done
python3 src/export_png.py "$HTML_DIR" "$PWD" "${names[@]}"
echo "HTML interactivos en $HTML_DIR"
