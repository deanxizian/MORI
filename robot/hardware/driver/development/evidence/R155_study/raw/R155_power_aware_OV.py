"""Independent OV proposal with a cost for cutting existing non-ground fill.

This is a routing preference, never acceptance or a design-rule exception.
Actual native refill and supply width/connectivity remain mandatory.
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
b=Path('robot/.state/c3-completion/trials')
revision,name,weight=sys.argv[1:4];weight=float(weight)
out=b/(name+'.json');assert not out.exists()
source=inspect.getsource(Planner.solve)
old='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) + (.35 if old is not None and old != d else 0)'
new='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) * (1 + self.fill_weight * max(int(self.fill_penalty[l,y,x]), int(self.fill_penalty[l,ny,nx]))) + (.35 if old is not None and old != d else 0)'
assert source.count(old)==1
ns=dict(vars(module));exec(compile(textwrap.dedent(source.replace(old,new)),'weighted_OV_solve','exec'),ns)
class PowerPlanner(Planner):solve=ns['solve']
p=PowerPlanner(b/revision/'MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
net='Net-(U1301-INB-_{slash}_OV)';gs=p.routing_groups(net);assert len(gs)==2
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly not in ['F.Cu','B.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in p.layers}
p.fill_penalty=np.array([mask(reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.105),p.xx,p.yy) for ly in p.layers]);p.fill_weight=weight
print(json.dumps({'source':revision,'weight':weight,'groups':[g['pads'] for g in gs]}),flush=True)
r=p.solve(gs[1],gs[0],(free,vf,blocked,allowed),1600000)
hits=[]
if r['status']=='PROPOSAL':
 for n,l,g in c.fills:
  if n in ['GND',net] or l not in p.layers:continue
  stroke=unary_union([LineString(x['points_mm']).buffer(.1+(p.internal_clearance if l.startswith('In') else .2)) for x in r['routes'] if x['layer']==l])
  cut=stroke.intersection(g)
  if cut.area>1e-8:hits.append({'net':n,'layer':l,'area_mm2':cut.area,'bounds_mm':cut.bounds})
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'weight':weight,'net':net,'result':r,'potential_power_cuts':hits,'adopted':False},indent=2)+'\n')
print(json.dumps({'result':r,'potential_power_cuts':hits}),flush=True)
