"""Remove the obsolete INA300 VS transfer and reuse the existing upper 3V3 via.

R170J is an unadopted comparison. This explicit plan is rebuilt from R168G,
retaining every source GND via and native rule. Move R1701 up 0.10 mm to test
clearance for a short B supply path between its pad and the original GND stitch.
RLIMIT direct return and every other original function still require restoration.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R171A-plan.json';assert not out.exists();p=json.loads((b/'R170J-plan.json').read_text());c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
for u in ['35011640-47d5-43d9-aa07-7c7e24d3d8e5','bc3e9793-b9cd-54b1-b44c-64b91f6e9a06']:
 t=c.by_id[u];assert u not in p['delete_copper'];p['delete_copper'].append(u);p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
v=c.by_id['aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57'];contacts=via_contact_layers(c.board,v,p['delete_copper']);print('remaining contacts',contacts,flush=True);assert len(contacts)<=1
p['remove_obsolete_vias']=[dict(uuid=uid(v),source_expected=via_snapshot(c.board,v),remaining_contact_layers=contacts,reason='The original F/B transfer is replaced by a B connection to unchanged 3V3 via (47.15,10.55); after retiring its two leads, this non-ground via has no multi-layer transfer function and violates the rotated INA300 native guard.')]
for spec in p['translations']:
 if spec['reference']=='R1701':spec['delta_mm']=[.1,-.05] # source (47.275,9.7) -> (47.375,9.65)
p['routes'].append(dict(net='MOTION_3V3',layer='B.Cu',width_mm=.2,points_mm=[[44.0,11.35],[44.0,10.875],[45.35,10.875],[45.75,10.475],[46.85,10.475],[46.925,10.55],[47.15,10.55]]))
p.update(revision='R171A',scope=__doc__,adoption_prohibited=True);out.write_text(json.dumps(p,indent=2)+'\n')
