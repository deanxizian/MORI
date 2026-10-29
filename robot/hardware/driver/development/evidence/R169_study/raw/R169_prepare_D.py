"""Independent INA300 half-turn plus R1310 placement and FAULT escape port.

R1310 moves to F (51.25,14.25)/0 degrees using a native courtyard/pad/guard
screen. Retire only its three old F leads; every existing via is kept. New
FAULT B escape and (49.45,14.0) via are proposals. INA300 originals and R1310
connections remain incomplete and must be restored before adoption.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R169D-plan.json';assert not out.exists();p=json.loads((b/'R169B-plan.json').read_text());c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha==p['board_sha256']
p['translations'].append(dict(reference='R1310',from_mm=[49.5,14.25],delta_mm=[1.75,0],rotation_deg=0))
for i in ['bcdd7ab3-adde-4d13-afc7-60400ae05dc1','f53097d6-39cd-41f5-a174-4720708ce322','3c59ab5a-ed77-4497-bfe1-918eab519360']:
 t=c.by_id[i];p['delete_copper'].append(i);p['deleted_copper_expected'][i]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p['routes']=[dict(net='/FAULT_N',layer='B.Cu',width_mm=.2,points_mm=[[49.45,13.35],[49.45,14]])]
p['vias']=[dict(net='/FAULT_N',position_mm=[49.45,14],diameter_mm=.5,drill_mm=.3)]
p.update(revision='R169D',scope=__doc__,adoption_prohibited=True);out.write_text(json.dumps(p,indent=2)+'\n')
