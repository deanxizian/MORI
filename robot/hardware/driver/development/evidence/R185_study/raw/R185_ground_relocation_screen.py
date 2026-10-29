"""Independent GND-via relocation screen; original native rules remain intact.

The source via terminates C601's two-segment return. Both segments are explicitly
replaced with an equal-width, shorter 45-degree return. All other source objects
remain obstacles. Counts and UUIDs are preserved; refill audit is mandatory.
"""
import json, math, sys
from pathlib import Path
from shapely.prepared import prep
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
out=b/'R185-ground-relocation-screen.json'; assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
v=c.by_id['2e7f36fc-97b4-4bdc-ac9d-b6a6321965ed']; old=xy(v.GetPosition())
retired={'1e6e4d91-7a6d-45e9-b841-a86fe7e91a87','9c5adea9-2cc4-48c2-b27e-6f1e509908f4'}
signal=c.by_id['2ceba827-433b-44de-af01-ce89cb121093']; sp=xy(signal.GetPosition())
pad=next(p for p in c.pads if c.pad_name(p)=='C601.2'); pp=xy(pad.GetPosition())
obstacles=[]; route_obstacles=[]
for (u,ly),s in c.shapes.items():
    o=c.by_id[u]
    if u in retired|{uid(v)}: continue
    if isinstance(o,pcb.PAD) or o.GetNetname()!='GND': obstacles.append(s.buffer(.455))
    elif isinstance(o,pcb.PCB_VIA): obstacles.append(Point(xy(o.GetPosition())).buffer(.705))
    if ly=='B.Cu' and o.GetNetname()!='GND': route_obstacles.append(s.buffer(.305))
for k in c.keepouts:
    if k['vias']: obstacles.append(k['shape'].buffer(.255))
    if k['tracks'] and 'B.Cu' in k['layers']: route_obstacles.append(k['shape'].buffer(.105))
for p in c.pads:
    if max(xy(p.GetDrillSize()))>0: obstacles.append(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.555))
blocked=prep(unary_union(obstacles)); route_blocked=prep(unary_union(route_obstacles))
ground=prep(c.copper['GND','In1.Cu'].intersection(c.copper['GND','In4.Cu']).buffer(-.255))
power=unary_union([g for n,ly,g in c.fills if n!='GND'])
oldvoid=Point(old).buffer(.655)
a=json.loads(Path('robot/hardware/driver/development/evidence/R181C/regression.json').read_text())
served=[r for r in a['reference_transitions'] if r.get('nearest_ground_uuid')==uid(v)]
rows=[]
for ix in range(1140,1181):
    for iy in range(140,191):
        q=(ix/20,iy/20);pt=Point(q);d=math.dist(q,sp)
        if not .705<=d<=1.95 or math.dist(q,old)>1.5 or blocked.intersects(pt) or not ground.contains(pt): continue
        bend=(pp[0],q[1]+abs(q[0]-pp[0]));pts=[pp,bend,q]
        line=LineString(pts)
        if bend[1]>pp[1] or line.length>1.225+math.sqrt(.35**2*2)+1e-6 or route_blocked.intersects(line):continue
        rows.append(dict(position_mm=q,signal_distance_mm=d,C601_return_points_mm=pts,C601_return_length_mm=line.length,
                         power_projection_added_mm2=pt.buffer(.655).difference(oldvoid).intersection(power).area))
rows.sort(key=lambda r:(r['power_projection_added_mm2'],r['C601_return_length_mm']))
result=dict(scope=__doc__,source_sha256=c.sha,via_uuid=uid(v),source_via=via_snapshot(c.board,v),retired_tracks=sorted(retired),
            old_C601_return_length_mm=1.225+math.sqrt(.35**2*2),served_transitions=served,candidates=rows,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(count=len(rows),served=served,best=rows[:12])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
