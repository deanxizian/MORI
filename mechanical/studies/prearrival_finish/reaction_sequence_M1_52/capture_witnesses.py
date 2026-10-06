"""Extract actual local collision sections; leave the native assembly untouched."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import P
ctx=Context();prior=json.loads((OUT/'initial.json').read_text())
assert ctx.source_hash==prior['source_blend_sha256']
rows=[]
for direction in [1,-1]:
    first=next(r for r in prior['vertical_paths'] if r['case']=='bare_link' and r['axis'][2]==direction)['first_collision']
    distance=first['travel_mm']
    link=ctx.ss['Yaw_Reaction_Link'].m.translate([0,0,direction*distance]);host=ctx.ss['Pitch_Yoke'].m
    overlap=link^host;pieces=overlap.decompose();largest=max(pieces,key=lambda m:abs(m.volume()))
    bounds=np.asarray(largest.bounding_box());center=(bounds[:3]+bounds[3:])/2
    plane_x=float(center[0]);tr=[[0,1,0,0],[0,0,1,0],[1,0,0,-plane_x]]
    sections={n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in [('link',link),('host',host),('overlap',overlap)]}
    rows.append(dict(direction_z=direction,travel_mm=distance,overlap_mm3=float(overlap.volume()),plane_x_mm=plane_x,
                     focus_yz_mm=center[[1,2]].tolist(),largest_overlap_bounds_mm=bounds.tolist(),sections=sections))
ctx.assert_unchanged()
(OUT/'witness_sections.json').write_text(json.dumps(dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,
    input_sha256=sha(OUT/'initial.json'),script_sha256=sha(Path(__file__)),rows=rows),ensure_ascii=False,indent=2)+'\n')
print('COLLISION_SECTIONS_SAVED',flush=True)
