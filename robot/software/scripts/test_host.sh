#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/bin
CORE=firmware_work/firmware/components/mori_core
cc --version
FLAGS=(-std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -I"$CORE/include")
cc "${FLAGS[@]}" "$CORE/mori_core.c" firmware_work/tests/test_core.c -lm -o reports/bin/core_tests
reports/bin/core_tests
cc "${FLAGS[@]}" "$CORE/mori_core.c" tests/test_baseline_regressions.c -lm -o reports/bin/regressions
reports/bin/regressions
cc "${FLAGS[@]}" "$CORE"/*.c tests/sim_hal.c tests/test_engine.c -lm -o reports/bin/engine_tests
reports/bin/engine_tests

cc "${FLAGS[@]}" -Itests/idf_stubs -Ifirmware_work/firmware/main firmware_work/firmware/main/motor.c "$CORE/mori_ui.c" tests/test_motor_adapter.c -lm -o reports/bin/SIMULATED_motor_adapter
reports/bin/SIMULATED_motor_adapter

cc "${FLAGS[@]}" -DMORI_TEST_LOCKED -Itests/idf_stubs -Ifirmware_work/firmware/main firmware_work/firmware/main/motor.c "$CORE/mori_ui.c" tests/test_motor_adapter.c -lm -o reports/bin/SIMULATED_motor_locked
reports/bin/SIMULATED_motor_locked
