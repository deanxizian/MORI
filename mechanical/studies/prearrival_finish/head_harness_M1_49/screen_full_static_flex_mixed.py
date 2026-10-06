"""Test six bounded rear-return candidates against unchanged main solids."""
import sys, json, time, itertools
from pathlib import Path
ROOT=Path('/Users/dean/Documents/MORI'); HERE=Path(__file__).resolve().parent
BASE=HERE/'remaining_routes/static_flex'; OUT=BASE/'full_route/mixed_screen'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts')); sys.path.insert(0,str(HERE))
from harness_context import Context, np, sha
from common import manifold
from full_static_flex_mixed_geometry import solve, ribbon
ctx=Context(); started=time.time()
source=BASE/'full_route/screen/review.json'
record=json.loads(source.read_text())
assert record['sources']['mechanical/mori_v1_2.blend']==ctx.source_hash
a,b=np.array(record['ends_mm']); rows=[]
for vertical,width in itertools.product([.5,1.5,2.5],[9.5,10.5]):
    label=f'V{vertical:g}_W{width:g}'
    fit=solve(a,b,first_vertical=vertical)
    if fit['status']!='PASS':
        rows.append(dict(id=label,status='BLOCKED',cause='Endpoint solver did not converge',residual=fit['residual'].tolist())); continue
    g=ribbon(fit,width=width); m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles']))
    assert m.status()==manifold.Error.NoError
    lo=g['vertices_mm'].min(0); hi=g['vertices_mm'].max(0); tested=[]; fail=[]
    threshold=.3+g['metadata']['polygonal_chord_error_bound_mm']
    for name,target in ctx.targets.items():
        if np.any(lo>target['hi']+1) or np.any(hi<target['lo']-1): continue
        overlap=float((m^target['m']).volume()); gap=float(m.min_gap(target['m'],1.))
        row=dict(target=name,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.)
        tested.append(row)
        if overlap>1e-7 or gap<threshold: fail.append(row)
    np.savez_compressed(OUT/(label+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    row=dict(id=label,status='FAIL' if fail else 'PASS',parameters=g['metadata'],
        nearby_targets=tested,failures=fail,required_model_gap_mm=threshold,
        mesh_components=len(m.decompose()),volume_mm3=float(m.volume()))
    rows.append(row); print('FULL_FFC_MIXED',label,row['status'],fail,flush=True)
ctx.assert_unchanged()
report=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Mixed-radius free-span capacity; assumed endpoint centers and connector zones, no selected cable or adoption',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,HERE/'full_static_flex_mixed_geometry.py',HERE/'full_static_flex_geometry.py']},
    rows=rows,ends_mm=[a.tolist(),b.tolist()],main_changed=False,adopted=False,
    physical_validation='NOT_TESTED',full_cable_fit='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FULL_FFC_MIXED_SCREEN_DONE',report['status'],flush=True)
