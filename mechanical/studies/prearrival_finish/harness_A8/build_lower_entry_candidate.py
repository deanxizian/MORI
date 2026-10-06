"""Independent lower-entry C1, not adopted and not a completed harness.

Use four real wire centerlines to locate a candidate cut in Yaw_Base only.
Record contact/strength limitations before asking for any structural approval.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT)
open_floor='--open-floor' in sys.argv
OUT=SCRIPT.parent/('lower_entry_open_candidate' if open_floor else 'lower_entry_candidate');OUT.mkdir(exist_ok=True)
from interface_completion import replace_owned
from validate_head_cleanup import geometry_record

assert len(ss)==209 and before=='bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
baseline_records={name:geometry_record(s.o) for name,s in ss.items()}
entry_path=SCRIPT.parent/'body_entry_bends.json';entries=json.loads(entry_path.read_text())
assert entries['source_blend_sha256']==before
selected=[r for r in entries['curves'] if r['radius_mm']==8 and r['azimuth_deg'] in [45,135,225,315]]
assert len(selected)==4
assert all({h['object'] for h in r['current_source_obstacles']}=={'Yaw_Base'} and not r['fixed_wire_hit'] for r in selected)

cut_radius=.93
cutters=[]
for row in selected:
    pts=np.asarray(row['curve_mm'])
    # Short arc chords plus spherical joins form a through-open channel.
    # A 0.3mm margin beyond the wire+clearance test covers this chordal cut.
    pts=np.vstack([pts[:201:5],pts[-1]])
    pieces=[manifold.Manifold.sphere(cut_radius,32).translate(p.tolist()) for p in pts]
    for a,b in zip(pts,pts[1:]):
        d=b-a;ln=float(np.linalg.norm(d))
        pieces.append(axial(cut_radius,ln,(a+b)/2,d/ln,segments=64))
    cutters.append(manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add))
cut=manifold.Manifold.batch_boolean(cutters,manifold.OpType.Add)
if open_floor:
    # Continue all four slots through the complete3mm roof to its existing
    # central bore. This removes the thin residual webs left by C1's curved cut.
    mouth=[]
    for angle in [45,135,225,315]:
        mouth.append(manifold.Manifold.cube((7.,1.86,3.4),center=True)
            .translate((8.,0.,145.5)).rotate((0.,0.,float(angle))))
    cut=cut+manifold.Manifold.batch_boolean(mouth,manifold.OpType.Add)
old=ss['Yaw_Base'].m
new=old-cut
assert new.status()==manifold.Error.NoError
removed=old-new
component_volumes=[float(m.volume()) for m in new.decompose()]
parts_to_preserve=['Yaw_Bearing','Yaw_Anti_Lift_Keeper','Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1',
                  'Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut',
                  'Yaw_Reaction_Link']
nearby=[dict(part=name,removed_to_reference_gap_mm=float(removed.min_gap(ss[name].m,10))) for name in parts_to_preserve]

# Include the lower approaches and rotate all four central wires by45deg.
# Endpoints, length law and wire spacing remain coherent through their join.
central_path=SCRIPT.parent/'central_uart_curves.json';central=json.loads(central_path.read_text())
source_hits=[];fixed_hits=[]
replace_owned('Yaw_Base',new)
new_source=Solid(ss['Yaw_Base'].o)
ss['Yaw_Base']=new_source;trees['Yaw_Base']=new_source.bvh()
for row in selected:
    pts=np.asarray(row['curve_mm'])
    h=sample_clear(pts,.3302,row['arc_chord_error_bound_mm'],['Yaw_Base'])
    if h:source_hits.append(dict(segment='lower',azimuth_deg=row['azimuth_deg'],**h))
for pose in central['selected']['poses']:
    yaw=pose['yaw_deg'];base=np.asarray(pose['first_wire_curve_mm'])
    for angle in [45,135,225,315]:
        p=math.radians(angle)
        rotation=np.array([[math.cos(p),-math.sin(p),0],[math.sin(p),math.cos(p),0],[0,0,1]])
        points=base@rotation.T
        fh=fixed_clear(points,.3302,pose['second_derivative_chord_error_bound_mm'])
        if fh:fixed_hits.append(dict(yaw_deg=yaw,azimuth_deg=angle,**fh))
        for pitch in range(-20,26,5):
            for name,s in ss.items():
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=points@inv[:3,:3].T+inv[:3,3]
                else:local=points
                h=sample_clear(local,.3302,pose['second_derivative_chord_error_bound_mm'],[name])
                if h:source_hits.append(dict(segment='central',yaw_deg=yaw,pitch_deg=pitch,azimuth_deg=angle,**h))

now_records={name:geometry_record(s.o) for name,s in ss.items()}
changed=sorted(name for name in baseline_records if baseline_records[name]!=now_records[name])
assert changed==['Yaw_Base'],changed
print('LOWER_C1',float(removed.volume()),component_volumes,len(source_hits),len(fixed_hits),flush=True)

# Save precise shapes for section inspection and an explicitly labelled copy.
for name,solid in [('Yaw_Base_baseline',old),('Yaw_Base_candidate',new),('removed',removed)]:
    m=solid.to_mesh64()
    np.savez_compressed(OUT/(name+'.npz'),vertices_mm=np.asarray(m.vert_properties[:,:3]),triangles=np.asarray(m.tri_verts))
sections={}
for z in [143.5,144.,145.,146.,147.]:
    sections[f'z={z}']={'kind':'XY','z_mm':z,
        'layers':{name:[p.tolist() for p in solid.slice(z).to_polygons()] for name,solid in
            [('before',old),('after',new),('removed',removed)]}}
angle=math.radians(45)
tr=np.array([[0,0,1,0],[math.cos(angle),math.sin(angle),0,0],[-math.sin(angle),math.cos(angle),0,0]])
sections['radial45']={'kind':'Z_radial','azimuth_deg':45,
    'layers':{name:[p.tolist() for p in solid.transform(tr).slice(0).to_polygons()] for name,solid in
        [('before',old),('after',new),('removed',removed),('reaction',ss['Yaw_Reaction_Link'].m),('bearing',ss['Yaw_Bearing'].m)]}}
(OUT/'sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')
bpy.context.scene['independent_unapproved_study']='A8 lower entry C1 only; upper route, retention and loads unresolved'
bpy.context.scene['main_model_not_updated']=True
ss['Yaw_Base'].o['candidate_only']='A8 lower-entry C1; NOT APPROVED; print strength and full harness NOT_TESTED'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
report=dict(status='PASS' if not source_hits and not fixed_hits and len(component_volumes)==1 else 'FAIL',
    status_scope='Lower approach plus rotated central segment geometry only; not a release or adoption recommendation',
    source_blend_sha256=before,source_entry_curve_sha256=hashlib.sha256(entry_path.read_bytes()).hexdigest(),
    source_central_curve_sha256=hashlib.sha256(central_path.read_bytes()).hexdigest(),
    changed_existing_ids=changed,unchanged_physical_ids=sorted(set(ss)-set(changed)),
    wire_azimuths_deg=[45,135,225,315],entry_bend_radius_mm=8,channel_cut_radius_mm=cut_radius,
    opened_to_central_bore_through_roof=open_floor,
    mouth_candidate_dimensions_mm=({'radial_limits':[4.5,11.5],'width':1.86,'z_limits':[143.8,147.2]} if open_floor else None),
    nominal_wire_surface_to_channel_gap_mm=cut_radius-.3302,
    removed_volume_mm3=float(removed.volume()),remaining_components_mm3=component_volumes,
    closest_source_parts=nearby,central_wire_pose_instances=520,source_hits=source_hits,fixed_wire_hits=fixed_hits,
    proposed_lower_curves=selected,head_motion_poses=130,
    blade_thin_edges='NOT_TESTED',load_contact_preservation='NOT_TESTED',physical_strength='NOT_TESTED',
    main_model_applied=False,complete_harness='BLOCKED',supplier_drawing='BLOCKED',
    candidate_blend_sha256=hashlib.sha256((OUT/'candidate.blend').read_bytes()).hexdigest(),
    limits=['Only Yaw_Base was cut in an independent copy; all original hardware and other208 physical meshes stay unchanged.',
            'Original zero degree local paths remain historical; this candidate uses45deg-rotated four-wire paths.',
            'No anchor or supplier length is defined by these staging curves.',
            'Candidate cuts must still be reviewed for thin remnants and loss of bearing/stem support.',
            'Upper ends, pitch route, all other branches and full installed assembly remain incomplete.',
            'No positive strength or manufacturing recommendation can be inferred from this geometry result.'])
(OUT/'screening.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
