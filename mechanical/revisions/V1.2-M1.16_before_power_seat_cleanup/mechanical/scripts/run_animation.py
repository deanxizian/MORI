"""Regenerate, encode and read back the editable assembly animation.

Run with the project Python (Pillow is used by the final gallery publisher).
"""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
blender = os.environ.get('MORI_BLENDER') or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
master = ROOT / 'mori_v1_2.blend'
target = ROOT / 'mori_assembly_animation.blend'
if json.loads((ROOT/'reports/validation.json').read_text())['counts']['FAIL']:
    raise SystemExit('Resolve current geometry failures before publishing an updated animation.')
steps = [
    ('build', [blender, '--background', '--python-exit-code', '1', str(master), '--python', str(ROOT/'scripts/assembly_animation.py'), '--', '--width', '1280', '--render', 'stills']),
    ('render', [blender, '--background', '--python-exit-code', '1', str(target), '-S', 'MORI_Assembly_Animation', '-a']),
    ('validate', [blender, '--background', '--python-exit-code', '1', str(target), '--python', str(ROOT/'scripts/check_assembly_animation.py')]),
    ('publish', [sys.executable, str(ROOT/'scripts/report.py')]),
]
records = []
(ROOT/'animation').mkdir(exist_ok=True)
for stage, command in steps:
    log = ROOT/'reports'/f'assembly_animation_{stage}.log'
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print('ANIMATION', stage, flush=True)
    with log.open('w') as out:
        result = subprocess.run(command, cwd=ROOT.parent, stdout=out, stderr=subprocess.STDOUT)
    records.append({'stage': stage, 'command': command, 'started_utc': started,
                    'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    'returncode': result.returncode, 'log': str(log.relative_to(ROOT))})
    (ROOT/'animation/commands.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    if result.returncode:
        raise SystemExit(result.returncode)
print('ANIMATION_COMPLETE', flush=True)
