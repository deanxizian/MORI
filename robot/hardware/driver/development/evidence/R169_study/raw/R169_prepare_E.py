"""Combine D's fault escape, a proposed In2 trunk and restored R1310 leads.

Align all terminals to actual native pad/via centres and the retained FAULT
segment at (64.05,18.7). The original INA300 inputs/LIMIT/GND remain unfinished;
this native comparison cannot be adopted even if the new FAULT link connects.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R169E-plan.json';assert not out.exists();p=json.loads((b/'R169D-plan.json').read_text());s=b/'R169D-power-aware-search'
f=json.loads((s/'fault_ina-plan.json').read_text());r=f['routes'][0];r['points_mm'][:2]=[[49.45,14],[49.6,14]];r['points_mm'][-1]=[64.05,18.7];p['routes'].append(r)
p['routes'].append(dict(net='Net-(U1302-CT)',layer='F.Cu',width_mm=.2,points_mm=[[50.425,14.25],[50.425,13.9],[50.95,13.375]]))
p['routes'].append(dict(net='MOTION_3V3',layer='F.Cu',width_mm=.2,points_mm=[[52.075,14.25],[52.075,14.675],[52.15,14.75],[51.85,15.05],[48.85,15.05],[47.9,14.1],[47.775,14.1]]))
p.update(revision='R169E',scope=__doc__,adoption_prohibited=True);out.write_text(json.dumps(p,indent=2)+'\n')
