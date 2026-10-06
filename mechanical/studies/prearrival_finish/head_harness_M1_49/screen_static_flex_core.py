"""Finite current-main packing screen for a planar LCD FFC central span."""
from pathlib import Path
import json,sys,time,itertools
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/static_flex/core_screen';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from static_flex_geometry import core

ctx=Context();started=time.time();rows=[]
for r,w,z in itertools.product([5.,7.5],[9.5,10.5],[236.,238.]):
    geom=core(radius=r,width=w,z=z)
    m=manifold.Manifold(manifold.Mesh64(geom['vertices_mm'],geom['triangles']))
    assert m.status()==manifold.Error.NoError
    lo=geom['vertices_mm'].min(0);hi=geom['vertices_mm'].max(0)
    tested=[];fail=[]
    threshold=.3+geom['metadata']['chord_error_bound_mm']
    for name,t in ctx.targets.items():
        if np.any(lo>t['hi']+1) or np.any(hi<t['lo']-1):continue
        v=float((m^t['m']).volume());gap=float(m.min_gap(t['m'],1.))
        row=dict(target=name,overlap_mm3=v,gap_mm=gap,gap_search_cap_mm=1.)
        tested.append(row)
        if v>1e-7 or gap<threshold:fail.append(row)
    name=f'R{r:g}_W{w:g}_Z{z:g}'
    np.savez_compressed(OUT/(name+'.npz'),**{k:v for k,v in geom.items() if k!='metadata'})
    record=dict(id=name,status='FAIL' if fail else 'PASS',parameters=geom['metadata'],
        checked_targets=len(tested),nearby_targets=tested,failures=fail,
        required_model_gap_mm=threshold,mesh_components=len(m.decompose()),volume_mm3=float(m.volume()))
    rows.append(record);print('STATIC_FLEX_CORE',name,record['status'],fail,flush=True)
ctx.assert_unchanged()
report=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='170 mm untwisted central-span storage; 30 mm reserved for two unmodeled ends, no endpoint/installation proof',
    rows=rows,sources=ctx.sources,inputs={str((HERE/'static_flex_geometry.py').relative_to(ROOT)):sha(HERE/'static_flex_geometry.py')},
    candidates_checked=len(rows),adopted=False,main_changed=False,full_flex_fit='BLOCKED',
    physical_validation='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('STATIC_FLEX_CORE_DONE',report['status'],flush=True)
