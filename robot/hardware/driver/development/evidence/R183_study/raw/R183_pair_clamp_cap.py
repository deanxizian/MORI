"""Pair exact native D1602/C1602 placement candidates, keeping D301 in place.

Independent clearance/adjacency candidates are not a simultaneous layout.
This adds mutual geometry and the retained D301/CLR spine before any native
trial. Electrical restoration and via placement are still mandatory.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R183-clamp-cap-pairs.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    n=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[n],type_ignores=[]),name,'exec'))
fixed=next(f for f in c.footprints if f.GetReference()=='D301')
fixed_yard=outline(fixed,pcb.B_CrtYd)
fixed_pads=[(p.GetNetname(),shape(p,c.ids['B.Cu'])) for p in fixed.Pads()]
clr=c.shapes['a64ead90-f8fb-47e5-9d8d-700e6f43096f','B.Cu']
sets={}
for ref in ['D1602','C1602']:
    d=json.loads((b/('R183-clamp-cap-'+ref+'-pose-screen.json')).read_text());assert d['source_sha256']==c.sha
    original=next(f for f in c.footprints if f.GetReference()==ref);rows=[]
    for r in d['candidates']:
        f=pcb.FOOTPRINT(original);f.SetOrientationDegrees(r['rotation_deg'])
        p0=xy(f.GetPosition());f.Move(pcb.VECTOR2I(round((r['position_mm'][0]-p0[0])*1e6),round((r['position_mm'][1]-p0[1])*1e6)))
        yard=outline(f,pcb.B_CrtYd);body=fab(f)
        pads=[(p.GetNetname(),shape(p,c.ids['B.Cu'])) for p in f.Pads()]
        if yard.intersection(fixed_yard).area>1e-8 or any(s.distance(g)<.1999996-1e-9 for n,s in pads for m,g in fixed_pads if n!=m):continue
        if body.intersects(clr) or any(s.distance(clr)<.1999996-1e-9 for n,s in pads):continue
        rows.append((r,yard,body,pads))
    sets[ref]=rows
rows=[]
for a,ya,ba,pa in sets['D1602']:
    for z,yz,bz,pz in sets['C1602']:
        if ya.intersection(yz).area>1e-8 or ba.intersection(bz).area>1e-8:continue
        if any(s.distance(g)<.1999996-1e-9 for n,s in pa for m,g in pz if n!=m):continue
        rows.append(dict(D1602=a,C1602=z,score=max(a['adjacency_distances_mm'].values())+max(z['adjacency_distances_mm'].values())))
rows.sort(key=lambda r:(r['score'],r['D1602']['displacement_mm']+r['C1602']['displacement_mm']))
novel=[r for r in rows if r['D1602']['displacement_mm']>.5]
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,D301_unchanged=True,
    filtered_independent_candidates={k:len(v) for k,v in sets.items()},pairs=rows,
    novel_clamp_pair_count=len(novel),adopted=False),indent=2)+'\n')
print(json.dumps(dict(pairs=len(rows),novel=len(novel),best_novel=novel[:5])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
