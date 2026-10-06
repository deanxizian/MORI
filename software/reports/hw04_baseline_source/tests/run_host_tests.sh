#!/bin/sh
set -eu
MORI_HARDWARE_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
mkdir -p "$MORI_HARDWARE_DIR/reports"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g \
 -I"$MORI_HARDWARE_DIR/firmware/components/mori_core/include" \
 "$MORI_HARDWARE_DIR/firmware/components/mori_core/mori_core.c" "$MORI_HARDWARE_DIR/tests/test_core.c" \
 -lm -o "$MORI_HARDWARE_DIR/reports/test_core"
"$MORI_HARDWARE_DIR/reports/test_core"
