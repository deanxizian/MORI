"""Keep the right 3V3 source transfer and jointly reposition U1702/ACT.

D moved the 3V3 reference void under its old B feed and trapped INA+ between
signal transfer holes. E restores the original right power transfer and feed,
moves U1702 left 0.25 mm from D, and moves the right ACT transfer to
(59.45,14.6). Its complete INA+, ACT, VDD and GND leads are replaced.
This is an unadopted candidate, pending full native/electrical/reference audit.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168E-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R168D-plan.json').read_text());assert p['board_sha256']==c.sha
next(t for t in p['translations'] if t['reference']=='U1702')['delta_mm']=[.25,-.5]
p['move_vias']=[m for m in p['move_vias'] if m['uuid']!='e81f1421-0f0e-4b1c-9a73-ed7af0f79a65']
next(m for m in p['move_vias'] if m['uuid']=='4312a4e0-e664-44e0-a44a-716dd81b836a')['position_mm']=[59.45,14.6]
for u in ['3c035269-ca47-599c-9993-22dfabca192e','d31e2045-4d15-49d7-a9ac-9567a50cdd95']:
 p['delete_copper'].remove(u);del p['deleted_copper_expected'][u]
assert p['routes'][-1]['net']=='MOTION_3V3';p['routes'].pop()
p['routes'][1]['points_mm']=[[56.8,16.3875],[55.825,15.4]]
p['routes'][3]['points_mm']=[[58.775,14.775],[59.275,14.775],[59.45,14.6]]
p['routes'][5]['points_mm']=[[59.9,12.575],[59.9,13.925],[60.25,14.275],[60.25,14.8375],[58.7,16.3875]]
p['routes'][6]['points_mm']=[[57.75,14.1125],[57.75,13.25],[57.6,13.1],[56.3,13.1],[55.6,13.8],[55.4,13.8]]
p['routes'][7]['points_mm']=[[59.625,13.6],[60.725,13.525]]
p['routes'][8]['points_mm']=[[57.75,16.3875],[57.75,17.925],[57.475,18.2]]
p['routes'][10]['points_mm']=[[59.45,14.6],[60.6,14.6],[61.5,15.5]]
p.update(revision='R168E',scope=__doc__,adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
