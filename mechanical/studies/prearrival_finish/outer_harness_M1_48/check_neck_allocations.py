"""Add the received plug and fourteen candidate-wire envelopes to neck checks."""
from pathlib import Path
import sys,json,math
from collections import Counter
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from native_context import *
ctx=Context();prior_path=HERE.parent/'neck_threading_M1_48/outer_corridor_screen.json'
prior=json.loads(prior_path.read_text());cache_path=HERE.parent/'neck_threading_M1_48/outer_corridor_curves.npz';cache=np.load(cache_path)
rows=[];counts=Counter()
for row in prior['passing']:
    points=cache[row['curve_key']];hit=ctx.clear(points,8*(1-math.cos(math.pi/400)))
    rows.append({**row,'status':'BLOCKED' if hit else 'PASS','failure':hit})
    if hit:counts[hit['object']]+=1
result=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Previously tested local corridors with all received mating allocations and fourteen candidate wires added',
    **ctx.evidence(),script_sha256=sha(__file__),source_prior_sha256=sha(prior_path),source_curves_sha256=sha(cache_path),
    rows=rows,blockers=dict(counts),main_applied=False,whole_harness='BLOCKED',
    head_pose_scope='These variants need their own combined-motion checks; a different variant cannot inherit the selected four-curve PASS.')
ctx.assert_unchanged();(HERE/'neck_allocations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('NECK_ALLOCATION_SCREEN',result['status'],'passing',sum(r['status']=='PASS' for r in rows),'blockers',dict(counts),flush=True)
for row in rows:
    if row['outer_radius_mm']==37.6 and row['lower_z_mm']==137 and row['upper_bend_start_z_mm']==160:
        print('PRIOR_SELECTED',row,flush=True)
