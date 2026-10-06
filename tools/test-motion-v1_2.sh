#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/v1_2/tests
src=firmware/motion/v1_2
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -I"$src/include" "$src/s288.c" "$src/bus.c" "$src/sensors.c" "$src/motion.c" "$src/timing.c" "$src/test_motion.c" -lm -o reports/v1_2/tests/motion_host
reports/v1_2/tests/motion_host
