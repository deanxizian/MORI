"""Represent all four CAM wire lengths while only the fixed bridge is fitted.

The PH housing remains with the bridge and is not treated as body-fixed. Full
existing nominal wire allocations are retained as upright head-side stock;
the yaw and pitch assemblies are explicitly absent. This diagnoses a staged
alternative, not adoption, supplier cut lengths or a complete feed proof.
"""
from pathlib import Path
STOCK_SCRIPT=Path(__file__).resolve();STOCK_A8=STOCK_SCRIPT.parent
STOCK_HELPER=STOCK_A8/'plan_h06_documented_mates.py'
__file__=str(STOCK_HELPER)
exec(compile(STOCK_HELPER.read_text().split('\nports=json.loads',1)[0],str(STOCK_HELPER),'exec'),globals())
__file__=str(STOCK_SCRIPT)
FULL=STOCK_A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head'
STOCK_OUT=FULL/'bridge_wire_stock';STOCK_OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
membership_path=FULL/'split_assembly/screen.json';membership=json.loads(membership_path.read_text())
assert membership['source_main_sha256']==source_hash and membership['source_objects']==209
protected=membership['protected_sources']
groups={n:set(v) for n,v in membership['membership'].items()}
bridge=groups['fixed_bridge'];upper=groups['upper_shell'];core=groups['body_core']
phys={n:s.m for n,s in ss.items()}
for n,row in membership['substituted_unadopted_prints'].items():
    p=PROJECT/row['path'];assert sha(p)==row['sha256'];a=np.load(p)
    phys[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))

partial_path=STOCK_A8/'cam_pitch_port/lower_staging/body_partial_curves.npz'
partial=np.load(partial_path)
datum_path=STOCK_A8/'cam_connector_install/route_datums.json'
datums=json.loads(datum_path.read_text())
body_math_path=STOCK_A8/'body_prefix_v2/body_to_yaw_motion.json'
body_math=json.loads(body_math_path.read_text())
wire={};rows=[];terminals={}
lengths=[]
for pin in range(1,5):
    p=partial[f'pin{pin}_yaw0'];row=datums['rows'][pin-1]
    prefix_length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
    allocation=row['total_routed_model_mm'];stock=allocation-prefix_length
    assert stock>140 and abs(p[-1,2]-193)<1e-8
    v=np.diff(p,axis=0)[-1];assert np.linalg.norm(v/np.linalg.norm(v)-[0,0,1])<1e-8
    extra=p[-1]+np.linspace(0,stock,math.ceil(stock/.05)+1)[:,None]*np.array([0.,0.,1.])
    wire[pin]=np.vstack([p,extra[1:]])
    error=next(r['curve_error_bound_mm'] for r in body_math['rows'] if r['array_key']==f'pin{pin}_yaw0')
    lengths.append(dict(pin_reference='Motion J5.'+str(pin),geometric_slot='H06-G'+str(pin),
        full_nominal_allocation_mm=allocation,prefix_polyline_mm=prefix_length,upright_stock_mm=stock,
        endpoint_mm=wire[pin][-1].tolist(),curve_chord_error_mm=error,
        initial_straight_stock_only=True,supplier_cut_length_mm=None))
    end=wire[pin][-1];er=np.r_[end[:2],0.];er/=np.linalg.norm(er);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
    tr=np.column_stack([er,et,ez,end+ez*4.1/2])
    terminals[pin]=manifold.Manifold.cube([1.,1.8,4.1],center=True).minkowski_sum(manifold.Manifold.sphere(.31,48)).transform(tr)
np.savez_compressed(STOCK_OUT/'full_wires.npz',**{'pin'+str(k):v for k,v in wire.items()})

targets={n:phys[n] for n in core|upper|bridge}
targets.update({'Plug_'+n:s.m for n,s in plug.items() if n!='motion_J5'})
targets.update({'fixed_wire_'+n:r['m'] for n,r in fixed.items()})
target_group={n:('bridge' if n in bridge else 'upper' if n in upper or n.startswith('Plug_rear_') else 'core') for n in targets}
target_data={}
for n,m in targets.items():
    a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3]);f=np.asarray(a.tri_verts)
    target_data[n]=(m,v.min(0),v.max(0),BVHTree.FromPolygons(v,f.tolist(),all_triangles=True))

I=np.eye(4);origin=Vector((0,0,D['body_z']))
def trans(y=0.,z=0.):
    t=I.copy();t[:3,3]=[0,y,z];return t
def shellpose(a,y,z):
    return np.asarray(Matrix.Translation((0,y,z))@Matrix.Translation(origin)@
        Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin))
def transform_points(p,t):return p@t[:3,:3].T+t[:3,3]

