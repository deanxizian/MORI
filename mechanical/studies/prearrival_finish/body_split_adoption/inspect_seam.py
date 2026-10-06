"""Read-only seam-space inspection on the saved M1.50 model."""
from pathlib import Path
import sys, json
OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[3]
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
from harness_context import Context, np
from common import P, D
ctx = Context()
rows = {}
for n, s in ctx.ss.items():
    if n in ['Body_Upper', 'Body_Lower', 'Motor_Retainer', 'Drive_Bridge', 'Load_Frame', 'Battery_Tray']:
        rows[n] = dict(lo=s.lo.tolist(), hi=s.hi.tolist())
seam = []
skin = ctx.ss['Body_Lower'].m + ctx.ss['Body_Upper'].m
for x in [-48,-36,-24,-12,0,12,24,36,48]:
    hits = skin.ray_cast([x,0,0],[x,0,100])
    seam.append(dict(x=x,hits=[dict(position=list(h.position),normal=list(h.normal)) for h in hits]))
result = dict(source=ctx.sources,body_parameters={k:P[k] for k in ['shell_thickness_mm','body_diameter_mm','body_side_cut_x_mm','seam_gap_mm']},
              D=D,parts=rows,seam=seam,native_fingerprints=ctx.print_fingerprints)
(OUT/'seam_space.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['source','native_fingerprints']},indent=2),flush=True)
ctx.assert_unchanged()
