"""Read-only diagnosis of the baseline reaction-link fastener interfaces."""
from pathlib import Path
import json, sys, time
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT / 'mechanical/scripts'))
from harness_context import Context, np, sha
from common import manifold, P

ctx = Context()
started = time.time()
names = ['Yaw_Reaction_Link', 'Yaw_Base', 'Pitch_Yoke', 'Yaw_Horn',
         'Yaw_Reaction_Clamp_Screw', 'Yaw_Reaction_Clamp_Nut',
         'Yaw_Reaction_Retainer_Screw', 'Yaw_Reaction_Retainer_Nut']
rows = {}
for n in names:
    s = ctx.ss[n]
    rows[n] = dict(bounds_mm=list(s.m.bounding_box()),
                   properties={k:s.o[k] for k in s.o.keys()
                               if k in ['classification', 'evidence', 'model_fidelity',
                                        'unknown_dimensions', 'interface_status', 'label_zh']})

contacts = []
for nut_name, host_name in [('Yaw_Reaction_Retainer_Nut', 'Yaw_Base'),
                            ('Yaw_Reaction_Clamp_Nut', 'Yaw_Reaction_Link')]:
    s = ctx.ss[nut_name]
    c = (s.lo + s.hi)/2
    host = ctx.ss[host_name].m
    for angle in [0, 30, -30]:
        m = s.m.translate((-c).tolist()).rotate([0, angle, 0]).translate(c.tolist())
        overlap = m ^ host
        v = float(overlap.volume())
        contacts.append(dict(nut=nut_name, host=host_name, rotation_about_Y_deg=angle,
                             overlap_mm3=v,
                             overlap_bounds_mm=list(overlap.bounding_box()) if abs(v)>1e-8 else None))
        if angle == 0:
            for tag, shape in [('nut',m), ('host',host), ('overlap',overlap)]:
                mesh=shape.to_mesh64()
                np.savez_compressed(OUT/(nut_name+'_'+tag+'.npz'),
                                    vertices_mm=mesh.vert_properties[:,:3],triangles=mesh.tri_verts)
ctx.assert_unchanged()
report=dict(revision=P['revision'], sources=ctx.sources, parts=rows, contacts=contacts,
            native_fingerprints=ctx.print_fingerprints,
            main_changed=False, scope='Current native nut seating and isolated orientation diagnosis only',
            script_sha256=sha(Path(__file__)), elapsed_s=time.time()-started)
(OUT/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('REACTION_CURRENT_INSPECTION',json.dumps(contacts),flush=True)
