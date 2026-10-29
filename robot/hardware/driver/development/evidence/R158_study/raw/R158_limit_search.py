"""Read-only alternate LIMIT routing after the top-group placement comparison.

The probe removes only native LIMIT tracks from an unadopted failed board.
It is not a repaired board: all original R158C failures remain to be resolved.
No source board is saved and no new route is accepted by this search.
"""
import ast,json,sys,shutil
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R158-LIMIT-search';out.mkdir(exist_ok=False);source=b/'R158C/MORI_Interface_C3.kicad_pcb';probe=out/'MORI_Interface_C3.kicad_pcb';board=pcb.LoadBoard(str(source));net='Net-(U1701-LIMIT)';removed=[]
for t in list(board.GetTracks()):
 if t.GetNetname()==net:removed.append(uid(t));board.Remove(t)
pcb.SaveBoard(str(probe),board);shutil.copy2(source.with_suffix('.kicad_dru'),probe.with_suffix('.kicad_dru'))
p=Planner(probe,.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free,vf,blocked,allowed=p.geometry(net)
for k,ly in enumerate(p.layers):
 if ly=='In3.Cu':continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);own=unary_union([g for (u,l),g in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);blocked[k]=unary_union([blocked[k],bodies.buffer(.102).difference(own.buffer(-.001))])
free=np.asarray([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)]);gs=p.routing_groups(net);assert len(gs)==2
r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),650000)
(out/'result.json').write_text(json.dumps({'scope':__doc__,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'probe_sha256':c.sha,'removed_track_uuids':removed,'groups':[x['pads'] for x in gs],'result':r,'adopted':False},indent=2)+'\n');print(json.dumps(r),flush=True)
