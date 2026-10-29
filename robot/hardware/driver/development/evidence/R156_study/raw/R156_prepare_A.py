"""Replay the R155 joint OV preparation with two corrected transfer locations.

No EN, ground or existing supply via is moved. The two disconnected MOTION_3V3
feeds remain mandatory restoration work; this model cannot be adopted alone.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
p=json.loads((b/'R155J-plan.json').read_text());p['revision']='R156A';p['scope']=__doc__
ov='Net-(U1301-INB-_{slash}_OV)'
for r in p['routes']:
 if r['net']!=ov:continue
 pts=r['points_mm']
 if r['layer']=='In3.Cu' and pts[0]==[40.75,26.8]:
  r['points_mm']=[[40.75,26.8],[40.75,26.15],[39.8,25.2],[39.8,24.5],[39.15,23.85],[38.8,23.85]]
 elif r['layer']=='B.Cu' and pts[0]==[38.8,23.95]:
  r['points_mm']=[[38.8,23.85],[38.4,23.45],[38.4,22.55],[38.7,22.25],[38.7,17.9],[39.2,17.4]]
 elif r['layer']=='In3.Cu' and pts[0]==[39.1,17.5]:
  r['points_mm']=[[39.2,17.4],[39.05,17.75]]+pts[3:]
for v in p['vias']:
 if v['position_mm']==[38.8,23.95]:v['position_mm']=[38.8,23.85]
 if v['position_mm']==[39.1,17.5]:v['position_mm']=[39.2,17.4]
f=b/'R156A-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R156A','source':p['board_sha256']}))
