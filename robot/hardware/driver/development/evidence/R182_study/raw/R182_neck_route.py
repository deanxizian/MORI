"""Independent displaced-terminal proposals against original full-power reservations.

The reserved geometry is recomputed from adopted R181C for R182. This script permits only candidates
with an explicit native trial plan. The source reservations retain the original
trunks but do not prove moved power terminals are restored. Native
refill, all connectivity/width/reference checks and visual review are required.
"""
import ast
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
from shapely import from_wkb
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask

b=Path('robot/.state/c3-completion/trials')
rev, name, net, first, last=sys.argv[1:6]
width=float(sys.argv[6]) if len(sys.argv)>6 else .2
out=b/(rev+'-R182-cam-protected-neck-'+name);out.mkdir(exist_ok=False)
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=Planner(str(Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb') if rev=='R182-source' else b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],width)
c=p.c
rdir=b/'R182-supply-reservations'
data=json.loads((rdir/'result.json').read_text())
assert data['source_sha256']==source.sha
assert len(data['roundtrip_checks'])==50 and all(r['status']=='PASS' for r in data['roundtrip_checks'])
nets={r['net'] for r in data['checks']}
for native in [source,c]:
    native.shapes
old={(u,ly):s for (u,ly),s in source.shapes.items() if source.by_id[u].GetNetname() in nets}
new={(u,ly):s for (u,ly),s in c.shapes.items() if c.by_id[u].GetNetname() in nets}
candidate_plan=json.loads((b/(rev+'-plan.json')).read_text())
assert candidate_plan['board_sha256']==source.sha
physical_delta=[dict(uuid=u,layer=ly,source_present=(u,ly) in old,candidate_present=(u,ly) in new) for u,ly in sorted(old.keys()|new.keys()) if (u,ly) not in old or (u,ly) not in new or not old[u,ly].equals_exact(new[u,ly],1e-8)]
(out/'power-physical-delta.json').write_text(json.dumps(dict(source_sha256=source.sha,board_sha256=c.sha,changes=physical_delta,scope='Explicit placement trial. Original zone reservations only; mandatory source connectivity/50-width acceptance not waived.'),indent=2)+'\n')
reserved={ly:[] for ly in LAYERS}
for row in data['files']:
    payload=(rdir/row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['sha256']
    geometry=from_wkb(payload)
    if row['net']=='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT' and row['layer']=='In3.Cu':
        window=box(16.5,15.3,25.5,18.6)
        removed=geometry.intersection(window)
        (out/'planning-exception.json').write_text(json.dumps(dict(net=row['net'],layer=row['layer'],window_mm=list(window.bounds),removed_planning_area_mm2=removed.area,original_wkb_sha256=row['sha256'],native_rules_unchanged=True,source_50_power_checks_mandatory=True),indent=2)+'\n')
        geometry=geometry.difference(window)
    if row['net']!=net:reserved[row['layer']].append(geometry)
reserved={ly:unary_union(v) for ly,v in reserved.items()}
# Also guard GND traces in a candidate; a new signal hole must not silently
# remove their reference. Old non-GND references are already in Planner.
ground_strokes=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if t.GetNetname()=='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
p.via_common=p.via_common.union(unary_union(ground_strokes).buffer(.657))
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
groups=p.routing_groups(net)
a=next(g for g in groups if first in g['pads']);z=next(g for g in groups if last in g['pads'])
assert a is not z,'Already connected'
free,vf,blocked,allowed=p.geometry(net)
blocked=list(blocked)
for i,ly in enumerate(p.layers):
    if ly in ['F.Cu','B.Cu']:
        bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
        lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
        blocked[i]=unary_union([blocked[i],bodies.buffer((p.width/2+.002)).difference(lands.buffer(-.001))])
    margin=(p.internal_clearance if ly.startswith('In') else .2)+(p.width/2+.002)
    blocked[i]=blocked[i].union(reserved[ly].buffer(margin))
via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
vf=vf & ~mask(via_guard,p.xx,p.yy)
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
# Planning-only exclusion for the native CAM supply neck severed in E.
neck=box(21.1,15.9,22.35,17.4)
index=p.layers.index('In3.Cu');blocked[index]=blocked[index].union(neck)
free[index]=~mask(blocked[index],p.xx,p.yy)&mask(allowed[index],p.xx,p.yy,True)
(out/'protected-neck.json').write_text(json.dumps(dict(bounds_mm=list(neck.bounds),reason='Exclude the demonstrated CAM_BAT_OUT severing approach; no native keepout, rule or acceptance change'),indent=2)+'\n')
start=time.monotonic();result=p.solve(a,z,(free,vf,blocked,allowed),2000000)
row=dict(scope=__doc__,source_sha256=c.sha,reservation_source_sha256=source.sha,
         reservation_result_sha256=hashlib.sha256((rdir/'result.json').read_bytes()).hexdigest(),
         grid_mm=p.grid,net=net,endpoint_groups=[a['pads'],z['pads']],result=result,
         elapsed_seconds=time.monotonic()-start,adopted=False)
(out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
if result['status']=='PROPOSAL':
    plan=dict(revision=rev+'-'+name,board_sha256=c.sha,scope=__doc__,
              routes=[dict(q,net=net) for q in result['routes']],
              vias=[dict(q,net=net) for q in result['vias']],
              activate_pth_layers=result['activate_pth_layers'])
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']},indent=2),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
