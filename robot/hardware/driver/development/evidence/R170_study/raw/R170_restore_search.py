"""Target changed-layout links while preferring preservation of foreign power fill.
Full-fill avoidance is attempted first. The weighted fallback is only a routing
proposal and never replaces native refill, all 50 width checks or references.
Every result is independent; proposals are not jointly compatible by inference.
"""
import ast,inspect,json,sys,textwrap,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
import plan_layered_route as module
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];suffix=sys.argv[2] if len(sys.argv)>2 else '';out=b/(rev+'-power-aware-search'+suffix);out.mkdir(exist_ok=False)
src=inspect.getsource(Planner.solve)
old='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) + (.35 if old is not None and old != d else 0)'
new='nc = cost + self.grid * (math.sqrt(2) if dx and dy else 1) * (1 + self.fill_weight * max(int(self.fill_penalty[l,y,x]), int(self.fill_penalty[l,ny,nx]))) + (.35 if old is not None and old != d else 0)'
assert src.count(old)==1;src=src.replace(old,new)
old='cost + 4., None';assert src.count(old)==1
src=src.replace(old,'cost + 4. + self.fill_weight * int(self.via_penalty[y,x]), None')
ns=dict(vars(module));exec(compile(textwrap.dedent(src),'power_aware_solve','exec'),ns)
class PowerPlanner(Planner):solve=ns['solve']
p=PowerPlanner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
requests=[('restore_S2_mcu','Net-(U1001-S2_{slash}_WHEEL_sense)','U1001.5','R1002.2'),('restore_S2_filter','Net-(U1001-S2_{slash}_WHEEL_sense)','C1002.1','R1002.2'),('restore_bat_tap','Net-(D1001-K)','D1001.1','R1001.2'),('restore_wheel_tx','/01 {slash} Core/WHEEL_TX','J102.18','U402.2'),('fault_ina','/FAULT_N','U1701.5','Q1701.3')]
rows=[]
for name,net,a,z in requests:
 print(json.dumps({'request':name,'phase':'geometry'}),flush=True)
 groups=p.routing_groups(net);ga=next(g for g in groups if a in g['pads']);gz=next(g for g in groups if z in g['pads'])
 free,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly not in ['F.Cu','B.Cu']:continue
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
 reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in LAYERS}
 guards=[reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102) for ly in p.layers]
 via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
 p.fill_penalty=np.array([mask(g,p.xx,p.yy) for g in guards]);p.via_penalty=mask(via_guard,p.xx,p.yy)
 for mode in ['preserve_foreign_fill','weighted_50']:
  obs=[x.union(y) for x,y in zip(blocked,guards)] if mode=='preserve_foreign_fill' else blocked
  fs=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(obs,allowed)])
  vs=vf & ~p.via_penalty if mode=='preserve_foreign_fill' else vf
  p.fill_weight=0 if mode=='preserve_foreign_fill' else 50
  start=time.monotonic();r=p.solve(ga,gz,(fs,vs,obs,allowed),1500000)
  hits=[]
  if r['status']=='PROPOSAL':
   for pn,ly,g in c.fills:
    if pn in ['GND',net]:continue
    clear=p.internal_clearance if ly.startswith('In') else .2
    stroke=unary_union([LineString(q['points_mm']).buffer(.1+clear) for q in r['routes'] if q['layer']==ly]+[Point(q['position_mm']).buffer(.25+clear) for q in r['vias']])
    cut=stroke.intersection(g)
    if cut.area>1e-8:hits.append({'net':pn,'layer':ly,'area_mm2':cut.area,'bounds_mm':list(cut.bounds)})
  row={'request':name,'net':net,'mode':mode,'result':r,'potential_power_cuts':hits,'elapsed_seconds':time.monotonic()-start};rows.append(row)
  (out/'searches.json').write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'grid_mm':p.grid,'results':rows,'adopted':False},indent=2)+'\n')
  print(json.dumps({'request':name,'mode':mode,'status':r['status'],'length_mm':r.get('length_mm'),'expanded':r.get('expanded'),'power_cut_regions':len(hits),'elapsed_seconds':row['elapsed_seconds']}),flush=True)
  if r['status']=='PROPOSAL':
   (out/(name+'-plan.json')).write_text(json.dumps({'revision':rev+'-'+name,'board_sha256':c.sha,'routes':[{**x,'net':net} for x in r['routes']],'vias':[{**x,'net':net} for x in r['vias']],'activate_pth_layers':r['activate_pth_layers'],'scope':__doc__,'adoption_prohibited':True},indent=2)+'\n');break
