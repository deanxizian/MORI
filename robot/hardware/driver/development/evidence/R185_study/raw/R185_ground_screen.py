"""Current-source candidate GND stitches for the six unresolved transition screens.

Project 2 mm proximity screening only; no EMC/impedance qualification. Protect
all source pads, copper, native via exclusions and both actual reference planes.
Rank power-antipad impact; native refill and every source width test still apply.
"""
import json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-ground-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
a=json.loads(Path('robot/hardware/driver/development/evidence/R181C/regression.json').read_text());assert a['board_sha256']==c.sha
flags=[r for r in a['reference_transitions'] if r['status']=='FAIL'];assert len(flags)==6
obstacles=[]
for (u,ly),s in c.shapes.items():
    o=c.by_id[u]
    if isinstance(o,pcb.PAD) or o.GetNetname()!='GND':obstacles.append(s.buffer(.455))
    elif isinstance(o,pcb.PCB_VIA):obstacles.append(Point(xy(o.GetPosition())).buffer(.705))
for k in c.keepouts:
    if k['vias']:obstacles.append(k['shape'].buffer(.255))
blocked=prep(unary_union(obstacles))
power=unary_union([g for net,ly,g in c.fills if net!='GND'])
ground=prep(c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.255).intersection(box(.755,.755,69.245,34.245)))
rows=[]
for f in flags:
    p=xy(c.by_id[f['uuid']].GetPosition());assert list(p)==f['position_mm']
    candidates=[]
    for ix in range(math.ceil((p[0]-1.95)*20),math.floor((p[0]+1.95)*20)+1):
        for iy in range(math.ceil((p[1]-1.95)*20),math.floor((p[1]+1.95)*20)+1):
            q=(ix/20,iy/20);dist=math.dist(p,q);pt=Point(q)
            if .705<=dist<=1.95 and not blocked.intersects(pt) and ground.contains(pt):
                candidates.append(dict(position_mm=list(q),signal_distance_mm=dist,power_antipad_projection_mm2=pt.buffer(.655).intersection(power).area))
    candidates.sort(key=lambda r:(r['power_antipad_projection_mm2'],r['signal_distance_mm']))
    rows.append(dict(signal_uuid=f['uuid'],net=f['net'],signal_position_mm=list(p),old_nearest_GND_mm=f['nearest_ground_mm'],candidate_count=len(candidates),candidates=candidates[:50]))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=.05,diameter_mm=.5,drill_mm=.3,flags=rows,adopted=False),indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='candidates'}|{'best':r['candidates'][:1]} for r in rows]),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
