"""Explicit RLIMIT return search, using pad/track/via groups without fills.
Two-stage searches can use existing ground vias as named terminals; each path
must be built and checked together. No new via is allowed in this screen.
"""
import ast,json,sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];o=b/(rev+'-ground-return-search.json');assert not o.exists();board=b/rev/'MORI_Interface_C3.kicad_pcb'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
trace=Copper(board);items=defaultdict(list)
for (u,ly),g in trace.shapes.items():items[trace.by_id[u].GetNetname(),ly].append(g)
trace.__dict__['copper']={k:unary_union(v) for k,v in items.items()};gs=groups(trace,'GND');a=next(g for g in gs if 'R1701.1' in g['pads']);z=next(g for g in gs if 'U1701.8' in g['pads']);assert a is not z;rows=[]
p=Planner(board,.05,['B.Cu','F.Cu','In3.Cu'],.2);c=p.c;free,vf,blocked,allowed=p.geometry('GND');vf[:]=False
for k,ly in enumerate(p.layers):
 if ly not in ['F.Cu','B.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);lands=unary_union([g for (u,l),g in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()=='GND']);blocked[k]=unary_union([blocked[k],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
requests=[('direct',a,z)]
for via in c.vias:
 if via.GetNetname()!='GND' or Point(xy(via.GetPosition())).distance(Point(42.75,9.05))>5:continue
 target=dict(pads=['via:'+uid(via)],layers={ly:Point(xy(via.GetPosition())).buffer(.035) for ly in p.layers if (uid(via),ly) in c.shapes})
 requests.extend([('to_'+uid(via),a,target),('from_'+uid(via),target,z)])
for name,start,end in requests:
 print(name,flush=True);r=p.solve(start,end,(free,vf,blocked,allowed),650000);rows.append(dict(name=name,result=r))
 o.write_text(json.dumps({'scope':__doc__,'board_sha256':c.sha,'source_pads':a['pads'],'target_pads':z['pads'],'rows':rows,'adopted':False},indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['routes','vias']}),flush=True)
