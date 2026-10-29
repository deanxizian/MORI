"""Complete an independent FAULT trunk proposal with the corrected INA escape.

The F geometry opens a 20.582 mm In2 routing proposal without new vias while
reserving the original 0.48 mm 3V3 source corridor. G uses exact original via
centers at both ends and the screened outward INA+ pad approach. Foreign
power fill is still crossed and full native copper regression is mandatory.
This plan does not adopt the layout or imply manufacturing readiness.
"""
import json
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R168G-plan.json';assert not out.exists()
p=json.loads((b/'R168F-plan.json').read_text())
screen=json.loads((b/'R168-ina-preflight.json').read_text());r=next(r for r in screen['rows'] if r['x']==59.5 and r['y']==16.1);assert not r['hits']
p['routes'][5]['points_mm']=r['points_mm']
q=json.loads((b/'R168F-fault-reserved-search/fault_main-plan.json').read_text());assert len(q['routes'])==1 and not q['vias'] and not q['activate_pth_layers']
route=q['routes'][0];assert route['layer']=='In2.Cu' and route['net']=='/FAULT_N'
route['points_mm']=[[56.175,14.9],[56.275,15]]+route['points_mm'][1:-1]+[[67.45,28.25],[67.45,28.35]]
p['routes'].append(route)
p.update(revision='R168G',scope=__doc__,INA_preflight='R168-ina-preflight.json',FAULT_proposal='R168F-fault-reserved-search/fault_main-plan.json',adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