def wire_check(pin,pts,matrices,first_only=True):
    step=float(np.max(np.linalg.norm(np.diff(pts,axis=0),axis=1)))
    allowance=OD/2+MARGIN+step/2+lengths[pin-1]['curve_chord_error_mm']+1e-4
    for name,(m,lo,hi,tree) in target_data.items():
        p=transform_points(pts,matrices[target_group[name]])
        mask=np.all(p>=lo-allowance,axis=1)&np.all(p<=hi+allowance,axis=1)
        indices=np.flatnonzero(mask)
        for idx in indices:
            q=p[idx];dist=float(tree.find_nearest(Vector(q))[3])
            if dist<allowance:
                return dict(kind='wire_clearance',pin=pin,point_mm=q.tolist(),obstacle=name,
                    centreline_distance_mm=dist,required_bound_mm=allowance)
        starts=indices[np.r_[True,np.diff(indices)>1]] if len(indices) else []
        for idx in starts:
            q=p[idx]
            if np.all(q>=lo) and np.all(q<=hi):
                probe=manifold.Manifold.sphere(.005,12).translate(q.tolist())
                if (probe^m).volume()>probe.volume()/2:
                    return dict(kind='wire_inside_solid',pin=pin,obstacle=name,point_mm=q.tolist())
    return None

housing=plug['motion_J5'].m
# A source mating envelope can intentionally overlap its own native header.
# Preserve that exact final spatial overlap as an explicitly unqualified
# mating domain; unrelated board material is never exempted.
mating_domain=housing^phys['MCU_Carrier']
def rigid_check(shape,matrices,is_housing=False):
    for name,(m,lo,hi,_) in target_data.items():
        placed=shape.transform(matrices[target_group[name]][:3,:4]);box=np.asarray(placed.bounding_box())
        if np.any(box[:3]>hi) or np.any(box[3:]<lo):continue
        overlap=placed^m
        if is_housing and name=='MCU_Carrier':overlap-=mating_domain
        volume=max(0.,float(overlap.volume()))
        if volume>1e-5:return dict(kind='housing' if is_housing else 'contact_space',obstacle=name,intersection_mm3=volume)
    return None

stages=[
 ('bridge_lift_shell_held',[(shellpose(15,0,14),trans(z=float(z))) for z in np.arange(0,18.01,.5)]),
 ('body_bridge_back',[(shellpose(15,float(y),14),trans(y=float(y),z=18)) for y in np.linspace(0,-14,57)]),
 ('body_bridge_bench',[(shellpose(15,-14,float(z)),trans(y=-14,z=float(z+4))) for z in np.arange(14,140.01,.5)]),
 ('body_shell_settle',[(shellpose(15*float(u),0,14*float(u)),I) for u in np.linspace(0,1,61)]),
]
started=time.time()
for label,poses in stages:
    failure=None;checked=0
    for index,(st,bt) in enumerate(poses):
        matrices={'core':bt,'upper':np.linalg.inv(st)@bt,'bridge':I}
        failure=rigid_check(housing,matrices,True)
        if not failure:
            for pin,pts in wire.items():
                failure=wire_check(pin,pts,matrices) or rigid_check(terminals[pin],matrices)
                if failure:break
        checked+=1
        if failure:
            failure.update(index=index,shell_transform=st.tolist(),bridge_transform=bt.tolist());break
    row=dict(stage=label,status='BLOCKED' if failure else 'PASS',checked_positions=checked,
        planned_positions=len(poses),failure=failure)
    rows.append(row);print('BRIDGE_WIRE_STOCK',label,row['status'],checked,failure,round(time.time()-started,2),flush=True)

report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Finite body/bridge motion with all four nominal wire lengths, upright head-side stock and a common PH allocation; not a full feeding/handling sequence',
    script_sha256=sha(STOCK_SCRIPT),helper_sha256=sha(STOCK_HELPER),source_main_sha256=source_hash,
    source_split_report_sha256=sha(membership_path),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [partial_path,datum_path,body_math_path,fixed_path]},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    membership=membership['membership'],present_source_objects=len(core|upper|bridge),
    source_objects=209,mating_allocations=len(plug),fixed_wire_solids=len(fixed),
    lengths=lengths,full_wire_polylines_sha256=sha(STOCK_OUT/'full_wires.npz'),
    wire_OD_mm=OD,clearance_requirement_mm=MARGIN,reference_minimum_bend_radius_mm=7.,
    terminal_dimensions_mm=[1.,1.8,4.1],terminal_evidence='ASSUMED requested space',
    body_housing_final_overlap_domain_mm3=float(mating_domain.volume()),body_housing_fit='NOT_TESTED',
    rows=rows,mutual_wire_clearance='NOT_TESTED',continuous_motion='NOT_TESTED',
    feed_into_bridge_before_this_state='NOT_TESTED',later_yaw_installation_over_stock='NOT_TESTED',
    full_wire_physical_shape_and_support='NOT_TESTED',supplier_cut_lengths=False,
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(STOCK_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('BRIDGE_WIRE_STOCK_DONE',report['status'],round(time.time()-started,2),flush=True)
