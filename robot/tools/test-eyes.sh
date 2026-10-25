#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/v1_2/tests
cc -std=c11 -O2 -Wall -Wextra -Werror -Ifirmware/interaction/core firmware/interaction/core/eyes.c firmware/interaction/core/benchmark_eyes.c -lm -o reports/v1_2/tests/eyes_benchmark
reports/v1_2/tests/eyes_benchmark
