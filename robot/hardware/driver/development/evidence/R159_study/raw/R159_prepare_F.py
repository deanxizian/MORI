"""Keep the original S2 drill position and change only its local trace approach.
Separate the new UPS via from the nearby 3V3 reference void, with the relocated
C505 supply lead routed above it. Keep all former native power settings.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R159E-plan.json').read_text());p['revision']='R159F';p['scope']=__doc__
p['move_vias']=[v for v in p['move_vias'] if v['uuid']!='3da8b3e2-7d4b-4ebe-87e6-877930d5d3f3']
p['vias'][0]['position_mm']=[51.35,6.2]
p['routes']=[r for r in p['routes'] if r['net']!='Net-(U1001-S2_{slash}_WHEEL_sense)' and not (r['net']=='MOTION_3V3' and r['layer']=='B.Cu') and not (r['net']=='/UPS_BAT' and r['layer']=='B.Cu')]
def route(n,l,w,pts):p['routes'].append({'net':n,'layer':l,'width_mm':w,'points_mm':pts})
route('/UPS_BAT','B.Cu',.35,[[46.25,8.3],[46.25,8.55],[50.85,8.55],[51.35,8.05],[51.35,6.2]])
route('MOTION_3V3','B.Cu',.2,[[49.775,5.9],[50.1,5.9],[50.1,5.3],[52.25,5.3],[52.25,5.9]])
route('Net-(U1001-S2_{slash}_WHEEL_sense)','F.Cu',.2,[[44.6,7.5],[44.6,9.2],[45.45,9.2],[45.6,9.35]])
route('Net-(U1001-S2_{slash}_WHEEL_sense)','In3.Cu',.2,[[36.85,9.35],[44.15,9.35],[44.3,9.2],[45.45,9.2],[45.6,9.35]])
f=b/'R159F-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R159F plan written')
