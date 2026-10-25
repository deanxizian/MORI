#!/bin/bash
set -eu
cd "$(dirname "$0")/../.."
stamp=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
case "$stamp" in *[!a-zA-Z0-9_-]*|"") exit 2;; esac
bash software/scripts/build_simulator.sh
python3 software/tools/mori_cli.py simulate --output "software/reports/SIMULATED_${stamp}_estop.csv" --frames 1000 --scenario estop
python3 software/tools/mori_cli.py replay "software/reports/SIMULATED_${stamp}_estop.csv"
python3 software/tools/mori_cli.py simulate --output "software/reports/SIMULATED_${stamp}_reset.csv" --frames 400 --scenario reset
python3 software/tools/mori_cli.py replay "software/reports/SIMULATED_${stamp}_reset.csv"
python3 software/tools/check_control_signs.py --output "software/reports/SIMULATED_${stamp}_direction.json"
software/reports/bin/SIMULATED_face 240 "software/reports/SIMULATED_${stamp}_face_240.ppm"
software/reports/bin/SIMULATED_face 360 "software/reports/SIMULATED_${stamp}_face_360.ppm"
python3 - "$stamp" <<'PY'
import hashlib,json,pathlib,sys
for size in (240,360):
 p=pathlib.Path(f'software/reports/SIMULATED_{sys.argv[1]}_face_{size}.ppm')
 p.with_suffix('.meta.json').write_text(json.dumps({'source':'SIMULATED','physical_validation':'NOT_TESTED','width':size,'height':size,'format':'PPM RGB renderer output','sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2)+'\n')
PY
