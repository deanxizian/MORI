"""Select a local power escape using actual filled reference and TVS projection.

The I/J reference-plane fills are verified equal. A 2 um stroke margin is used
only for planning; final native DRC/refill checks retain their original limits.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R185-supply-exit-screen.json';assert not out.exists()
c=Copper(str(b/'R185I/MORI_Interface_C3.kicad_pcb'));j=Copper(str(b/'R185J/MORI_Interface_C3.kicad_pcb'));net='MOTION_3V3'
assert all(c.copper['GND',ly].symmetric_difference(j.copper['GND',ly]).area<1e-8 for ly in ['In1.Cu','In4.Cu'])
ground=c.copper['GND','In1.Cu'];tvs=c.copper['/UPS_BAT','F.Cu']
lands=unary_union([s for o in c.anchors(net) for s in [reference_transfer_shape(c,o,'In1.Cu')] if s is not None])
allowed=ground.union(lands.buffer(.405))
obstacles=unary_union([s.buffer(.202) for (u,l),s in c.shapes.items() if l=='In2.Cu' and c.by_id[u].GetNetname()!=net])
rows=[]
for i in range(0,31):
    x=58.925+i*.005;dy=x-58.9
    pts=[[58.9,8.6],[round(x,6),round(8.6+dy,6)],[round(x,6),9.5],[round(x-.2,6),9.7],[57.65,9.7],[57.2,9.25],[57.2,8.05]]
    stroke=LineString(pts).buffer(.252)
    rows.append(dict(x=x,points_mm=pts,reference_missing_mm2=stroke.difference(allowed).area,
                     unshielded_TVS_projection_mm2=stroke.intersection(tvs).difference(ground).area,
                     physical_collision_mm2=stroke.intersection(obstacles).area,length_mm=LineString(pts).length))
safe=[r for r in rows if r['reference_missing_mm2']<1e-8 and r['unshielded_TVS_projection_mm2']<1e-8 and r['physical_collision_mm2']<1e-8]
out.write_text(json.dumps(dict(scope=__doc__,reference_source_sha256=c.sha,comparison_source_sha256=j.sha,rows=rows,safe=safe,adopted=False),indent=2)+'\n')
print(json.dumps(dict(safe_count=len(safe),safe=safe),indent=2))
