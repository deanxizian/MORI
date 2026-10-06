"""Check two final straight approaches to the current camera capture."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex/camera_corridor'; OUT=BASE/'terminal'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts')); sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from camera_flex_terminal_geometry import terminal_route
ctx=Context(); started=time.time(); source=BASE/'review.json'; prior=json.loads(source.read_text()); params=prior['rows'][0]['parameters']; rows=[]
for tail in [1.,2.]:
    g=terminal_route(params['start_mm'],params['end_mm'],tail=tail)
    m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles'])); assert m.status()==manifold.Error.NoError
    lo=g['vertices_mm'].min(0); hi=g['vertices_mm'].max(0); nearby=[]; failures=[]; bound=.3+g['metadata']['chord_error_bound_mm']; label=f'T{tail:g}_W6.6'
    for name,target in ctx.targets.items():
        if np.any(lo>target['hi']+1) or np.any(hi<target['lo']-1): continue
        overlap=float((m^target['m']).volume()); gap=float(m.min_gap(target['m'],1.))
        item=dict(target=name,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.); nearby.append(item)
        if overlap>1e-7 or gap<bound: failures.append(item)
    np.savez_compressed(OUT/(label+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    rows.append(dict(id=label,status='FAIL' if failures else 'PASS',parameters=g['metadata'],nearby_targets=nearby,failures=failures,required_model_gap_mm=bound))
    print('CAMERA_TERMINAL',label,rows[-1]['status'],failures,flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,HERE/'camera_flex_terminal_geometry.py',HERE/'camera_flex_corridor_geometry.py']},
    rows=rows,main_changed=False,adopted=False,source_FPC_compatibility='BLOCKED',physical_validation='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAMERA_TERMINAL_DONE',r['status'],flush=True)
