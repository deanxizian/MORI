"""Keep the IMU-reference repair and reroute the affected WHEEL_TX tail.

The A trial exposed an actual In2 clearance/reference collision at the moved
sampling transfer. Replace that explicit tail at the same 0.20 mm width; the
power planes, original connections and every native rule must still pass.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R187B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
plan=json.loads((b/'R187A-plan.json').read_text());assert plan['board_sha256']==c.sha
plan.update(revision='R187B',scope=__doc__)
for u in ['8810cd1f-de34-4e47-b0de-3a2b96db87e6','f75a488c-0442-45ff-98da-c51572a36518']:
    t=c.by_id[u];assert t.GetNetname()=='/01 {slash} Core/WHEEL_TX' and t.GetLayer()==pcb.In2_Cu
    plan['delete_copper'].append(u)
    plan['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer='In2.Cu',width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
plan['routes'].append(dict(net='/01 {slash} Core/WHEEL_TX',layer='In2.Cu',width_mm=.2,
    points_mm=[[38.83,7.85],[46.2,7.85],[46.6,8.25],[47.45,8.25],[48,7.7]]))
out.write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(revision='R187B',retired_tracks=len(plan['delete_copper']),new_routes=len(plan['routes']))))
