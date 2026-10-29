"""Reduce the preparation scope: retain D301/ARMED and the original OV branch.

Keep the lower CLR branch outside the original D301 body, escape the top CLR
from the outer portion of its own pad, and move the 0.60 mm power via only
0.03 mm. Native checks must establish whether this preserves power and reference.
The current-filter through connection is intentionally still unfinished.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R150D-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R150C-plan.json').read_text());p.update(revision='R150D',scope=__doc__)
p['translations']=[r for r in p['translations'] if r['reference']!='D301']
p['move_vias']=[v for v in p['move_vias'] if v['uuid']!='b049d7c8-9984-50be-a63c-ab8f19b37c43']
p['move_vias'][-1]['position_mm']=[34.85,13.02]
ov='Net-(U1301-INB-_{slash}_OV)';armed=c.by_id['b049d7c8-9984-50be-a63c-ab8f19b37c43'].GetNetname()
p['routes']=[r for r in p['routes'] if r['net'] not in [ov,armed]]
p['routes'][1]['points_mm']=[[31.6,7.0375],[31.6,6.16],[31.91,5.85]]
p['routes'][3]['points_mm']=[[32.1,13.15],[32.1,14.825],[32.025,14.9]]
p['routes'][-1]['points_mm']=[[34.85,12.5],[34.85,13.02]]
for u in list(p['delete_copper']):
    if c.by_id[u].GetNetname() in [ov,armed]:
        p['delete_copper'].remove(u);del p['deleted_copper_expected'][u]
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
