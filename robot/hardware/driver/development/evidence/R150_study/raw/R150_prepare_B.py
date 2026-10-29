"""Correct the exact hierarchical ARMED net name in the independent preparation."""
import json, sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
out=b/'R150B-plan.json'; assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R150A-plan.json').read_text()); p.update(revision='R150B',scope=__doc__)
for r,u in zip(p['routes'][-2:],['01c0c62f-2e70-5cdb-b96b-7826f4ff753a','e0b746d4-193b-52fd-b359-e8159756c433']):
    r['net']=c.by_id[u].GetNetname()
out.write_text(json.dumps(p,indent=2)+'\n'); print(out)
