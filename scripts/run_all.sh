#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BLENDER_BIN=${BLENDER_BIN:-/Applications/Blender.app/Contents/MacOS/Blender}
mkdir -p "$PROJECT_DIR/reports/logs"
"$BLENDER_BIN" --background --factory-startup --python-exit-code 1 --python "$PROJECT_DIR/scripts/build.py" > "$PROJECT_DIR/reports/logs/build.log" 2>&1
"$BLENDER_BIN" --background "$PROJECT_DIR/models/MORI_assembly.blend" --python-exit-code 1 --python "$PROJECT_DIR/scripts/render.py" -- --views all > "$PROJECT_DIR/reports/logs/render.log" 2>&1
"$BLENDER_BIN" --background "$PROJECT_DIR/models/MORI_assembly.blend" --python-exit-code 1 --python "$PROJECT_DIR/scripts/export.py" > "$PROJECT_DIR/reports/logs/export.log" 2>&1
"$BLENDER_BIN" --background "$PROJECT_DIR/models/MORI_assembly.blend" --python-exit-code 1 --python "$PROJECT_DIR/scripts/validate.py" > "$PROJECT_DIR/reports/logs/validate.log" 2>&1
printf '%s\n' 'MORI finished. Read reports/validation.md before slicing.'
