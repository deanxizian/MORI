"""Jointly separate the right ACT/3V3 transfers and reconnect their full leads.

From canonical R165M, preserve C's complete plan but move C1702 0.25 mm
up, the original right ACT transfer to (59.7,14.6) and original right 3V3
transfer to (60.925,13.475). The F INA+ lead moves around the ACT transfer;
the original B and In3 ACT leads and B 3V3 bend are explicitly replaced.
All 114 source GND vias remain fixed. This is an independent native trial;
no claim of a usable FAULT corridor precedes DRC/refill/reference checks.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168D-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R168C-plan.json').read_text());assert p['board_sha256']==c.sha
next(t for t in p['translations'] if t['reference']=='C1702')['delta_mm']=[.125,-.375]
for u,pos,net in [('4312a4e0-e664-44e0-a44a-716dd81b836a',[59.7,14.6],'/17 {slash} Actuator_Overcurrent/ACT_UV_N'),('e81f1421-0f0e-4b1c-9a73-ed7af0f79a65',[60.925,13.475],'MOTION_3V3')]:
 v=c.by_id[u];assert v.GetNetname()==net
 p['move_vias'].append(dict(uuid=u,source_expected=via_snapshot(c.board,v),position_mm=pos,reason='Joint local transfer separation with complete explicit replacement of original terminal leads; no ground via moves or rule relaxation.'))
for u in ['64c33dbe-831a-4348-8867-180d933014b9','0d2eb667-e5ff-57d9-9e77-42e6ca29632a','3c035269-ca47-599c-9993-22dfabca192e','d31e2045-4d15-49d7-a9ac-9567a50cdd95']:
 t=c.by_id[u];assert not isinstance(t,pcb.PCB_VIA)
 p['delete_copper'].append(u)
 p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes'][3]['points_mm']=[[58.775,14.775],[59.525,14.775],[59.7,14.6]]
p['routes'][5]['points_mm']=[[60.05,12.575],[60.3,12.825],[60.3,15.1],[59.2,16.2],[59.2,16.3875],[58.95,16.3875]]
p['routes'][7]['points_mm']=[[59.625,13.6],[60.8,13.6],[60.925,13.475]]
p['routes'] += [dict(net='/17 {slash} Actuator_Overcurrent/ACT_UV_N',layer='In3.Cu',width_mm=.2,points_mm=[[59.7,14.6],[60.6,14.6],[61.5,15.5]]),dict(net='MOTION_3V3',layer='B.Cu',width_mm=.5,points_mm=[[61.3,13.1],[60.925,13.475]])]
p.update(revision='R168D',scope=__doc__,adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
