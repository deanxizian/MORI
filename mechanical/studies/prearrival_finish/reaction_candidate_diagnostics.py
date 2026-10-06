"""Inspect failed candidate intersections before changing any proposal."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
helper = (HERE/'reaction_access_candidate.py').read_text().split("names = ['Yaw_Reaction_Link'")[0]
exec(compile(helper, str(HERE/'reaction_access_candidate.py'), 'exec'), globals())
m = construct(cx=7.6, dz=1., rear_flat=9., join_split=True)
rows=[]
for z in (0., 2., 5., 10., 13.):
    part=m.translate((0,0,z)) ^ ss['Pitch_Yoke'].m
    rows.append(dict(z_mm=z, volume_mm3=part.volume(),
                     bounds_mm=list(part.bounding_box()) if part.volume() > .000001 else None))
nut=ss['Yaw_Reaction_Clamp_Nut'].m.translate((.6,0,1))
v=nut ^ m
out=dict(source_blend_sha256=source_hash, main_applied=False,
         path_hits=rows, nut_overlap=dict(volume_mm3=v.volume(), bounds_mm=list(v.bounding_box())),
         old_nut_overlap_mm3=(ss['Yaw_Reaction_Clamp_Nut'].m ^ original).volume(),
         nut_bounds=list(nut.bounding_box()),
         horn_bounds=list(ss['Yaw_Horn'].m.bounding_box()),
         yoke_vertices_near_entry=[r.tolist() for r in ss['Pitch_Yoke'].v
                                  if -6<r[0]<6 and -15<r[1]<0 and 196<r[2]<203],
         straight_trim_limit=dict(rear_seat_front_y_mm=-6.149999618530273,
             assumed_assembly_gap_mm=.3, required_flat_y_at_least_mm=-5.849999618530273,
             existing_horn_seat_radius_mm=5.2, remaining_centerline_lower_back_wall_mm=.649999618530273,
             existing_upper_relief_radius_mm=6.4,
             effect='Deeper straight trim opens the existing upper relief; cannot treat it as cosmetic cleanup',
             qualification='Geometric deduction for current provisional horn allocation, not strength evidence'))
(OUT/'diagnostics.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='yoke_vertices_near_entry'},indent=2),flush=True)
