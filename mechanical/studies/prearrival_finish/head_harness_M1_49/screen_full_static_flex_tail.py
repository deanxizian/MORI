"""Screen longer LCD-side straight runs; no body/board movement or new holes."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex';OUT=BASE/'full_route/tail_screen'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from full_static_flex_tail_geometry import solve_tail,ribbon

ctx=Context();started=time.time()
initial=BASE/'full_route/screen/review.json';source=json.loads(initial.read_text())
assert source['sources']['mechanical/mori_v1_2.blend']==ctx.source_hash
a,b=np.array(source['ends_mm']);rows=[]
for tail,width,seed in itertools.product([10.5,12.5,14.],[9.5,10.5],[15.,20.,25.]):
    fit=solve_tail(a,b,tail=tail,middle_seed=seed)
    name=f'T{tail:g}_W{width:g}_M{seed:g}'
    if fit['status']!='PASS':
        rows.append(dict(id=name,status='BLOCKED',cause='Endpoint solver did not converge',residual=fit['residual'].tolist(),iterations=fit['iterations']));continue
    g=ribbon(fit,width=width);m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles']))
    assert m.status()==manifold.Error.NoError
    lo=g['vertices_mm'].min(0);hi=g['vertices_mm'].max(0);tested=[];fail=[]
    threshold=.3+g['metadata']['polygonal_chord_error_bound_mm']
    for n,t in ctx.targets.items():
        if np.any(lo>t['hi']+1) or np.any(hi<t['lo']-1):continue
        overlap=float((m^t['m']).volume());gap=float(m.min_gap(t['m'],1.))
        row=dict(target=n,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.)
        tested.append(row)
        if overlap>1e-7 or gap<threshold:fail.append(row)
    np.savez_compressed(OUT/(name+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    row=dict(id=name,status='FAIL' if fail else 'PASS',parameters=g['metadata'],
        checked_targets=len(tested),nearby_targets=tested,failures=fail,
        required_model_gap_mm=threshold,mesh_components=len(m.decompose()),volume_mm3=float(m.volume()))
    rows.append(row);print('FULL_FFC_TAIL_SCREEN',name,row['status'],fail,flush=True)
ctx.assert_unchanged()
record=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='194 mm free span with longer LCD-side orientation transition; uncertain connector zones excluded',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [initial,
        HERE/'full_static_flex_geometry.py',HERE/'full_static_flex_tail_geometry.py']},
    rows=rows,ends_mm=[a.tolist(),b.tolist()],endpoint_datum_basis=source['endpoint_datum_basis'],
    nominal_stock_length_mm=200,free_span_mm=194,reserved_connection_zones_mm=6,
    main_changed=False,adopted=False,physical_validation='NOT_TESTED',full_cable_fit='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('FULL_FFC_TAIL_SCREEN_DONE',record['status'],flush=True)
