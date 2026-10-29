"""Complete the candidate filter path and repair the HEAD_VM width neck.

Preserve the original OV tail and CAM thermal routing; replace only the one
diagnosed crossing segment, which must still be reconnected in a later step.
The current-filter endpoints are reconstructed to real copper and via centres.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R151E-plan.json';assert not out.exists()
p=json.loads((b/'R151D-plan.json').read_text());p.update(revision='R151E',scope=__doc__)
ov='Net-(U1301-INB-_{slash}_OV)';cross='8bc8d6c2-cfce-4b18-a22d-1c1e34ec824c'
restored=[]
for u in list(p['delete_copper']):
    snap=p['deleted_copper_expected'][u]
    if snap['net']==ov and u!=cross:
        restored.append((u,LineString([snap['start_mm'],snap['end_mm']]).buffer(snap['width_mm']/2)))
        p['delete_copper'].remove(u);del p['deleted_copper_expected'][u]
assert len(restored)==9
net='/ACT_CURRENT_FILTERED'
q=json.loads((b/'R151D_FILTER-search/plan-0-1.json').read_text())
q['routes'][0]['points_mm']=[[58.7,23.675],[58.7,22.25],[59.05,21.9],[60.65,21.9],[61.25,21.3]]
q['routes'][1]['points_mm'][-1:]=[[30.9,5.95],[31.0,5.85]]
planner=Planner(b/'R151D/MORI_Interface_C3.kicad_pcb',.1,['F.Cu','In3.Cu'],.2);c=planner.c
_,_,blocked,allowed=planner.geometry(net);blocked=list(blocked)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.F_Cu])
own=unary_union([s for (u,l),s in c.shapes.items() if l=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
blocked[0]=blocked[0].union(bodies.buffer(.102).difference(own.buffer(-.001)))
checks=[]
for r in q['routes']:
    i=planner.layers.index(r['layer'])
    for a,z in zip(r['points_mm'],r['points_mm'][1:]):
        line=LineString([a,z]);checks.append(dict(layer=r['layer'],start=a,end=z,blocked=bool(line.intersects(blocked[i])),reference_allowed=bool(allowed[i].covers(line)),restored_OV_hits=[u for u,s in restored if r['layer']=='In3.Cu' and line.buffer(.1).distance(s)<.2-1e-7]))
(b/'R151E-filter-screen.json').write_text(json.dumps(dict(scope=__doc__,screen_board_sha256=c.sha,checks=checks),indent=2)+'\n')
assert all(not r['blocked'] and r['reference_allowed'] and not r['restored_OV_hits'] for r in checks), 'Filter reconstruction failed; inspect screen report'
p['routes'].extend(q['routes']);p['vias'].extend(q['vias'])
bridge=json.loads((b/'R151D-HEADVM-bridge/result.json').read_text())
assert bridge['result']['status']=='PROPOSAL' and not bridge['result']['vias']
p['routes'].extend(dict(net='/HEAD_VM',**r) for r in bridge['result']['routes'])
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
