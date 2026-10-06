"""Finite free-span screen with received CAM/LCD cable approach directions.

The two ends stop outside source package bounds. Their height is an explicitly
assumed AABB-center allocation; inserted tips, real slot heights and retention
are not qualified. Main geometry is never altered or saved by this script.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/static_flex';OUT=BASE/'full_route/screen'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from full_static_flex_geometry import solve,ribbon

ctx=Context();started=time.time()
ports=json.loads((BASE/'endpoints.json').read_text())['ports']
receipt=json.loads((BASE/'connector_faces/direction_receipt.json').read_text())
assert receipt['main_sha256']==ctx.source_hash
assert receipt['directions']['DISPLAY_FPC_18']['outward_zero_pose_XYZ']==[-1,0,0]
def end(ref):
    row=next(r for r in ports if r['reference']==ref)
    bounds=np.asarray(row['bounds_mm']);c=bounds.mean(0);c[0]=bounds[0,0]-.6
    return c
a=end('DISPLAY_FPC_18');b=end('Connector_108')
rows=[]
for radius,width,seed in itertools.product([7.5,10.],[9.5,10.5],[5.,10.,15.]):
    fit=solve(a,b,radius=radius,middle_seed=seed)
    name=f'R{radius:g}_W{width:g}_M{seed:g}'
    if fit['status']!='PASS':
        rows.append(dict(id=name,status='BLOCKED',cause='Endpoint solver did not converge',
            residual=fit['residual'].tolist(),iterations=fit['iterations']));continue
    g=ribbon(fit,width=width);m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles']))
    assert m.status()==manifold.Error.NoError
    lo=g['vertices_mm'].min(0);hi=g['vertices_mm'].max(0)
    tested=[];fail=[];threshold=.3+g['metadata']['polygonal_chord_error_bound_mm']
    for name_t,target in ctx.targets.items():
        if np.any(lo>target['hi']+1) or np.any(hi<target['lo']-1):continue
        overlap=float((m^target['m']).volume());gap=float(m.min_gap(target['m'],1.))
        row=dict(target=name_t,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.)
        tested.append(row)
        if overlap>1e-7 or gap<threshold:fail.append(row)
    np.savez_compressed(OUT/(name+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    row=dict(id=name,status='FAIL' if fail else 'PASS',parameters=g['metadata'],
        checked_targets=len(tested),nearby_targets=tested,failures=fail,
        required_model_gap_mm=threshold,mesh_components=len(m.decompose()),volume_mm3=float(m.volume()))
    rows.append(row)
    print('FULL_FFC_SCREEN',name,row['status'],fail,flush=True)
ctx.assert_unchanged()
record=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='194 mm free-span candidate with correct outward/inward tangents and endpoint width frames; not actual mating or fixed-cable qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [
        BASE/'endpoints.json',BASE/'connector_faces/direction_receipt.json',HERE/'full_static_flex_geometry.py']},
    rows=rows,ends_mm=[a.tolist(),b.tolist()],
    endpoint_datum_basis='Outer source-package X bound minus0.6mm; YZ at AABB center. Slot center/height are unknown; these are ASSUMED allocations.',
    nominal_stock_length_mm=200,free_span_mm=194,reserved_connection_zones_mm=6,
    connection_zone_basis='Budget only, not actual insertion length or proof that two tips can be made.',
    native_servo_bounds={n:[ctx.ss[n].lo.tolist(),ctx.ss[n].hi.tolist()] for n in ['Yaw_Servo','Pitch_Servo']},
    main_changed=False,adopted=False,physical_validation='NOT_TESTED',full_cable_fit='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('FULL_FFC_SCREEN_DONE',record['status'],flush=True)
