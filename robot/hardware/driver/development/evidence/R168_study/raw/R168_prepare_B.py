"""Reconstruct the joint group with explicit supply, signal and ground leads.

The saved A preparation reassigned its orphaned moved ACT via to GND, and the
builder rejected the readback. B keeps that failure intact and connects moved
transfers explicitly to the correct native pads before saving. It also moves
the original 3V3 transfer to (55.4,13.8), above the new signal holes, and gives
U1702.2 an explicit F return to the unchanged GND via (57.475,18.2).
Native DRC, fill, electrical/reference and body checks remain mandatory.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168B-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R168A-plan.json').read_text());assert p['board_sha256']==c.sha
u='91ef992b-7d59-4fdf-9c25-f80e62b58f1e';v=c.by_id[u];assert v.GetNetname()=='MOTION_3V3'
p['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,v),position_mm=[55.4,13.8],reason='Keep the original 3V3 supply transfer above the new local signal clearances and explicitly reconnect U1702 VDD. Its identity, net, drill and annulus stay unchanged; source power-width checks remain required.'))
act='/17 {slash} Actuator_Overcurrent/ACT_UV_N';port=[56.35,14.9]
routes=[
 dict(net='/HEAD_UV_ENABLE',layer='B.Cu',points_mm=[[57.9847,11.875],[56.9875,11.875],[56.175,12.6875],[56.175,13.0625]]),
 dict(net=act,layer='F.Cu',points_mm=[[57.05,16.3875],[56.8125,16.3875],[55.825,15.4]]),
 dict(net=act,layer='B.Cu',points_mm=[[58.075,13.0625],[58.35,13.0625],[58.575,13.2875],[58.575,15.4]]),
 dict(net=act,layer='B.Cu',points_mm=[[58.575,14.775],[58.925,14.775]]),
 dict(net=act,layer='B.Cu',points_mm=[[55.825,15.4],[55.825,15.6],[56.225,16],[57.7,16],[58.3,15.4],[58.575,15.4]]),
 dict(net='Net-(U1702-INA+)',layer='F.Cu',points_mm=[[59.6,12.575],[59.6,16.1],[59.3125,16.3875],[58.95,16.3875]]),
 dict(net='MOTION_3V3',layer='F.Cu',width_mm=.25,points_mm=[[58,14.1125],[58,13.5],[57.6,13.1],[56.3,13.1],[55.6,13.8],[55.4,13.8]]),
 dict(net='MOTION_3V3',layer='B.Cu',width_mm=.25,points_mm=[[59.625,13.85],[60.15,13.85],[60.475,13.525],[60.725,13.525]]),
 dict(net='GND',layer='F.Cu',width_mm=.25,points_mm=[[58,16.3875],[58,17.675],[57.475,18.2]]),
 dict(net='/FAULT_N',layer='B.Cu',points_mm=[[57.125,14.9375],port]),
]
for r in routes:r.setdefault('width_mm',.2)
p.update(revision='R168B',scope=__doc__,routes=routes,vias=[dict(net='/FAULT_N',position_mm=port,diameter_mm=.5,drill_mm=.3)],adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
