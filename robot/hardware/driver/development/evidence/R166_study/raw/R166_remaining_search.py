"""Read-only current-board route screening of every remaining pad network.

Keep native layer rules, mounted-face bodies, drill gaps and continuous reference
checks. Proposals are not acceptance; no PCB or source file is modified.
"""
import ast,json,sys,math
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R166-remaining-route-proposals.json';assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','B.Cu','In2.Cu','In3.Cu'],.2);c=p.c;assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['F.Cu','B.Cu']}
rows=[];nets=sorted(net for net,gs in c.pad_groups().items() if len(gs)>1 and not net.startswith('unconnected-'))
for ni,net in enumerate(nets):
 print(json.dumps({'phase':'geometry','net':net,'index':ni+1,'net_count':len(nets)}),flush=True);gs=p.routing_groups(net);free,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly not in bodies:continue
  lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.102).difference(lands.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 for i,a in enumerate(gs):
  for z in gs[i+1:]:
   r=p.solve(a,z,(free,vf,blocked,allowed),250000);row={'net':net,'endpoint_groups':[a['pads'],z['pads']],'result':r};rows.append(row);out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'grid_mm':.05,'rows':rows,'adopted':False},indent=2)+'\n');print(json.dumps({'net':net,'status':r['status'],'length_mm':r.get('length_mm'),'vias':len(r.get('vias',[]))}),flush=True)
print(json.dumps({'complete':True,'nets':len(nets),'pairs':len(rows),'proposals':sum(r['result']['status']=='PROPOSAL' for r in rows)}),flush=True)
