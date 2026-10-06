"""Conditional SH housing and lead departure at the photo-located CAM J11.

No connector substitution or hardware/main model edits. Native logical pin map
is untouched; geometric slots deliberately have no asserted physical pin IDs.
"""
from pathlib import Path
PORT_SCRIPT=Path(__file__).resolve();PORT_DIR=PORT_SCRIPT.parent
PORT_HELPER=PORT_DIR/'plan_h06_documented_mates.py';__file__=str(PORT_HELPER)
exec(compile(PORT_HELPER.read_text().split('\nports=json.loads',1)[0],str(PORT_HELPER),'exec'),globals())
__file__=str(PORT_SCRIPT);OUT=PORT_DIR/'cam_pitch_port';OUT.mkdir(exist_ok=True)
from validate import rigidtr
from validate_head_cleanup import geometry_record
from interface_completion import replace_owned
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={n:geometry_record(s.o) for n,s in ss.items()}
candidate=PORT_DIR/'assembly_feed_v3/open_mouth/cleaned'
for name in ['Yaw_Base','Pitch_Yoke']:
    a=np.load(candidate/(name+'.npz'))
    replace_owned(name,manifold.Manifold(manifold.Mesh64(vert_properties=a['vertices_mm'],tri_verts=a['triangles'].astype(np.uint64))))
    ss[name]=Solid(ss[name].o);obstacles[name]=ss[name];trees[name]=ss[name].bvh()

# Reconstruct component solids from the actual displayed source mesh. Remove
# only the declared mating connector from this *check*, never the whole board.
cam=ss['CAM_Mainboard'];o=cam.o
v=np.array([o.matrix_world@x.co for x in o.data.vertices]);f=np.array([list(p.vertices) for p in o.data.polygons],np.uint64)
assert all(len(p.vertices)==3 for p in o.data.polygons)
index=json.loads(o['component_reference_index']);components={}
for row in index:
    va,vb=row['vertices'];fa,fb=row['faces']
    m=manifold.Manifold(manifold.Mesh64(vert_properties=v[va:vb],tri_verts=f[fa:fb]-va))
    assert m.status()==manifold.Error.NoError,row['reference']
    components[row['reference']]=manifold.Manifold.batch_boolean(m.decompose(),manifold.OpType.Add)
full=manifold.Manifold.batch_boolean(list(components.values()),manifold.OpType.Add)
difference=abs(float((full-cam.m).volume()))+abs(float((cam.m-full).volume()))
assert difference<.02,('CAM source reconstruction mismatch',difference)
rest=manifold.Manifold.batch_boolean([m for ref,m in components.items() if ref!='UART_4P'],manifold.OpType.Add)
reference_sources=[(n,s.group,s.m) for n,s in obstacles.items() if n!='CAM_Mainboard']
reference_sources.append(('CAM_without_own_UART','pitch',rest))
reference_sources += [(n,'body',r['m']) for n,r in fixed.items()]

ports=json.loads((PORT_DIR/'h06_ports.json').read_text())
bb=np.array(ports['head']['model_allocation']['bounds_mm'])
xc=float(bb[:,0].mean());yc=float(bb[:,1].mean());mouth=float(bb[0,2])
# JST catalogue page1 gives reference mated axial length6.25; page3 header
# length4.25. Their common rear datum leaves2mm beyond the header mouth.
protrusion=6.25-4.25
exit_z=mouth-protrusion
lo=np.array([xc-2.5,yc-1.4,exit_z]);hi=lo+np.array([5.,2.8,5.])
housing=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
slots=np.array([[xc+dx,yc,exit_z] for dx in [-1.5,-.5,.5,1.5]])
ends=slots+np.array([0,0,-5.])
wire_shapes=[]
for a,b in zip(slots,ends):
    m=manifold.Manifold.cylinder(5.,OD/2,OD/2,48).translate(b.tolist())
    wire_shapes.append(m)
objects=[('housing',housing)]+[(f'slot{i}_5mm_departure',m) for i,m in enumerate(wire_shapes)]
rows=[];minimum_noncontact_gap=math.inf
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        head=np.asarray(rigidtr(yaw,pitch));hits=[];near=[]
        for name,shape in objects:
            for n,group,solid in reference_sources:
                matrix=np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)) if group in ['yaw','pitch'] else np.eye(4)
                # Same rigid body has exactly identity relative motion. Do not
                # introduce a float32 inverse-roundtrip at a nominal PCB face.
                placed=shape if group=='pitch' else shape.transform((np.linalg.inv(matrix)@head)[:3,:4])
                pb=np.array(placed.bounding_box());sb=np.array(solid.bounding_box())
                if np.any(pb[:3]>sb[3:]+.5) or np.any(sb[:3]>pb[3:]+.5):continue
                volume=max(0.,float((placed^solid).volume()))
                if volume>1e-6:hits.append({'part':name,'obstacle':n,'intersection_mm3':volume})
                else:
                    gap=float(placed.min_gap(solid,1.))
                    if gap<.3:near.append({'part':name,'obstacle':n,'gap_mm':gap})
                    minimum_noncontact_gap=min(minimum_noncontact_gap,gap)
        rows.append({'yaw_deg':yaw,'pitch_deg':pitch,'status':'BLOCKED' if hits else 'PASS','hits':hits,'gaps_below_0_3mm':near})
    print('CAM_PORT_YAW',yaw,len(rows),flush=True)

