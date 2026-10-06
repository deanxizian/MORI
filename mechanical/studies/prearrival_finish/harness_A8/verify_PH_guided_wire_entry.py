"""Replay saved full wires and continuously cover the new PH/lead motion.

Linear primitives use endpoint convex hulls. Circular primitives add the exact
maximum-radius chord sagitta as an axis-aligned Minkowski box. Full flexible
wire-to-wire motion is still a finite check, clearly distinct from these sweeps.
"""
from pathlib import Path

GUIDE_VERIFY_SCRIPT=Path(__file__).resolve()
GUIDE_VERIFY_HELPER=GUIDE_VERIFY_SCRIPT.parent/'screen_PH_guided_wire_entry.py'
__file__=str(GUIDE_VERIFY_HELPER)
exec(compile(GUIDE_VERIFY_HELPER.read_text().split('\nstarted=time.time();',1)[0],
             str(GUIDE_VERIFY_HELPER),'exec'),globals())
__file__=str(GUIDE_VERIFY_SCRIPT)
source_report=json.loads((OUT/'screen.json').read_text())
assert source_report['status']=='PASS' and source_report['script_sha256']==sha(GUIDE_VERIFY_HELPER)
for name,h in source_report['source_files'].items():assert sha(PROJECT/name)==h,name
assert source_report['curves_sha256']==sha(OUT/'curves.npz')
guide=source_report['selected_guide']
for segment in guide['segments']:
    for k in ['start','end','tangent','normal','entry','axis','c','r0']:
        if k in segment:segment[k]=np.asarray(segment[k],dtype=float)
stored=np.load(OUT/'curves.npz')


def lead_box(s,pin):
    p,t,n=guide_pose(guide,s)
    b=np.cross(t,n)
    q=p+slot_offsets[pin-1]*n-2.5*t
    diameter=OD+2*MARGIN
    return manifold.Manifold.cube([diameter,diameter,5+diameter],center=True).transform(np.column_stack([n,b,t,q]))


def continuous_bound(segment,a,b,shape_a,shape_b):
    bound=manifold.Manifold.batch_hull([shape_a,shape_b])
    error=0.
    if segment['kind']=='arc':
        mesh=shape_a.to_mesh64()
        vertices=np.asarray(mesh.vert_properties[:,:3])-segment['c']
        perpendicular=vertices-np.outer(vertices@segment['axis'],segment['axis'])
        radius_max=float(np.linalg.norm(perpendicular,axis=1).max())
        theta=(b-a)/segment['radius']
        assert theta<math.pi
        error=radius_max*(1-math.cos(theta/2))+1e-6
        bound=bound.minkowski_sum(manifold.Manifold.cube([2*error]*3,center=True))
    return bound,error


started=time.time();sweeps=[];max_volume=0.;maximum_error=0.;failure=None
for primitive_index,segment in enumerate(guide['segments']):
    sample=np.linspace(segment['s0'],segment['s1'],max(2,math.ceil(segment['length']/.75)+1))
    # Do not let a mating exception extend beyond the documented first 8 mm.
    if segment['s0']<8.<segment['s1']:
        sample=np.unique(np.r_[sample,8.])
    for a,b in zip(sample[:-1],sample[1:]):
        for item in ['PH',1,2,3,4]:
            shape_a=guided_housing(guide,float(a)) if item=='PH' else lead_box(float(a),item)
            shape_b=guided_housing(guide,float(b)) if item=='PH' else lead_box(float(b),item)
            bound,error=continuous_bound(segment,float(a),float(b),shape_a,shape_b)
            maximum_error=max(maximum_error,error)
            checks=[]
            for name,obstacle in near(bound):
                overlap=bound^obstacle
                mating_exception=bool(item=='PH' and b<=8.+1e-8 and name=='MCU_Carrier')
                if mating_exception:overlap-=native
                volume=max(0.,float(overlap.volume()));max_volume=max(max_volume,volume)
                checks.append(dict(obstacle=name,intersection_mm3=volume,native_mating_exception=mating_exception))
                if volume>1e-5:
                    failure=dict(primitive=primitive_index,item=item,a_mm=float(a),b_mm=float(b),
                                 obstacle=name,intersection_mm3=volume,bound_error_mm=error)
                    break
            sweeps.append(dict(primitive=primitive_index,item=item,a_mm=float(a),b_mm=float(b),
                bound_error_mm=error,status='BLOCKED' if failure else 'PASS',near_checks=checks))
            if failure:break
        if failure:break
    print('GUIDE_CONTINUOUS',primitive_index,len(sweeps),'BLOCKED' if failure else 'PASS',failure,flush=True)
    if failure:break

