"""Read-only 3.3 V restoration with retained VM corridors and native constraints.

Foreign power fill is a path cost, while four explicit existing VM/Buck corridors
are reserved. This differs from the previous all-foreign-fill hard reservation.
Actual fill/width/reference regression is mandatory for every resulting candidate.
"""
import ast,inspect,json,sys,textwrap
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
import plan_layered_route as module
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev,label=sys.argv[1:3];net='MOTION_3V3';gate=.48;width=.5
out=b/(label+'.json');assert not out.exists()
source=inspect.getsource(Planner.solve)
old='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) + (.35 if old is not None and old != d else 0)'
new='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) * (1 + self.fill_weight * max(int(self.fill_penalty[l,y,x]), int(self.fill_penalty[l,ny,nx]))) + (.35 if old is not None and old != d else 0)'
assert source.count(old)==1;ns=dict(vars(module));exec(compile(textwrap.dedent(source.replace(old,new)),'joint_power_solve','exec'),ns)
class PowerPlanner(Planner):solve=ns['solve']
p=PowerPlanner(b/rev/'MORI_Interface_C3.kicad_pcb',.05,['In2.Cu','In3.Cu','F.Cu','B.Cu'],width);c=p.c
a=json.loads((b/(rev+'-audit.json')).read_text());r=next(x for x in a['power_width'] if x['net']==net and x['width_mm']==gate)
needed={u for pair in r['lost_pairs'] for u in pair};pairs=c.connected_pairs(net,gate);ids=[]
while needed:
 u=min(needed);group={u}|{v if k==u else k for k,v in pairs if k==u or v==u};ids.append(group);needed-=group
assert len(ids)>=2;gs=[dict(pads=[],layers={}) for _ in ids]
for ly in p.layers:
 regions=[[] for _ in ids]
 for region in parts(c.copper.get((net,ly),GeometryCollection()).buffer(-gate/2,join_style=1)):
  hits=[i for i,g in enumerate(ids) if any((u,ly) in c.shapes and region.intersects(c.shapes[u,ly]) for u in g)];assert len(hits)<=1
  if hits:regions[hits[0]].append(region.buffer(-(width-gate)/2-.001))
 for i,ss in enumerate(regions):gs[i]['layers'][ly]=unary_union(ss)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
for k,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[k]=blocked[k].union(bodies.buffer(width/2+.002).difference(own.buffer(-.001)))
spines=[]
for filename in ['R155-power-spines.json','R155-power-spines-fine.json']:
 spines += [r for r in json.loads((b/filename).read_text())['rows'] if r['status']=='RESERVED_PROPOSAL_CORRIDOR']
assert len(spines)==4
protected=unary_union([LineString(r['points_mm']).buffer(r['width_mm']/2+p.internal_clearance+width/2+.005) for r in spines])
blocked[0]=blocked[0].union(protected);vf=vf&~mask(protected,p.xx,p.yy)
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in p.layers}
p.fill_penalty=np.array([mask(reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+width/2+.005),p.xx,p.yy) for ly in p.layers]);p.fill_weight=50
main=max(range(len(ids)),key=lambda i:len(ids[i]));rows=[]
for i in range(len(ids)):
 if i==main:continue
 print(json.dumps({'phase':'search','components':[i,main],'anchor_counts':[len(ids[i]),len(ids[main])]}),flush=True)
 result=p.solve(gs[i],gs[main],(free,vf,blocked,allowed),1000000)
 rows.append({'components':[i,main],'result':result})
 out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'net':net,'gate_width_mm':gate,'proposed_width_mm':width,'component_anchor_ids':[sorted(g) for g in ids],'reserved_corridors':spines,'rows':rows,'adopted':False},indent=2)+'\n')
 print(json.dumps(result),flush=True)
