#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/v1_2/tests
src=firmware/motion/v1_2
vendor=refs/v1_2/digital_servo/stm32/firmware/App
cc -std=c11 -Wall -Wextra -Wno-invalid-source-encoding -include stdlib.h -fsanitize=address,undefined -g -I"$src/include" -I"$src/tests/vendor_stubs" -I"$vendor" "$src/s288.c" "$src/tests/test_unitree_reference.c" "$vendor/protocol.c" -lm -o reports/v1_2/tests/unitree_reference
reports/v1_2/tests/unitree_reference