wire_rows=[];wire_failure=None;max_source_reconstruction_error=0.;min_radius=1000.;min_stock=1000.;max_stock=0.
for row in source_report['replay']:
    index=row['index'];s=row['s_mm'];curves={}
    for meta in row['curves']:
        pin=meta['pin'];points=stored[f'pose{index}_pin{pin}']
        regenerated,error=guided_wire(guide,s,pin)
        assert error is None and points.shape==regenerated['points'].shape
        discrepancy=float(np.linalg.norm(points-regenerated['points'],axis=1).max())
        max_source_reconstruction_error=max(max_source_reconstruction_error,discrepancy)
        assert discrepancy<1e-8
        assert abs(meta['analytic_total_mm']-lengths[pin-1]['full_nominal_allocation_mm'])<1e-8
        if meta['minimum_analytic_radius_mm'] is not None:min_radius=min(min_radius,meta['minimum_analytic_radius_mm'])
        min_stock=min(min_stock,meta['stock_mm']);max_stock=max(max_stock,meta['stock_mm'])
        c=dict(meta,points=points);curves[pin]=c
        lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
        wire_failure=wire_check(pin,points,identity_matrices) or self_check(c)
        if wire_failure:break
    pairs=[]
    if not wire_failure:pairs,wire_failure=mutual_check(curves)
    if not wire_failure:wire_failure=terminal_checks(curves,I)
    if not wire_failure:
        own=guided_housing(guide,s,padded=False)
        mesh=own.to_mesh64();vertices=np.asarray(mesh.vert_properties[:,:3]);faces=np.asarray(mesh.tri_verts)
        tree=BVHTree.FromPolygons(vertices,faces.tolist(),all_triangles=True)
        lo,hi=vertices.min(0),vertices.max(0)
        for pin,c in curves.items():
            points=c['points'];ds=np.linalg.norm(np.diff(points,axis=0),axis=1)
            arc=np.r_[0.,ds.cumsum()]
            points=points[arc>=5.-1e-8]
            distance_bound=OD/2+MARGIN+c['curve_chord_error_mm']+float(ds.max())/2+1e-4
            candidates=points[np.all(points>=lo-distance_bound,axis=1)&np.all(points<=hi+distance_bound,axis=1)]
            for q in candidates:
                distance=float(tree.find_nearest(Vector(q))[3])
                if distance<distance_bound:
                    wire_failure=dict(kind='nonlocal_wire_own_PH',pin=pin,point_mm=q.tolist(),
                        sampled_distance_mm=distance,required_bound_mm=distance_bound);break
                if np.all(q>=lo) and np.all(q<=hi):
                    probe=manifold.Manifold.sphere(.005,12).translate(q.tolist())
                    if (probe^own).volume()>probe.volume()/2:
                        wire_failure=dict(kind='nonlocal_wire_inside_own_PH',pin=pin,point_mm=q.tolist());break
            if wire_failure:break
    wire_rows.append(dict(index=index,s_mm=s,status='BLOCKED' if wire_failure else 'PASS',failure=wire_failure,pairs=pairs))
    if index%40==0 or wire_failure:print('GUIDE_SAVED_WIRE',index,'BLOCKED' if wire_failure else 'PASS',wire_failure,flush=True)
    if wire_failure:break

final=guided_housing(guide,guide['length'])
upper_top=max(targets[n].bounding_box()[5] for n in targets if target_group[n]=='upper')
external_gap=float(final.bounding_box()[2]-upper_top)
assert external_gap>0
status='PASS' if not failure and not wire_failure and len(wire_rows)==len(source_report['replay']) else 'BLOCKED'
report=dict(status=status,scope='Continuous PH/first-5mm bounds plus saved full-wire finite replay, not complete harness assembly',
    script_sha256=sha(GUIDE_VERIFY_SCRIPT),helper_sha256=sha(GUIDE_VERIFY_HELPER),
    source_report_sha256=sha(OUT/'screen.json'),source_curves_sha256=sha(OUT/'curves.npz'),
    source_files=source_report['source_files'],protected_sources=protected,
    sweeps=sweeps,sweep_failure=failure,continuous_sweeps=len(sweeps),maximum_rotation_bound_error_mm=maximum_error,
    maximum_remaining_intersection_mm3=max_volume,wire_rows=wire_rows,wire_failure=wire_failure,
    wire_finite_positions=len(wire_rows),max_saved_reconstruction_error_mm=max_source_reconstruction_error,
    minimum_analytic_bend_radius_mm=min_radius,free_end_stock_range_mm=[min_stock,max_stock],
    final_PH_clearance_above_upper_shell_mm=external_gap,
    native_mating_fit='NOT_TESTED',initial_8mm_mating_exception='MCU_Carrier overlap of the original padded axial sweep only',
    nonlocal_wire_own_PH_finite='PASS' if not wire_failure else 'BLOCKED',own_lead_root_exception_mm=5.,
    complete_flexible_wire_continuous_motion='NOT_TESTED',subsequent_neck_threading='NOT_TESTED',
    later_H01_H04_installation='NOT_TESTED',hands_and_tools='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('GUIDE_VERIFICATION_DONE',status,len(sweeps),len(wire_rows),external_gap,flush=True)
