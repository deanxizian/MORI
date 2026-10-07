#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/bin
CORE=firmware_work/firmware/components/mori_core
cc -std=c11 -Wall -Wextra -Werror -O2 -I"$CORE/include" -Itests "$CORE"/*.c tests/sim_hal.c tools/SIMULATED_device.c -lm -o reports/bin/SIMULATED_device
cc -std=c11 -Wall -Wextra -Werror -O2 -I"$CORE/include" "$CORE/mori_ui.c" tools/SIMULATED_face.c -lm -o reports/bin/SIMULATED_face
