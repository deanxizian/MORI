#!/bin/bash
set -eu
cd "$(dirname "$0")/../firmware_work/firmware"
source /Users/dean/esp/esp-idf/export.sh
idf.py --version
python --version
cmake --version
ninja --version
xtensa-esp32s3-elf-gcc --version
test "$(git -C /Users/dean/esp/esp-idf describe --tags --dirty)" = "v5.5.2"
idf.py build
