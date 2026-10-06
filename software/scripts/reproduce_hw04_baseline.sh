#!/bin/bash
# Reproduce the immutable upstream snapshot in reports; never overwrite work firmware.
set -eu
cd "$(dirname "$0")/.."
python3 - <<'PY'
import hashlib,json,pathlib,zipfile
root=pathlib.Path('reports/hw04_baseline_source');root.mkdir(exist_ok=True)
manifest=json.loads(pathlib.Path('reference_sources/HW-SW-0.4_baseline_manifest.json').read_text())
with zipfile.ZipFile('reference_sources/HW-SW-0.4_firmware_baseline.zip') as z:
    for name,sha in manifest['sha256'].items():
        data=z.read(name);assert hashlib.sha256(data).hexdigest()==sha,name
        path=root/name
        if path.exists():assert path.read_bytes()==data,name+' existing reference was modified'
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
print('PASS immutable HW-SW-0.4 archive members:',len(manifest['sha256']))
# CMake writes its derived configuration outside the pristine baseline sources.
pathlib.Path('reports/hw04_baseline.sdkconfig').write_bytes((root/'firmware/sdkconfig').read_bytes())
PY
cc --version
sh reports/hw04_baseline_source/tests/run_host_tests.sh
source /Users/dean/esp/esp-idf/export.sh
test "$(git -C /Users/dean/esp/esp-idf describe --tags --dirty)" = "v5.5.2"
idf.py --version
python --version
cmake --version
ninja --version
xtensa-esp32s3-elf-gcc --version
idf.py -C "$(pwd)/reports/hw04_baseline_source/firmware" -B "$(pwd)/reports/hw04_baseline_build" \
 -DSDKCONFIG="$(pwd)/reports/hw04_baseline.sdkconfig" build
