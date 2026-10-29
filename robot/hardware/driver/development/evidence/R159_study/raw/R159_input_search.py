"""Front-only TPS3700 input route search after moving the series resistor pair.
Actual source fills/reference, all native keepouts, pads and holes are retained.
Only the failed R159B input trunk is removed in a new diagnostic copy.
"""
import json,sys,subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R159-input-search';out.mkdir(exist_ok=False)
c=Copper(b/'R159B/MORI_Interface_C3.kicad_pcb');removed=[]
for t in c.segments:
 if t.GetNetname()=='Net-(U1702-INA+)' and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])<58:
  removed.append(uid(t));c.board.Remove(t)
for ext in ['.kicad_pro','.kicad_dru']:(out/('MORI_Interface_C3'+ext)).write_bytes((b/'R159B'/('MORI_Interface_C3'+ext)).read_bytes())
probe=out/'MORI_Interface_C3.kicad_pcb';pcb.SaveBoard(str(probe),c.board)
(out/'probe.json').write_text(json.dumps({'source':c.sha,'removed_tracks':removed,'not_a_candidate':True},indent=2)+'\n')
# Read in a separate process because of the documented SWIG same-process reload error.
worker=out/'worker.py';worker.write_text('''import sys,json\nfrom pathlib import Path\nimport numpy as np\nsys.path.insert(0,"robot/hardware/driver/development/scripts")\nfrom plan_layered_route import Planner\np=Planner(sys.argv[1],.025,["F.Cu"],.2)\nnet="Net-(U1702-INA+)"\ngs=p.routing_groups(net)\ng=p.geometry(net)\ng=(g[0],np.zeros(g[1].shape,dtype=bool),g[2],g[3])\na=next(r for r in gs if "R1703.2" in r["pads"])\nb=next(r for r in gs if "U1702.3" in r["pads"])\nr=p.solve(a,b,g,800000)\nPath(sys.argv[2]).write_text(json.dumps({"scope":"Bounded front-only proposal, not native acceptance", "board_sha256":p.c.sha,"result":r},indent=2)+"\\n")\nprint(json.dumps(r))\n''')
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
r=subprocess.run([py,str(worker),str(probe),str(out/'result.json')],capture_output=True,text=True)
(out/'worker-log.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2)+'\n')
print(r.stdout);print('worker_returncode',r.returncode)
