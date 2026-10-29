"""Coupled screen of legal local FAULT ports and U1702 VDD restoration.

For each native legal through-via position reachable directly on B from Q1701,
subtract its prospective In1 ground clearance before searching the F supply
lead. No PCB or rule is modified. Native refill remains mandatory.
"""
import ast,json,sys,math
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-port-supply-screen.json');assert not out.exists()
p=Planner(b/rev/'MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
def geometries(net):
 free,vf,obs,al=p.geometry(net)
 for i,l in enumerate(p.layers):
  if l not in ['B.Cu','F.Cu']:continue
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==l])
  lands=unary_union([s for (u,ll),s in c.shapes.items() if ll==l and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  obs[i]=obs[i].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
 free=np.array([~mask(o,p.xx,p.yy)&mask(a,p.xx,p.yy,True) for o,a in zip(obs,al)])
 return free,vf,obs,al
ff,vf,fo,fa=geometries('/FAULT_N');q=next(q for q in c.pads if c.pad_name(q)=='Q1701.3')
starts=mask(c.shapes[uid(q),'B.Cu'].buffer(-.001),p.xx,p.yy,True)&ff[0]
lab,n=ndimage.label(ff[0],np.ones((3,3)));region=np.isin(lab,np.unique(lab[starts]))
sites=region&vf&((ff[2]&p.ground_near)|ff[3]);ys,xs=np.where(sites)
ports=[[round(float(p.xs[x]),6),round(float(p.ys[y]),6)] for y,x in zip(ys,xs)]
print('direct B ports',ports,flush=True)
free,_,obs,al=geometries('MOTION_3V3')
pad=next(q for q in c.pads if c.pad_name(q)=='U1702.5');via=c.by_id['91ef992b-7d59-4fdf-9c25-f80e62b58f1e']
a=dict(pads=['U1702.5'],layers={'F.Cu':c.shapes[uid(pad),'F.Cu']})
z=dict(pads=[uid(via)],layers={'F.Cu':c.shapes[uid(via),'F.Cu']})
rows=[]
for pos in ports:
 # Actual future native ground clearance is at least the unchanged inner zone
 # clearance. A margin is added for the polygon/raster approximation.
 hole=Point(pos).buffer(.25+p.internal_clearance+.005)
 all_al=list(al);all_ob=list(obs)
 all_al[1]=al[1].difference(hole.buffer(.102)).union(c.shapes[uid(pad),'F.Cu'].buffer(-.102))
 all_ob[1]=obs[1].union(Point(pos).buffer(.25+.205+.1))
 fs=np.zeros(free.shape,dtype=bool);fs[1]=~mask(all_ob[1],p.xx,p.yy)&mask(all_al[1],p.xx,p.yy,True)
 r=p.solve(a,z,(fs,np.zeros(vf.shape,dtype=bool),all_ob,all_al),150000)
 rows.append(dict(port_mm=pos,result=r));print(pos,r['status'],r.get('length_mm'),flush=True)
 out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,direct_B_ports=ports,results=rows,adopted=False),indent=2)+'\n')