# Unplugging is studied at zero pose. Check the continuous translation sweep;
# the own UART plastic is the mating interface, not a foreign obstruction.
sweep=manifold.Manifold.batch_hull([housing,housing.translate([0,0,-6.])]);entry_hits=[]
for n,group,solid in reference_sources:
    sb=np.array(solid.bounding_box());pb=np.array(sweep.bounding_box())
    if np.any(pb[:3]>sb[3:]) or np.any(sb[:3]>pb[3:]):continue
    volume=max(0.,float((sweep^solid).volume()))
    if volume>1e-6:entry_hits.append({'obstacle':n,'intersection_mm3':volume})
stored={}
for name,m in objects+[('housing_6mm_unplug_sweep',sweep),('CAM_without_own_UART',rest)]:
    a=m.to_mesh64();stored[name+'_v']=np.asarray(a.vert_properties[:,:3]);stored[name+'_f']=np.asarray(a.tri_verts)
np.savez_compressed(OUT/'allocation_meshes.npz',**stored)
source_paths=[PORT_DIR/'h06_ports.json',PROJECT/'config/geometry.json',
    PROJECT/'hardware/v1_2/head_harness_evidence_20261003/sources/JST_SH.pdf',
    PROJECT/'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',
    PROJECT/'mechanical/reports/solid_CAM_Mainboard.json',candidate/'candidate.blend']
result={'status':'PASS' if not any(r['hits'] for r in rows) else 'BLOCKED',
    'scope':'Conditional catalogue SHR-04V-S envelope plus5mm straight tails at photo CAM UART datum; no actual mating qualification',
    'source_main_sha256':source_hash,'source_script_sha256':sha(PORT_SCRIPT),'source_helper_sha256':sha(PORT_HELPER),
    'sources':{str(p.relative_to(PROJECT)):sha(p) for p in source_paths},
    'catalogue_url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
    'documented_reference':{'housing':'SHR-04V-S without protrusions','housing_dimensions_mm':[5.,2.8,5.],
        'pitch_mm':1.,'matching_header_reference':'SM04B-SRSS-TB','mated_length_reference_mm':6.25,
        'header_length_mm':4.25,'derived_protrusion_mm':protrusion,'drawing_is_reference_not_tolerance_stack':True},
    'estimated_datum':{'source':'Existing official-photo reconstruction','header_front_z_mm':mouth,
        'housing_bounds_mm':[lo.tolist(),hi.tolist()],'exit_geometric_slots_mm':slots.tolist(),
        'straight_tail_endpoints_mm':ends.tolist(),'physical_pin_numbering':'BLOCKED; slot indexes are geometry only',
        'location_uncertainty_not_included_in_nominal_test':{'x_z_mm':.4,'y_projection_mm':.5}},
    'source_component_count':len(components),'excluded_mating_component_only':'CAM/UART_4P',
    'source_reconstructed_difference_mm3':difference,'head_poses':130,'rows':rows,
    'zero_pose_unplug_sweep':{'length_allocation_mm':6.,'status':'PASS' if not entry_hits else 'BLOCKED','hits':entry_hits},
    'allowance_meshes_sha256':sha(OUT/'allocation_meshes.npz'),
    'CAM_header_actual_manufacturer_and_revision':'BLOCKED','actual_insertion_depth':'BLOCKED',
    'geometry_with_uncertainties':'NOT_TESTED','housing_catalogue_tolerances':'NOT_TESTED',
    'full_pitch_route':'NOT_TESTED','retention_and_strain_relief':'NOT_TESTED',
    'main_applied':False,'hardware_or_pinmap_changed':False,'manufacturing_release':False,'whole_harness':'BLOCKED'}
(OUT/'mating_allocation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
assert all(geometry_record(s.o)==before[n] for n,s in ss.items() if n not in ['Pitch_Yoke','Yaw_Base'])
print('CAM_UART_ALLOCATION',result['status'],'blocked poses',sum(bool(r['hits']) for r in rows),'unplug',result['zero_pose_unplug_sweep']['status'],flush=True)
