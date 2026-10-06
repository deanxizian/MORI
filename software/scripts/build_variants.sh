#!/bin/bash
set -eu
cd "$(dirname "$0")/../firmware_work/firmware"
source /Users/dean/esp/esp-idf/export.sh
python - <<'PY'
from pathlib import Path
base=Path('sdkconfig').read_text()
out=Path('../../reports/compile_only');out.mkdir(exist_ok=True)
for mode in ('no_screen','gated_code_coverage'):
 text=base
 changes={'MORI_LCD_ENABLE':mode!='no_screen'}
 if mode=='gated_code_coverage':
  changes.update({key:True for key in ('MORI_POWER_STAGE_VERIFIED','MORI_ENABLE_BALANCE','MORI_HEAD_VERIFIED','MORI_AXES_VERIFIED')})
 for key,value in changes.items():
  prefix='CONFIG_'+key
  text='\n'.join(line for line in text.splitlines() if not line.startswith(prefix+'=') and line!='# '+prefix+' is not set')+'\n'
  text+=prefix+'=y\n' if value else '# '+prefix+' is not set\n'
 (out/(mode+'.sdkconfig')).write_text(text)
PY
# These compile-coverage artifacts are NEVER commissioning firmware.
idf.py -B ../../reports/compile_only/no_screen -DSDKCONFIG="$(pwd)/../../reports/compile_only/no_screen.sdkconfig" build
idf.py -B ../../reports/compile_only/DO_NOT_FLASH_gated_coverage -DSDKCONFIG="$(pwd)/../../reports/compile_only/gated_code_coverage.sdkconfig" build
