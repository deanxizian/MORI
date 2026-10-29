"""Remove two local preparation defects without hiding the CAM/GND blockers.
Use a single 0.50-mm UPS_5V branch into the existing vertical capacitor feed;
shift R1022 away from the retained H_DUMP_SENSE via. ADC In3 is still open.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143N-plan.json';assert not out.exists()
c=Copper(str(b/'R143M/MORI_Interface_C3.kicad_pcb'));m=json.loads((b/'R143M/edit_manifest.json').read_text())
p={'revision':'R143N','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[23.4,16.2],'delta_mm':[-.1,-.1],'rotation_deg':270}],'delete_copper':[],'deleted_copper_expected':{},'routes':[]}
for row in m:
 if row['kind']=='track' and row['net']=='/06 {slash} CAM_Buck/UPS_5V':
  t=c.by_id[row['uuid']];u=uid(t);p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':'F.Cu','width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
assert len(p['delete_copper'])==3
p['routes']=[{'net':'/06 {slash} CAM_Buck/UPS_5V','layer':'F.Cu','width_mm':.5,'points_mm':[[22.5,14.7],[23.525,14.7]]}]
out.write_text(json.dumps(p,indent=2)+'\n')
