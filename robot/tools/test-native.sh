#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports/v1/tests
CORE=firmware/motion/components/mori_core
V1=firmware/motion/components/mori_v1
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -Icontracts -Icontracts/generated -I"$V1/include" -I"$CORE/include" contracts/wire.c "$CORE/mori_core.c" "$V1/mori_v1.c" "$V1/test_v1.c" -lm -o reports/v1/tests/motion_v1_host
reports/v1/tests/motion_v1_host
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g firmware/interaction/core/audio.c firmware/interaction/core/test_audio.c -o reports/v1/tests/audio_host
reports/v1/tests/audio_host
