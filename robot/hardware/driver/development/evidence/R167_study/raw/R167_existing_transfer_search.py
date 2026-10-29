"""Recover original Q/U links using exact native pads and retained old vias.

Orphaned source transfers are explicit terminals, not omitted simply because
they no longer belong to a group containing a pad. No new via is allowed.
This search preserves every native/reference/mounted-face body constraint.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
out=b/(rev+'-existing-transfer-search.json');assert not out.exists()
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.025,['B.Cu','F.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
def terminal(name,ly):
 o=c.by_id[name] if name in c.by_id else next(q for q in c.pads if c.pad_name(q)==name)
 assert (uid(o),ly) in c.shapes, (name,ly)
 return o,dict(pads=[name],layers={ly:c.shapes[uid(o),ly]})
requests=[('act_output_old_transfer','F.Cu','U1702.1','74c0d925-81e9-4f8b-8224-202391f21e26'),('act_Q_old_transfer','B.Cu','Q1701.2','74c0d925-81e9-4f8b-8224-202391f21e26'),('act_Q_right_transfer','B.Cu','Q1701.2','4312a4e0-e664-44e0-a44a-716dd81b836a')]
rows=[]
for name,ly,a,z in requests:
 oa,ga=terminal(a,ly);oz,gz=terminal(z,ly);net=oa.GetNetname();assert net==oz.GetNetname()
 free,vf,blocked,allowed=p.geometry(net)
 for i,l in enumerate(p.layers):
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==l])
  lands=unary_union([s for (u,ll),s in c.shapes.items() if ll==l and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=blocked[i].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 for i,l in enumerate(p.layers):
  if l!=ly:free[i][:]=False
 vf[:]=False
 print(name,'search',flush=True)
 r=p.solve(ga,gz,(free,vf,blocked,allowed),300000)
 rows.append(dict(request=name,net=net,from_terminal=a,to_terminal=z,from_mm=list(xy(oa.GetPosition())),to_mm=list(xy(oz.GetPosition())),result=r))
 out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,results=rows,adopted=False),indent=2)+'\n')
 print(name,r,flush=True)
