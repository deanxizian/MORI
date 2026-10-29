"""Read-only ADC proposals that account for foreign filled power copper.

All native obstacles, full mounted-face nominal bodies, old-reference proxy and
reference coverage remain. Foreign fill is a routing cost, not a clearance waiver:
native refill and actual power connectivity/width remain final acceptance gates.
The hard-reservation comparison is deliberately conservative, not a proof of
unroutability. This script never saves a PCB or changes a formal design rule.
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
base=Path('robot/.state/c3-completion/trials');revision=sys.argv[1]
out=base/(revision+'-power-aware-adc');out.mkdir(exist_ok=False)
source=inspect.getsource(Planner.solve)
old='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) + (.35 if old is not None and old != d else 0)'
new='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) * (1 + self.fill_weight * max(int(self.fill_penalty[l,y,x]), int(self.fill_penalty[l,ny,nx]))) + (.35 if old is not None and old != d else 0)'
assert source.count(old)==1
namespace=dict(vars(module));exec(compile(textwrap.dedent(source.replace(old,new)),'power_aware_solve','exec'),namespace)
class PowerPlanner(Planner):solve=namespace['solve']
p=PowerPlanner(str(base/revision/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
tree=ast.parse((base/'R138_joint_search.py').read_text());fab_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[fab_node],type_ignores=[]),'nominal_fab_helper','exec'),globals())
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['F.Cu','B.Cu']}
net='/01 {slash} Core/ACT_CURRENT_ADC';gs=p.routing_groups(net)
a=next(g for g in gs if 'R1003.2' in g['pads']);b=next(g for g in gs if 'J101.7' in g['pads']);assert a is not b
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly in bodies:
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.102).difference(own.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in p.layers}
guards=[reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+p.width/2+.005) for ly in p.layers]
p.fill_penalty=np.array([mask(g,p.xx,p.yy) for g in guards]);rows=[]
print(json.dumps({'source_sha256':c.sha,'groups':[a['pads'],b['pads']]}),flush=True)
for mode,weight in [('hard',0),('cost_10',10),('cost_50',50)]:
 p.fill_weight=weight
 if mode=='hard':
  blocked_=[unary_union([x,g]) for x,g in zip(blocked,guards)]
  free_=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked_,allowed)])
  via_=vf&~np.any(p.fill_penalty,axis=0)
 else:free_,via_,blocked_=free,vf,blocked
 r=p.solve(a,b,(free_,via_,blocked_,allowed),1000000)
 hits=[]
 if r['status']=='PROPOSAL':
  for n,l,g in c.fills:
   if n in ['GND',net] or l not in p.layers:continue
   route=unary_union([LineString(x['points_mm']).buffer(.1+(p.internal_clearance if l.startswith('In') else .2)) for x in r['routes'] if x['layer']==l])
   cut=route.intersection(g)
   if cut.area>1e-8:hits.append({'net':n,'layer':l,'affected_fill_mm2':cut.area,'bounds_mm':cut.bounds})
 row={'source_sha256':c.sha,'scope':__doc__,'mode':mode,'fill_cost_weight':weight,'result':r,'potential_power_fill_cuts':hits}
 rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({'mode':mode,**{k:v for k,v in r.items() if k not in ['routes','activate_pth_layers']},'power_cuts':hits}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
