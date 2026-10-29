"""Compare original INA300 pose/supply transfers with the revised local passives.

Restore the source U1701 body rules and both source 3V3 vias/leads, move R1707
left 0.25 mm to open the mounted-face LIMIT corridor, then re-route inputs.
This is a native candidate, not an adopted layout or a completed circuit.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R176C-plan.json').read_text())
p['revision']='R176D';p['scope']=__doc__
p['translations']=[x for x in p['translations'] if x['reference']!='U1701']
for x in p['translations']:
 if x['reference']=='R1707':x['delta_mm'][0]=-.25
p['move_vias']=[];p['remove_obsolete_vias']=[]
restored=['35011640-47d5-43d9-aa07-7c7e24d3d8e5','bc3e9793-b9cd-54b1-b44c-64b91f6e9a06','94097be9-7a4a-5f2f-a1eb-c11cabb5d174','afcf9e26-68ae-4e49-b6cc-970f0435d8fe','4e3cff17-d7fe-4cb4-87f2-0dfef758262e','3c59ab5a-ed77-4497-bfe1-918eab519360']
for u in restored:
 p['delete_copper'].remove(u);del p['deleted_copper_expected'][u]
p['routes']=[r for r in p['routes'] if r['net']=='MOTION_3V3' and r['layer']=='B.Cu']
out=b/'R176D-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(dict(revision=p['revision'],restored_source_tracks=restored,retired_tracks=len(p['delete_copper'])))
