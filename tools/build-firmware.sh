#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
if [ "${1:-all}" = motion ]; then exec bash tools/build-motion-v1_2.sh; fi
if [ "${1:-all}" = all ]; then bash tools/build-motion-v1_2.sh; fi
: "${IDF_PATH:=/Users/dean/esp/esp-idf}"
source "$IDF_PATH/export.sh"
case "${1:-all}" in
 legacy-motion) idf.py -C firmware/motion -B firmware/motion/build_v1 -D MORI_LEGACY_ESP32=ON build ;;
 interaction|all) idf.py -C firmware/interaction -B firmware/interaction/build_v1_2 -D SDKCONFIG=sdkconfig.v1_2 build ;;
 *) echo 'motion (STM32) | legacy-motion (ESP32 A0/V1) | interaction | all';exit 2;;
esac
