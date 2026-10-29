"""Buildable reconstruction of the R150 multi-layer OV proposal, from R148E.

Preserve the unadopted local R150D preparation and its known K/NRST conflict.
Replace the complete old OV In3 branch, with exact existing-via endpoints.
All proposed segments are screened before a native candidate is constructed.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R151A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
net='Net-(U1301-INB-_{slash}_OV)'
routes=[
 dict(net=net,layer='In3.Cu',width_mm=.2,points_mm=[[60.55,17.0],[60.55,17.4],[61.15,18.0],[61.15,21.2],[61.25,21.3]]),
 dict(net=net,layer='B.Cu',width_mm=.2,points_mm=[[61.25,21.3],[61.25,22.15],[60.85,22.55],[60.85,22.85]]),
 dict(net=net,layer='In3.Cu',width_mm=.2,points_mm=[[60.85,22.85],[60.35,22.85],[59.8,23.4],[59.8,24.6],[61.25,26.05],[62.4,26.05],[64.275,27.925],[64.275,28.8]])]
planner=Planner(b/'R150B/MORI_Interface_C3.kicad_pcb',.1,['B.Cu','In3.Cu','F.Cu'],.2)
pc=planner.c;_,_,blocked,allowed=planner.geometry(net);blocked=list(blocked)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
d=json.loads((b/'R149-soft-obstacle-diagnostic/diagnosis.json').read_text())[0]
for i,ly in enumerate(planner.layers):
    if ly in ['B.Cu','F.Cu']:
        bodies=unary_union([fab(f) for f in pc.footprints if pc.board.GetLayerName(f.GetLayer())==ly])
        own=unary_union([s for (u,l),s in pc.shapes.items() if l==ly and isinstance(pc.by_id[u],pcb.PAD) and pc.by_id[u].GetNetname()==net])
        blocked[i]=blocked[i].union(bodies.buffer(.102).difference(own.buffer(-.001)))
    blocked[i]=blocked[i].union(unary_union([LineString(r['points_mm']).buffer(.405) for r in d['routes'] if r['layer']==ly]))
checks=[]
for r in routes:
    i=planner.layers.index(r['layer'])
    for a,z in zip(r['points_mm'],r['points_mm'][1:]):
        line=LineString([a,z]);checks.append(dict(layer=r['layer'],start=a,end=z,blocked=bool(line.intersects(blocked[i])),reference_allowed=bool(allowed[i].covers(line))))
(b/'R151A-endpoint-screen.json').write_text(json.dumps(dict(scope=__doc__,screen_board_sha256=pc.sha,checks=checks),indent=2)+'\n')
assert all(not r['blocked'] and r['reference_allowed'] for r in checks), 'Endpoint reconstruction rejected; see screen report'
p=json.loads((b/'R150D-plan.json').read_text());p.update(revision='R151A',scope=__doc__)
for t in c.segments:
    if t.GetNetname()!=net or c.board.GetLayerName(t.GetLayer())!='In3.Cu':continue
    u=uid(t);assert u not in p['delete_copper'];p['delete_copper'].append(u)
    p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer='In3.Cu',width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'].extend(routes)
p['vias'].extend(dict(net=net,position_mm=pos,diameter_mm=.5,drill_mm=.3) for pos in [[61.25,21.3],[60.85,22.85]])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
