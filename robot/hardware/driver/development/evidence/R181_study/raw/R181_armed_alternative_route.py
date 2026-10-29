"""Independent signal-corridor trial within an explicitly bounded MOTION_3V3 plane window.

The source reservations are tied to R179I. Only the In3 MOTION_3V3 planning reservation inside (21.5,6.8)-(35.5,19.0) is opened for an explicit trial; actual native rules, physical copper obstacles and full 50 power-width acceptance remain unchanged. This script permits only candidates
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
out=b/(rev+'-R181-plane-alternative-'+name);out.mkdir(exist_ok=False)
source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=Planner(str(Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb') if rev=='R180-source' else b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2)
c=p.c
rdir=b/'R180-supply-reservations'
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
plane_window=box(21.5,6.8,35.5,19.0)
plane_exceptions=[]
for row in data['files']:
    payload=(rdir/row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['sha256']
    g=from_wkb(payload)
    if row['net']=='MOTION_3V3' and row['layer']=='In3.Cu':
        removed=g.intersection(plane_window)
        plane_exceptions.append(dict(net=row['net'],layer=row['layer'],bounds_mm=list(plane_window.bounds),removed_planning_area_mm2=removed.area,original_wkb_sha256=row['sha256'],native_copper_modified=False,original_power_acceptance_mandatory=True))
        g=g.difference(plane_window)
    if row['net']!=net:reserved[row['layer']].append(g)
reserved={ly:unary_union(v) for ly,v in reserved.items()}
(out/'plane-planning-exceptions.json').write_text(json.dumps(plane_exceptions,indent=2)+'\n')
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
        blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
    margin=(p.internal_clearance if ly.startswith('In') else .2)+.102
    blocked[i]=blocked[i].union(reserved[ly].buffer(margin))
via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
vf=vf & ~mask(via_guard,p.xx,p.yy)
# The first shortest proposal partitioned 3V3 by ending at this In3 transfer.
# Exclude that approach in planning only; preserve its real copper and all rules.
exclusion=Point(32.86,15.85).buffer(.85)
blocked[p.layers.index('In3.Cu')]=blocked[p.layers.index('In3.Cu')].union(exclusion)
(out/'approach-exclusion.json').write_text(json.dumps(dict(layer='In3.Cu',center_mm=[32.86,15.85],radius_mm=.85,reason='Avoid the previously demonstrated 3V3-plane cut ending at this transfer; planning only, not a native keepout or test relaxation.'),indent=2)+'\n')
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
start=time.monotonic();result=p.solve(a,z,(free,vf,blocked,allowed),2000000)
row=dict(scope=__doc__,source_sha256=c.sha,reservation_source_sha256=source.sha,
         reservation_result_sha256=hashlib.sha256((rdir/'result.json').read_bytes()).hexdigest(),
         plane_planning_exceptions=plane_exceptions,grid_mm=p.grid,net=net,endpoint_groups=[a['pads'],z['pads']],result=result,
         elapsed_seconds=time.monotonic()-start,adopted=False)
(out/'result.json').write_text(json.dumps(row,indent=2)+'\n')
if result['status']=='PROPOSAL':
    plan=dict(revision=rev+'-'+name,board_sha256=c.sha,scope=__doc__,
              routes=[dict(q,net=net) for q in result['routes']],
              vias=[dict(q,net=net) for q in result['vias']],
              activate_pth_layers=result['activate_pth_layers'],plane_planning_exceptions=plane_exceptions)
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']},indent=2),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
