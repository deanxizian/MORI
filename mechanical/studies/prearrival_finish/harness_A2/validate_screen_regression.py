"""Scene-derived regression cases for the corrected connected-curve screen."""
from pathlib import Path
import json,hashlib
STAGE=Path(__file__).resolve().parent
code=(STAGE/'check_static.py').read_text().split('specs=[')[0]
exec(compile(code,str(STAGE/'check_static.py'),'exec'),globals())
cases=[
    ('cavity_next_to_rear_seat','Body_Upper',[15.5,-46.5346,116.2994],[15.5,-46.4,116.3],False),
    ('entire_curve_inside_existing_deck','Load_Frame',[22.,-39.,112.9],[22.,-39.,113.1],True),
    ('curve_crosses_existing_deck','Load_Frame',[22.,-39.,110.],[22.,-39.,116.],True),
    ('within_allocated_surface_margin','Load_Frame',[22.,-39.,115.7],[22.,-39.,115.8],True)]
rows=[]
for label,name,a,b,expected in cases:
    s=obstacles[name];pts=resample([a,b],.02);clear=.508+.3+.011
    dist=[trees[name].find_nearest(Vector(p))[3] for p in pts]
    near=min(dist)<clear;inside=False;ratio=None
    if not near and np.all(pts>=s.lo) and np.all(pts<=s.hi):
        probe=manifold.Manifold.sphere(.01,16).translate(pts[0].tolist())
        ratio=max(0,(probe^s.m).volume())/probe.volume();inside=ratio>.5
    row=dict(id=label,object=name,expected_reject=expected,rejected=near or inside,
        nearest_surface_mm=float(min(dist)),containment_fraction=ratio,
        status='PASS' if (near or inside)==expected else 'FAIL')
    rows.append(row);print('SCREEN_REGRESSION',row,flush=True)
out=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
    source_blend_sha256=source_hash,cases=rows,main_modified=False,
    method='Scene-derived empty cavity / solid interior / crossing / margin cases; no nearest-face normal sign used')
(STAGE/'screen_regression.json').write_text(json.dumps(out,indent=2)+'\n')
assert out['status']=='PASS'
