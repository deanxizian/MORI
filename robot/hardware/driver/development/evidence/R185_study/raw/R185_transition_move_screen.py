"""Screen an explicit non-ground transfer move while retaining existing GND vias.

Only its three terminal segments are prospectively replaced. This screens new
reference voids and actual physical copper before constructing any moved via.
It does not prove the replacement routes or post-refill power widths.
"""
import json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-transition-move-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
v=c.by_id['2ceba827-433b-44de-af01-ce89cb121093'];net=v.GetNetname();old=xy(v.GetPosition())
retired={'0b73501d-5218-471d-b279-d5d0ec7a63a8','33e4355a-601b-4b18-a5d3-3898bad38203','c498f839-de08-4b3f-8baa-cfc725dc5d77'}
assert all(c.by_id[u].GetNetname()==net and not isinstance(c.by_id[u],pcb.PCB_VIA) for u in retired)
omit=retired|{uid(v)};obstacles=[]
for (u,ly),s in c.shapes.items():
    o=c.by_id[u]
    if u in omit:continue
    if isinstance(o,pcb.PAD) or o.GetNetname()!=net:obstacles.append(s.buffer(.457))
    elif isinstance(o,pcb.PCB_VIA):obstacles.append(Point(xy(o.GetPosition())).buffer(.607))
for k in c.keepouts:
    if k['vias']:obstacles.append(k['shape'].buffer(.257))
for p in c.pads:
    if max(xy(p.GetDrillSize()))>0:obstacles.append(Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557))
physical=prep(unary_union(obstacles))
referenced=[]
for t in c.segments:
    ly=c.board.GetLayerName(t.GetLayer())
    if uid(t) not in retired and ly in REFERENCE:
        referenced.append(c.shapes[uid(t),ly].intersection(c.copper['GND',REFERENCE[ly]]))
refguard=prep(unary_union(referenced).buffer(.657))
gnd=[o for o in c.anchors('GND') if all((uid(o),ly) in c.shapes and c.shapes[uid(o),ly].intersects(c.copper['GND',ly]) for ly in ['In1.Cu','In4.Cu'])]
power=unary_union([g for n,ly,g in c.fills if n!='GND'])
rows=[];counts=dict(physical=0,new_reference_loss=0,too_far_from_GND=0)
for ix in range(1150,1221):
    for iy in range(140,201):
        q=(ix/20,iy/20);pt=Point(q)
        if math.dist(q,old)<.001 or math.dist(q,old)>1.5:continue
        nearest=min(math.dist(q,xy(o.GetPosition())) for o in gnd)
        if nearest>1.95:counts['too_far_from_GND']+=1;continue
        if physical.intersects(pt):counts['physical']+=1;continue
        if refguard.intersects(pt):counts['new_reference_loss']+=1;continue
        rows.append(dict(position_mm=list(q),distance_from_original_mm=math.dist(q,old),nearest_dual_plane_GND_mm=nearest,
                         new_power_antipad_projection_mm2=pt.buffer(.657).intersection(power).area))
rows.sort(key=lambda r:(r['new_power_antipad_projection_mm2'],r['distance_from_original_mm']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,source_via=via_snapshot(c.board,v),prospectively_retired_tracks=sorted(retired),
                              candidates=rows,rejections=counts,grid_mm=.05,adopted=False),indent=2)+'\n')
print(json.dumps(dict(candidates=len(rows),rejections=counts,best=rows[:10])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
