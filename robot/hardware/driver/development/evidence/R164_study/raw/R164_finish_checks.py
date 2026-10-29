"""Complete checkpoint checks without adopting either R164 layout."""
import json
import subprocess
import time
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
py = str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
records = []

def run(step, argv):
    start = time.monotonic()
    result = subprocess.run(argv, text=True, capture_output=True)
    records.append(dict(step=step, argv=argv, returncode=result.returncode,
                        stdout=result.stdout, stderr=result.stderr,
                        elapsed_seconds=time.monotonic()-start))
    (b/'R164-checkpoint-commands.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps(dict(step=step, returncode=result.returncode,
                         elapsed_seconds=records[-1]['elapsed_seconds'])), flush=True)
    assert result.returncode == 0, step

assert (b/'R164A-verification/result.json').exists()
assert not (b/'R164G-verification').exists()
run('G full native verification', [py, str(dev/'scripts/verify_trial.py'),
    str(dev/'native'), str(b/'R164G'), str(b/'R164G-verification')])
for rev in ['R164A', 'R164G']:
    assert not (b/(rev+'-planned-delta.json')).exists()
    run(rev+' planned delta', [py, str(dev/'scripts/review_planned_delta.py'),
        str(dev/'native/MORI_Interface_C3.kicad_pcb'),
        str(b/rev/'MORI_Interface_C3.kicad_pcb'), str(b/(rev+'-plan.json')),
        str(b/(rev+'-verification')/'regression.json'),
        str(dev/'evidence/R159H/regression.json'), str(b/(rev+'-planned-delta.json'))])
    assert not (b/(rev+'-inspection.json')).exists()
    run(rev+' source-ground and body screen', [py, str(b/'R162_inspection.py'), rev])

out = b/'R164-local-views'
out.mkdir(exist_ok=False)
views = [('R164A', 'B.Cu', [63, 15, 70, 28], '/HEAD_UV_ENABLE'),
         ('R164A', 'In3.Cu', [63, 15, 70, 28], '/HEAD_UV_ENABLE'),
         ('R164G', 'F.Cu', [39, 26, 46, 33], 'GND'),
         ('R164G', 'In3.Cu', [62, 27, 68, 33], 'Net-(R1301-~-Pad1)')]
for rev, layer, bounds, net in views:
    name = rev+'-'+layer.replace('.', '_')
    run(name+' render', [py, str(b/'R152_render_highlight.py'),
        str(b/rev/'MORI_Interface_C3.kicad_pcb'), layer,
        *map(str, bounds), str(out/(name+'.svg')), '--highlight', net])
    run(name+' raster', ['/Users/dean/.local/share/kicad-mcp/venv/bin/python', '-c',
        'import cairosvg,sys;cairosvg.svg2png(url=sys.argv[1],write_to=sys.argv[2])',
        str(out/(name+'.svg')), str(out/(name+'.png'))])
