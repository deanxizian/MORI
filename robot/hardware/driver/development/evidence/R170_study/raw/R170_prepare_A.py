"""Original INA300 pose with explicit replacement of four crossing old tracks.

R169C diagnoses a B escape region after retiring six LIMIT tracks. A keeps all
parts/guards/vias fixed, retires those six LIMIT segments plus four identified
S2, D1001-K and WHEEL_TX segments, and tests a new FAULT port above Q1601. All
retired original connections and LIMIT must be restored before adoption.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R170A-plan.json';assert not out.exists()
p=Planner(b/'R169C/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c;net='/FAULT_N';port=[43.6,7.4]
n=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[n],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net);body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu]);lands=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);blocked[0]=blocked[0].union(body.buffer(.102).difference(lands.buffer(-.001)));free[0]=~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True);free[1:]=False;vf[:]=False
a=next(g for g in p.routing_groups(net) if 'U1701.5' in g['pads']);z=dict(pads=['prospective_FAULT_port'],layers={'B.Cu':Point(port).buffer(.03)})
r=p.solve(a,z,(free,vf,blocked,allowed),500000);(b/'R170A-escape-proposal.json').write_text(json.dumps(r,indent=2)+'\n');assert r['status']=='PROPOSAL' and not r['vias'];print(json.dumps(r),flush=True)
plan=json.loads((b/'R169C-plan.json').read_text());source=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert source.sha==plan['board_sha256']
for i in ['6a3bf882-25d0-5397-8429-bceb319b1674','8810cd1f-de34-4e47-b0de-3a2b96db87e6','5fb83ea2-603e-4b06-aaa4-799eaf73dfec','78bf16e7-6750-4c80-b037-513416bf8972']:
 t=source.by_id[i];plan['delete_copper'].append(i);plan['deleted_copper_expected'][i]=dict(net=t.GetNetname(),layer=source.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
plan['routes']=[dict(q,net=net) for q in r['routes']];plan['vias']=[dict(net=net,position_mm=port,diameter_mm=.5,drill_mm=.3)];plan.update(revision='R170A',scope=__doc__,adoption_prohibited=True);out.write_text(json.dumps(plan,indent=2)+'\n')
