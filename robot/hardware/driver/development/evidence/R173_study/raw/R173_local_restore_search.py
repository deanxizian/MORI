"""Sequential local B-face direct-loop restoration proposals on a native trial.

Keep native clearance, reference, body rules and all pads/vias. Every earlier
proposal becomes a same-face obstacle for later different-net proposals. No new
via or saved PCB; native refill and full old-connection/power checks are required.
"""
import ast,json,sys,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-local-restore');out.mkdir(exist_ok=False)
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.025,['B.Cu'],.2);c=p.c
p.xs=np.arange(40,54.001,.025);p.ys=np.arange(5,20.001,.025);p.xx,p.yy=np.meshgrid(p.xs,p.ys)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu]);pads={c.pad_name(q):q for q in c.pads}
tasks=[('rlimit_direct_gnd','R1701.1','U1701.8'),('ina_bypass_gnd','C1701.2','U1701.8'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_limit','R1701.2','U1701.3'),('supervisor_ct','R1310.1','U1302.4'),('supervisor_vdd','C1304.1','U1302.5'),('supervisor_gnd','C1304.2','U1302.2')]
rows=[];newroutes=[]
for name,an,bn in tasks:
 aa,bb=pads[an],pads[bn];net=aa.GetNetname();assert net==bb.GetNetname()
 a=dict(pads=[an],layers={'B.Cu':c.shapes[uid(aa),'B.Cu']});z=dict(pads=[bn],layers={'B.Cu':c.shapes[uid(bb),'B.Cu']})
 start=time.monotonic();free,vf,blocked,allowed=p.geometry(net)
 lands=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 obstacles=[blocked[0],bodies.buffer(.102).difference(lands.buffer(-.001))]
 obstacles += [LineString(r['points_mm']).buffer(r['width_mm']/2+.205+p.width/2) for r in newroutes if r['net']!=net]
 blocked[0]=unary_union(obstacles);free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
 result=p.solve(a,z,(free,np.zeros_like(vf),blocked,allowed),900000)
 if result['status']=='PROPOSAL':newroutes.extend(dict(r,net=net) for r in result['routes'])
 row=dict(name=name,net=net,pads=[an,bn],result=result,elapsed_seconds=time.monotonic()-start);rows.append(row)
 (out/'searches.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=.025,bounds_mm=[40,5,54,20],sequential_proposal_obstacles=True,results=rows,new_routes=newroutes,adopted=False),indent=2)+'\n')
 print(json.dumps({**row,'result':{k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']}}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
