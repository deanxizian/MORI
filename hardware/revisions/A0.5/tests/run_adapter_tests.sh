#!/bin/sh
set -eu
MORI_REV_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$MORI_REV_DIR"
mkdir -p reports
for MORI_CASE in verified locked; do
  MORI_FLAGS=""
  if [ "$MORI_CASE" = locked ]; then MORI_FLAGS="-DMORI_TEST_LOCKED"; fi
  cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g \
    $MORI_FLAGS -Itests/idf_stubs -Ifirmware/main \
    -Ifirmware/components/mori_core/include \
    firmware/main/motor.c tests/test_motor_adapter.c -lm \
    -o "reports/test_adapter_$MORI_CASE"
  "reports/test_adapter_$MORI_CASE"
done
