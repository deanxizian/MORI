#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
default_arm="$PWD/.state/toolchains/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin"
if [ "$(uname -s)" = Linux ]; then default_arm="$PWD/.state/toolchains/arm-gnu-toolchain-14.2.rel1-x86_64-arm-none-eabi/bin"; fi
export PATH="${MORI_ARM_BIN:-$default_arm}:$PATH"
if ! command -v cmake >/dev/null; then
  source "${IDF_PATH:-/Users/dean/esp/esp-idf}/export.sh" >/dev/null
fi
arm-none-eabi-gcc --version
arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror -fsyntax-only -Ifirmware/motion/controller/include firmware/motion/controller/*.c
cmake --version
cmake -S firmware/motion -B firmware/motion/build_stm32 -G Ninja -DCMAKE_TOOLCHAIN_FILE="$PWD/firmware/motion/controller/arm-toolchain.cmake"
cmake --build firmware/motion/build_stm32
