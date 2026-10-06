# -*- coding: utf-8 -*-
"""Independent deck-slot feasibility screen. Does not edit any saved model."""
from pathlib import Path
import json, hashlib
STAGE = Path(__file__).resolve().parent
code = (STAGE/'check_static.py').read_text().split('specs=[')[0]
exec(compile(code, str(STAGE/'check_static.py'), 'exec'), globals())

outdir = STAGE/'deck_slot_review'
outdir.mkdir(exist_ok=True)
frame = ss['Load_Frame'].m
z = P['layout']['deck_z_mm']
th = P['layout']['deck_thickness_mm']

def slot(x, y, w, length, h):
    middle = manifold.Manifold.cube([w,length-w,h],center=True).translate([x,y,z])
    ends = [axial(w/2,h,[x,y+d*(length-w)/2,z],[0,0,1]) for d in [-1,1]]
    return middle+ends[0]+ends[1]

rows = []
for sign in [-1,1]:
    x,y,w,length = sign*42.,-43.,8.,22.
    cut = slot(x,y,w,length,th+.02)
    removed = frame^cut
    candidate = frame-cut
    outside = cut-frame
    # Compare the full closed slot against the declared straight outer deck
    # outline independently, including the broad folded rear corners.
    profile = np.array(P['layout_cleanup']['frame_outline_xy_mm'])
    edge = []
    for a,b in zip(profile,np.roll(profile,-1,axis=0)):
        v=b-a
        # Closest distance from each analytic end-circle to a boundary edge.
        ds=[]
        for cy in [y-(length-w)/2,y+(length-w)/2]:
            c=np.array([x,cy]);t=np.clip((c-a)@v/(v@v),0,1)
            ds.append(float(np.linalg.norm(c-a-v*t))-w/2)
        edge.append(min(ds))
    neighbors=[]
    for n,s in obstacles.items():
        if n=='Load_Frame':continue
        # Local candidate prism extended above/below the deck for seat context.
        roi=slot(x,y,w+8,length+8,22)
        if (roi^s.m).volume()>.0001:
            neighbors.append(dict(name=n,bounds_mm=list(s.m.bounding_box()),
                cut_overlap_mm3=max(0,(cut^s.m).volume())))
    row=dict(name='left' if sign<0 else 'right',center_xy_mm=[x,y],
        width_mm=w,length_mm=length,radius_mm=w/2,
        deck_bottom_top_z_mm=[z-th/2,z+th/2],
        removed_mm3=removed.volume(),removed_bounds_mm=list(removed.bounding_box()),
        frame_components_before=len(frame.decompose()),frame_components_after=len(candidate.decompose()),
        minimum_declared_outer_edge_land_mm=min(edge),neighbors=neighbors)
    rows.append(row)
    print('DECK_SLOT_INSPECT',json.dumps(row),flush=True)
result=dict(source_blend_sha256=source_hash,status='NOT_TESTED',
    scope='Local closed slot feasibility only; routes, plug feeding, strength and complete service are not qualified',
    candidates=rows,ports={k:dict(bounds_mm=list(plug[k].m.bounding_box())) for k in ['motion_J4','imu_J1']},
    main_geometry_changed=False,adopted=False)
(outdir/'inspection.json').write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
