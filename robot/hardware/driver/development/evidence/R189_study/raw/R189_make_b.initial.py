"""Independent RAW escape using a relocated wheel-level signal transfer.

Retain all GND vias and the OV In2 path. Replace the long OV F detour by a
straight approach beside J401, restore both tails of the moved U402 transfer,
and expose RAW. No global connection or manufacturing acceptance is claimed.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R189B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
ov='Net-(U1301-INB-_{slash}_OV)';wheel='Net-(U402-1Y)'
retained={'466156db-1b96-47be-98fd-374c6d5c2fec','89087538-cea6-47e9-9b62-78e1e2fae6b2','d199d541-588a-561c-814a-056c6dacd8b2'}
deleted=[uid(t) for t in c.segments if t.GetNetname()==ov and t.GetLayer()==pcb.F_Cu and uid(t) not in retained]
deleted+=['38b1aa1f-6d6c-5391-ae66-8dc9df61b001','ad23fc9d-55cc-5e3c-910c-9b49312999af']
assert len(deleted)==14
v='5cc2b6b0-e919-4910-b0af-8902a95393d9'
def route(net,layer,pts):return dict(net=net,layer=layer,width_mm=.2,points_mm=pts)
plan=dict(revision='R189B',board_sha256=c.sha,scope=__doc__,delete_copper=deleted,
 deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
 move_vias=[dict(uuid=v,source_expected=via_snapshot(c.board,c.by_id[v]),position_mm=[59,17.975])],
 routes=[route(ov,'F.Cu',[[60.55,17],[60.9,17.35],[60.9,22.9]]),
 route(wheel,'B.Cu',[[59.6,17.175],[59,17.775],[59,17.975]]),
 route(wheel,'In2.Cu',[[58.475,16.9],[59,17.425],[59,17.975]]),
 route('/HEAD_6V_RAW','B.Cu',[[60.45,18.925],[59.875,18.35],[59.65,18.35]])],
 vias=[dict(net='/HEAD_6V_RAW',position_mm=[59.65,18.35],diameter_mm=.5,drill_mm=.3)])
with out.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps(dict(retired=len(deleted),new_segments=sum(len(x['points_mm'])-1 for x in plan['routes']),source_sha256=c.sha)))
