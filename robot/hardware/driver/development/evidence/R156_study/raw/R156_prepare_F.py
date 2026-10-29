"""Refine the R156E group candidate without moving ground or supply vias.

Place R1703 at (49.05,9.95), restoring its output by a straight vertical trace
and keeping the original long INA+ trunk exactly unchanged. Route the wheel
sense tap around the right of the fixed GND hole and above the lower 3V3 hole
instead of through the narrow reference gap between the two original holes.
The unchanged internal supply fill must again preserve all source power gates.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R156E-plan.json').read_text());p['revision']='R156F';p['scope']=__doc__
p['translations'][1]['delta_mm']=[.55,-.45]
keep='46b45438-08f9-40a3-97c0-eeccfd4d2b5b';p['delete_copper'].remove(keep);del p['deleted_copper_expected'][keep]
p['routes']=[
 {'net':'Net-(R1702-~-Pad2)','layer':'F.Cu','width_mm':.2,'points_mm':[[48.825,8.5],[48.825,8.8],[48.225,9.4],[48.225,9.95]]},
 {'net':'Net-(U1702-INA+)','layer':'F.Cu','width_mm':.2,'points_mm':[[49.875,9.95],[49.875,12.45]]},
 {'net':'/WHEEL_VM','layer':'F.Cu','width_mm':.2,'points_mm':[[47.175,8.5],[47.175,8.8],[47.4,9.025],[47.4,10.9],[48.15,11.65],[48.15,12.55],[46.355,14.345],[46.355,15.5]]}]
f=b/'R156F-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print('R156F plan')
