"""Read-only complete OV-branch reroute on the existing R13-permitted In2 layer.

Expose only the existing through-via lands after checking their actual diameter,
foreign copper and native track keepouts. No new via, board save or rule change.
Any raster proposal still needs exact endpoint reconstruction and native checks.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner

b=Path('robot/.state/c3-completion/trials'); out=b/'R150-OV-In2-search'; out.mkdir(exist_ok=False)
p=Planner(b/'R150B/MORI_Interface_C3.kicad_pcb',.05,['In2.Cu'],.2); c=p.c
net='Net-(U1301-INB-_{slash}_OV)'; assert net in p.in2_nets
gs=p.routing_groups(net)
source=next(g for g in gs if 'R1306.1' in g['pads'])
target=next(g for g in gs if 'R1307.2' in g['pads'])
exposed=[]
for g in [source,target]:
    for v in c.vias:
        if v.GetNetname()!=net: continue
        # The actual B or F via land must belong to this electrical group.
        if not any((uid(v),ly) in c.shapes and c.shapes[uid(v),ly].intersects(s) for ly,s in g['layers'].items()): continue
        lid=c.ids['In2.Cu']; land=shape(v,lid)
        foreign=unary_union([s for (u,ly),s in c.shapes.items() if ly=='In2.Cu' and c.by_id[u].GetNetname()!=net])
        if land.buffer(.205).intersects(foreign): continue
        if any(k['tracks'] and 'In2.Cu' in k['layers'] and land.intersects(k['shape']) for k in c.keepouts): continue
        g['layers']['In2.Cu']=g['layers'].get('In2.Cu',GeometryCollection()).union(land)
        exposed.append(dict(uuid=uid(v),position_mm=xy(v.GetPosition()),source_flashed=v.FlashLayer(lid)))
print(json.dumps(dict(phase='search',groups=[source['pads'],target['pads']],exposed=exposed)),flush=True)
r=p.solve(source,target,p.geometry(net),500000)
result=dict(scope=__doc__,source_sha256=c.sha,net=net,groups=[source['pads'],target['pads']],exposed_existing_vias=exposed,result=r)
(out/'search.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(r),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
