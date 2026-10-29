"""Bounded multilayer input route proposal on the unchanged R159B diagnostic probe."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R159-input-search/multilayer-result.json';assert not out.exists()
p=Planner(str(b/'R159-input-search/MORI_Interface_C3.kicad_pcb'),.05,['F.Cu','B.Cu','In3.Cu'],.2)
net='Net-(U1702-INA+)';gs=p.routing_groups(net);g=p.geometry(net)
a=next(r for r in gs if 'R1703.2' in r['pads']);z=next(r for r in gs if 'U1702.3' in r['pads'])
r=p.solve(a,z,g,750000);out.write_text(json.dumps({'scope':__doc__,'board_sha256':p.c.sha,'result':r},indent=2)+'\n');print(json.dumps(r))
