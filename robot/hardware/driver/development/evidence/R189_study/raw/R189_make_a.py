"""Independent RAW port preparation with complete OV and R1307 ground recovery.

Keep all footprints and interfaces. Reroute the existing OV transfer pair on
In3, slightly move one GND via with a shorter direct return, and expose the RAW
terminal through one new via. The remaining global RAW route is still required.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from ground_via_moves import validate_ground_via_moves
b=Path('robot/.state/c3-completion/trials');out=b/'R189A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
gids=['e4a81c6a-0f7b-51ec-bfa7-1740c29a5705','28290012-2af5-5ae0-8195-1b405caa228f']
ovids=['17ba0129-9826-4ed3-81b0-f1ae47427144','b2c91013-fbf9-4e6e-81d5-36b2363b7987','ca502b74-cb95-4ee5-a0c1-707a1bbb85a9','f8b0c5de-3049-48b4-9985-faffdd80f24e']
gv='45e4d5ec-0663-48d5-bee4-df6e2a0d14a3';pad=next(p for p in c.pads if c.pad_name(p)=='R1307.1')
contacts=sorted(uid(t) for t in c.segments if t.GetNetname()=='GND' and shape(t,t.GetLayer()).intersects(shape(c.by_id[gv],t.GetLayer())))
deleted=gids+ovids
def route(net,layer,points,width=.2):return dict(net=net,layer=layer,width_mm=width,points_mm=points)
plan=dict(revision='R189A',board_sha256=c.sha,scope=__doc__,delete_copper=deleted,
 deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
 move_ground_vias=[dict(uuid=gv,source_expected=via_snapshot(c.board,c.by_id[gv]),position_mm=[60.4,17.925],reason='Retain a short R1307 divider return while exposing RAW; explicit all-layer and actual fill review required.',source_contact_track_uuids=contacts,
 return_paths=[dict(pad_uuid=uid(pad),layer='B.Cu',source_track_uuids=gids,source_pad_exit_mm=[62.2,17.3],replacement_route_indices=[0])])],
 routes=[route('GND','B.Cu',[[62.2,17.125],[61.2,17.125],[60.4,17.925]],.3),
 route('Net-(U1301-INB-_{slash}_OV)','In3.Cu',[[60.55,17],[59.375,17],[58.1,18.275],[58.1,18.9],[57.375,18.9]]),
 route('/HEAD_6V_RAW','B.Cu',[[60.45,18.925],[61.1,18.275],[61.1,18.1]])],
 vias=[dict(net='/HEAD_6V_RAW',position_mm=[61.1,18.1],diameter_mm=.5,drill_mm=.3)])
validation=validate_ground_via_moves(c.board,plan)
with (b/'R189A-ground-plan-validation.json').open('x') as f:json.dump(validation,f,indent=2);f.write('\n')
with out.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(validation))
