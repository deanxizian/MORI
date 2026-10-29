"""Compare a straight comparator-input corridor with coordinated sample/ground transfers.

No component, circuit, outline or native-rule change. Move the sampling transfer
and shorten the C1002 direct GND return together; preserve every source power,
ground, reference and native check before considering development adoption.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from ground_via_moves import validate_ground_via_moves
b=Path('robot/.state/c3-completion/trials');out=b/'R188A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='6dbcf638a4292c080a05c01f46f9317d69bd655f37d57f0da46d6e3d3bfcb876'
gv='9de23d3c-b74e-4fac-9c4e-98d191bd73df';sv='68fd19fb-550e-48aa-9664-2b3293e9421c'
ground=['f1ba4665-1ebb-46a4-9d98-a23a0f62e879','4b54c41d-1434-40fd-b86b-23fffa02e7d5','16d2b710-a72b-46ff-95c8-43292c6deb43','5c02e4f5-8254-4386-8e2a-617bde214145']
deleted=ground+['fad834e3-3d03-447c-82a3-772b9e996450','b047e09b-e1e9-4107-8fd4-39697f2fd9a5','7e742981-2298-49b0-96f5-fab746780408',
    '46b45438-08f9-40a3-97c0-eeccfd4d2b5b','c6322a91-08ee-5998-bebe-d80c60939e6c','d765e723-dcaa-5ea2-a388-08b21b5adb6b']
pad=next(p for p in c.pads if c.pad_name(p)=='C1002.2')
contacts=sorted(uid(t) for t in c.segments if t.GetNetname()=='GND' and shape(t,t.GetLayer()).intersects(shape(c.by_id[gv],t.GetLayer())))
def route(net,layer,points):return dict(net=net,layer=layer,width_mm=.2,points_mm=points)
wheel='Net-(U1001-S2_{slash}_WHEEL_sense)';comp='Net-(U1702-INA+)'
plan=dict(revision='R188A',board_sha256=c.sha,scope=__doc__,delete_copper=deleted,
    deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
    move_ground_vias=[dict(uuid=gv,source_expected=via_snapshot(c.board,c.by_id[gv]),position_mm=[53.6,13.45],
      reason='Shorter C1002 direct return and clearance for relocated sampling transfer; actual both-plane attachment and all original power/reference checks remain required.',source_contact_track_uuids=contacts,
      return_paths=[dict(pad_uuid=uid(pad),layer='B.Cu',source_track_uuids=ground,source_pad_exit_mm=[52.25,15.275],replacement_route_indices=[0])])],
    move_vias=[dict(uuid=sv,source_expected=via_snapshot(c.board,c.by_id[sv]),position_mm=[54.8,13.45],reason='Restore comparator reference while preserving sampling transfer identity and original B/In3 contacts.')],
    routes=[route('GND','B.Cu',[[51.9,15.275],[52.25,15.275],[52.6,14.925],[52.6,14.45],[53.6,13.45]]),
      route(wheel,'B.Cu',[[52.9975,12.6275],[53.9775,12.6275],[54.8,13.45]]),
      route(wheel,'In3.Cu',[[52.95,10.8265],[54.8,12.6765],[54.8,13.45]]),
      route(comp,'F.Cu',[[49.875,12.45],[50.075,12.65],[60.825,12.65],[60.9,12.575]]),
      route(comp,'F.Cu',[[59.925,12.65],[59.925,13.825]])])
validation=validate_ground_via_moves(c.board,plan)
with out.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
with (b/'R188A-ground-plan-validation.json').open('x') as f:json.dump(validation,f,indent=2);f.write('\n')
print(json.dumps(validation))
