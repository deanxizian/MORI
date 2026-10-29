import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,"robot/hardware/driver/development/scripts")
from plan_layered_route import Planner
p=Planner(sys.argv[1],.025,["F.Cu"],.2)
net="Net-(U1702-INA+)"
gs=p.routing_groups(net)
g=p.geometry(net)
g=(g[0],np.zeros(g[1].shape,dtype=bool),g[2],g[3])
a=next(r for r in gs if "R1703.2" in r["pads"])
b=next(r for r in gs if "U1702.3" in r["pads"])
r=p.solve(a,b,g,800000)
Path(sys.argv[2]).write_text(json.dumps({"scope":"Bounded front-only proposal, not native acceptance", "board_sha256":p.c.sha,"result":r},indent=2)+"\n")
print(json.dumps(r))
