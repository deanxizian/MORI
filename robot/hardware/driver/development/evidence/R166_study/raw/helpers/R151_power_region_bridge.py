"""Read-only wide-copper restoration using actual width-connected copper regions.

Pad and via anchors both participate. Terminals are interior to the actual
eroded region, not arbitrary thin copper or guessed anchor coordinates. Native
clearance, reference, mounted-face bodies and foreign power fills stay protected.
No vias or PCB mutations are introduced by this proposal search.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev,net,label=sys.argv[1:4];gate=float(sys.argv[4]);width=.5
out=b/(label+'-region-bridge');out.mkdir(exist_ok=False)
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.05,['In2.Cu','In3.Cu','F.Cu','B.Cu'],width);c=p.c
a=json.loads((b/(rev+'-audit.json')).read_text());r=next(x for x in a['power_width'] if x['net']==net and x['width_mm']==gate)
needed={u for pair in r['lost_pairs'] for u in pair};pairs=c.connected_pairs(net,gate);ids=[]
while needed:
    u=min(needed);group={u}|{v if k==u else k for k,v in pairs if k==u or v==u};ids.append(group);needed-=group
assert len(ids)>=2,len(ids)
gs=[dict(pads=[],layers={}) for _ in ids]
for ly in p.layers:
    regions=[[] for _ in ids]
    for region in parts(c.copper.get((net,ly),GeometryCollection()).buffer(-gate/2,join_style=1)):
        hits=[i for i,group in enumerate(ids) if any((u,ly) in c.shapes and region.intersects(c.shapes[u,ly]) for u in group)]
        assert len(hits)<=1
        if hits:regions[hits[0]].append(region.buffer(-(width-gate)/2-.001))
    for i,ss in enumerate(regions):gs[i]['layers'][ly]=unary_union(ss)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
for k,ly in enumerate(p.layers):
    foreign=unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]])
    blocked[k]=blocked[k].union(foreign.buffer((p.internal_clearance if ly.startswith('In') else .2)+width/2+.005))
    if ly in ['F.Cu','B.Cu']:
        bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
        own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
        blocked[k]=blocked[k].union(bodies.buffer(width/2+.002).difference(own.buffer(-.001)))
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
rows=[]
for i,g in enumerate(gs):
    for j,h in enumerate(gs[i+1:],i+1):
        print(json.dumps(dict(phase='search',components=[i,j],anchor_counts=[len(ids[i]),len(ids[j])])),flush=True)
        result=p.solve(g,h,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),500000)
        rows.append(dict(components=[i,j],result=result))
        (out/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,net=net,gate_width_mm=gate,proposed_width_mm=width,component_anchor_ids=[sorted(g) for g in ids],rows=rows),indent=2)+'\n')
        print(json.dumps(result),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
