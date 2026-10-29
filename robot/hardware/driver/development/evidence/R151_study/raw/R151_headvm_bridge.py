"""Seek an actual 0.50 mm In2 bridge between the lost 0.48 mm HEAD_VM regions.

Use the filled, eroded connected regions as terminals. Other power pours, all
native holes/keepouts, and full ground reference remain protected. No new via,
board save, arbitrary thin-copper terminal, or rule change is permitted.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-HEADVM-bridge');out.mkdir(exist_ok=False)
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.025,['In2.Cu'],.5);c=p.c;net='/HEAD_VM';assert net in p.in2_nets
a=json.loads((b/(rev+'-audit.json')).read_text());r=next(x for x in a['power_width'] if x['net']==net and x['width_mm']==.48)
needed={u for pair in r['lost_pairs'] for u in pair};pairs=c.connected_pairs(net,.48);ids=[]
while needed:
    u=min(needed);group={u}|{v if k==u else k for k,v in pairs if k==u or v==u}
    ids.append(group);needed-=group
assert len(ids)==2,len(ids)
regions=[[],[]]
for region in parts(c.copper[net,'In2.Cu'].buffer(-.24,join_style=1)):
    hits=[]
    for i,group in enumerate(ids):
        if any((u,'In2.Cu') in c.shapes and region.intersects(c.shapes[u,'In2.Cu']) for u in group):hits.append(i)
    assert len(hits)<=1
    if hits:regions[hits[0]].append(region.buffer(-.011))
gs=[dict(pads=[],layers={'In2.Cu':unary_union(ss)}) for ss in regions]
free,vf,blocked,allowed=p.geometry(net)
foreign=unary_union([g for n,ly,g in c.fills if ly=='In2.Cu' and n not in ['GND',net]])
blocked=[blocked[0].union(foreign.buffer(p.internal_clearance+.255))]
free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
print(json.dumps(dict(phase='search',component_anchor_counts=[len(g) for g in ids],region_counts=[len(g) for g in regions])),flush=True)
result=p.solve(gs[0],gs[1],(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),500000)
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,net=net,component_anchor_ids=[sorted(g) for g in ids],result=result),indent=2)+'\n')
print(json.dumps(result),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
