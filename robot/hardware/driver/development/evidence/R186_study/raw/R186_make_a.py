"""Joint UPS port preparation, sampling-tail relocation and shorter C1002 return.

Independent candidate only. Original full-width supplies, references and every
existing pad connection must be recovered before any adoption is considered.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from ground_via_moves import validate_ground_via_moves
b=Path('robot/.state/c3-completion/trials');out=b/'R186A-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
wheel='Net-(U1001-S2_{slash}_WHEEL_sense)';scl='/01 {slash} Core/UPS_SCL_MCU';sda='/01 {slash} Core/UPS_SDA_MCU'
gv='9de23d3c-b74e-4fac-9c4e-98d191bd73df';sv='68fd19fb-550e-48aa-9664-2b3293e9421c'
ground_tracks=['f1ba4665-1ebb-46a4-9d98-a23a0f62e879','4b54c41d-1434-40fd-b86b-23fffa02e7d5','16d2b710-a72b-46ff-95c8-43292c6deb43','5c02e4f5-8254-4386-8e2a-617bde214145']
deleted=ground_tracks+['77ba0ea0-5ca3-4421-aa6a-659f3538a16d','b047e09b-e1e9-4107-8fd4-39697f2fd9a5','fad834e3-3d03-447c-82a3-772b9e996450','2fb3da79-8035-4e3d-9d30-d38b582efa1b','7e742981-2298-49b0-96f5-fab746780408','46b45438-08f9-40a3-97c0-eeccfd4d2b5b']
def route(net,layer,points,width=.2):return dict(net=net,layer=layer,width_mm=width,points_mm=points)
pad=next(p for p in c.pads if c.pad_name(p)=='C1002.2');f=next(f for f in c.footprints if f.GetReference()=='D1801')
contacts=sorted(uid(t) for t in c.segments if t.GetNetname()=='GND' and shape(t,t.GetLayer()).intersects(shape(c.by_id[gv],t.GetLayer())))
plan=dict(revision='R186A',board_sha256=c.sha,scope=__doc__,
 translations=[dict(reference='D1801',from_mm=list(xy(f.GetPosition())),delta_mm=[-.025,-.1],reconstruct_fixed_via_guards=True,repartition_fixed_via_guards=True)],
 delete_copper=deleted,deleted_copper_expected={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in deleted},
 move_ground_vias=[dict(uuid=gv,source_expected=via_snapshot(c.board,c.by_id[gv]),position_mm=[53.2,14.25],reason='Shorten C1002 direct return and release the shared UPS signal escape corridor; preserve exact via/padstack and all actual plane/source-power checks.',source_contact_track_uuids=contacts,
 return_paths=[dict(pad_uuid=uid(pad),layer='B.Cu',source_track_uuids=ground_tracks,source_pad_exit_mm=[52.25,15.275],replacement_route_indices=[0])])],
 reassign_vias=[dict(uuid=sv,source_expected=via_snapshot(c.board,c.by_id[sv]),net=scl,reason='Reuse the old sampling transfer for the UPS SCL escape; the complete sampling tail is replaced explicitly.')],
 routes=[route('GND','B.Cu',[[51.9,15.275],[52.175,15.275],[53.2,14.25]]),
 route(wheel,'B.Cu',[[51.9,13.725],[51.2,13.025]]),
 route(wheel,'In3.Cu',[[52.95,10],[52.95,10.8265],[51.2,12.5765],[51.2,13.025]]),
 route('Net-(U1702-INA+)','F.Cu',[[49.875,12.45],[53.65,12.45],[53.85,12.25],[58.7375,12.25],[58.9375,12.45]]),
 route(scl,'B.Cu',[[55.575,10.8625],[55.575,12.6121],[55.1553,13.0318]]),
 route(sda,'B.Cu',[[54.925,10.8625],[54.925,11.95],[54.275,12.6],[54,12.6],[53.3,13.3]])],
 vias=[dict(net=wheel,position_mm=[51.2,13.025],diameter_mm=.5,drill_mm=.3),dict(net=sda,position_mm=[53.3,13.3],diameter_mm=.5,drill_mm=.3)])
print(json.dumps(validate_ground_via_moves(c.board,plan),indent=2))
out.write_text(json.dumps(plan,indent=2)+'\n')
