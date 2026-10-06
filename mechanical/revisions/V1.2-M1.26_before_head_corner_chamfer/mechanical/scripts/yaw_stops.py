"""M1.21 compact yaw stops. Real solid geometry; impact strength is unqualified."""
from common import *

S=P.get('compact_yaw_stops',{})

def sector(name,ri,ro,a0,a1,z0,z1):
    count=max(2,math.ceil((a1-a0)/S['arc_step_deg']))
    aa=np.linspace(math.radians(a0),math.radians(a1),count+1)
    poly=[(ro*math.cos(a),ro*math.sin(a)) for a in aa]
    poly += [(ri*math.cos(a),ri*math.sin(a)) for a in reversed(aa)]
    m=manifold.CrossSection([poly]).extrude(z1-z0).translate([0,0,z0])
    data=m.to_mesh64();o=mesh(name,data.vert_properties[:,:3].tolist(),data.tri_verts.tolist())
    SOLIDS[o.name]=m
    return o

def retain_feature(o,name):
    c=clone(o,'DATUM_Compact_Yaw_'+name);c['role']='construction';c['export_candidate']=False
    c['data_status']='ASSUMED';c['functional_purpose']='Exact generated stop feature before integral union; validation helper only'
    move_collection(c,'DATUMS')

def build_compact_stops(base,yoke):
    bz=D['yaw_bearing_z'];mz=[bz+v for v in S['moving_z_from_bearing_mm']]
    fz=[bz+v for v in S['fixed_z_from_bearing_mm']]
    rz=[bz+v for v in S['fixed_root_z_from_bearing_mm']]
    collar=ring('compact_yaw_rotor_shoulder',(0,0,sum(mz)/2),S['collar_outer_radius_mm'],S['collar_inner_radius_mm'],mz[1]-mz[0],n=192)
    retain_feature(collar,'Collar');union(yoke,collar)
    ha=S['moving_half_angle_deg']
    lug=sector('compact_yaw_rotor_key',S['moving_inner_radius_mm'],S['moving_outer_radius_mm'],-ha,ha,*mz)
    retain_feature(lug,'Key');union(yoke,lug)
    for sign in [-1,1]:
        angles=sorted([sign*a for a in S['fixed_sector_deg']])
        block=sector('compact_yaw_fixed_block',S['fixed_inner_radius_mm'],S['fixed_outer_radius_mm'],*angles,*fz)
        foot=sector('compact_yaw_root',S['fixed_root_inner_radius_mm'],S['fixed_outer_radius_mm'],*angles,*rz)
        union(block,foot);retain_feature(block,'Fixed_'+str(sign));union(base,block)
    base['yaw_stop_note']='Two short annular blocks rooted directly on bearing housing, inside shadow rim. Bearing can lift after rotor is removed. Not impact-qualified.'
    yoke['yaw_stop_note']='Low integral annular shoulder with short broad key, above bearing; no thin radial stop flag. Not impact-qualified.'
    save_json(ROOT/'reports/compact_yaw_stop_geometry.json',{'revision':P['revision'],'parameters_source':'config/geometry.json#/compact_yaw_stops',
        'moving_z_mm':mz,'fixed_z_mm':fz,'fixed_root_z_mm':rz,'normal_yaw_deg':[-60,60],
        'ideal_sector_boundary_onset_deg':S['fixed_sector_deg'][0]-ha,
        'added_parts':0,'added_fasteners':0,'print_strength':'NOT_TESTED'})

def validate_compact_stops(solids=None):
    from validate import Solid,intersect_volume
    if solids is None:solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
    rotor=solids['Pitch_Yoke'];base=solids['Yaw_Base'];bearing=solids['Yaw_Bearing']
    features={n:Solid(bpy.data.objects[PREFIX+'DATUM_Compact_Yaw_'+n]) for n in ['Collar','Key','Fixed_-1','Fixed_1']}
    rows=[];step=S['contact_sample_step_deg'];tol=S['intersection_tolerance_mm3']
    for sign in [-1,1]:
        free=0.;hit=None
        for angle in np.arange(0,75+step/2,step):
            moved=Solid(rotor.o,rotor,Matrix.Rotation(math.radians(sign*angle),4,'Z'))
            overlap=moved.m^base.m
            if overlap.volume()>tol:
                v=np.asarray(overlap.to_mesh64().vert_properties)[:,:3]
                hit={'first_sampled_overlap_deg':sign*float(angle),'previous_free_sample_deg':sign*free,
                    'overlap_mm3':float(overlap.volume()),'overlap_bounds_xyz_mm':list(zip(v.min(0).tolist(),v.max(0).tolist()))}
                break
            free=float(angle)
        wanted=S['expected_contact_interval_deg']
        ok=bool(hit and wanted[0]<=abs(hit['first_sampled_overlap_deg'])<=wanted[1])
        rows.append({'direction':sign,'status':'PASS' if ok else 'FAIL','engagement':hit})
    normal=[];clearances=[];wires=[]
    routes=[Solid(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.get('role')=='routing']
    for angle in range(-60,61,5):
        tr=Matrix.Rotation(math.radians(angle),4,'Z');moved=Solid(rotor.o,rotor,tr)
        overlap=intersect_volume(moved,base)
        if overlap>tol:normal.append({'yaw_deg':angle,'overlap_mm3':overlap})
        for n in ['Collar','Key']:
            f=Solid(features[n].o,features[n],tr)
            clearances.append({'yaw_deg':angle,'feature':n,'base_gap_mm':f.m.min_gap(base.m,10),
                               'bearing_gap_mm':f.m.min_gap(bearing.m,10)})
        for r in routes:
            # Full combined pitch cable sampling is also performed by validate.py.
            rr=Solid(r.o,r,tr) if r.group in ['yaw','pitch'] else r
            for n,f in features.items():
                ff=Solid(f.o,f,tr) if n in ['Collar','Key'] else f
                vol=intersect_volume(ff,rr)
                if vol>.1:wires.append({'yaw_deg':angle,'feature':n,'route':r.name,'overlap_mm3':vol})
    paths=[]
    for what,part,obstacles in [('rotor',rotor,{'base':base,'bearing':bearing}),('bearing_after_rotor_removed',bearing,{'base':base})]:
        for d in range(46):
            moved=Solid(part.o,part,Matrix.Translation((0,0,d)))
            for n,target in obstacles.items():
                vol=intersect_volume(moved,target)
                if vol>tol:paths.append({'item':what,'lift_mm':d,'obstacle':n,'overlap_mm3':vol})
    dims={n:{'bounds_xyz_mm':list(zip(f.lo.tolist(),f.hi.tolist())),
             'max_radius_mm':float(np.linalg.norm(f.v[:,:2],axis=1).max())} for n,f in features.items()}
    rim_top=bounds(bpy.data.objects[PREFIX+'Yaw_Base'])[2][1]
    below=all(f.hi[2]<=rim_top+.001 for f in features.values())
    inside=all(d['max_radius_mm']<P['part_consolidation']['fixed_rim_join_inner_radius_mm'] for d in dims.values())
    gap=min(c['base_gap_mm'] for c in clearances)
    ok=all(r['status']=='PASS' for r in rows) and not any([normal,wires,paths]) and below and inside and gap>=S['minimum_sampled_running_gap_mm']-.01
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','step_deg':step,
        'tested_each_direction_deg':[0,75],'intersection_threshold_mm3':tol,
        'stop_center_z_mm':D['yaw_bearing_z']+sum(S['moving_z_from_bearing_mm'])/2,'cases':rows,
        'normal_yaw_deg':[-60,60],'normal_sample_step_deg':5,'normal_overlaps':normal,
        'clearance_samples':clearances,'minimum_new_rotating_feature_to_base_gap_mm':gap,
        'minimum_new_rotating_feature_to_bearing_gap_mm':min(c['bearing_gap_mm'] for c in clearances),
        'routing_overlaps_at_pitch_zero':wires,'lift_each_1_mm_to_45_mm_failures':paths,
        'lift_prerequisites':'Detach pitch head, yaw servo and cross-retainer per existing service sequence. Reaction link is released/lifted with U/journal. Bearing removal is checked with rotor absent. Only named mating solids are checked in this local path test.',
        'features':dims,'all_features_inside_fixed_rim':inside,'all_features_below_rim_top':below,
        'ring_top_z_mm':rim_top,'fixed_radial_overhang_from_bearing_wall_mm':0,
        'moving_key_radial_extension_beyond_shoulder_mm':S['moving_outer_radius_mm']-S['collar_outer_radius_mm'],
        'moving_feature_height_mm':S['moving_z_from_bearing_mm'][1]-S['moving_z_from_bearing_mm'][0],
        'added_parts':0,'added_fasteners':0,'strength':'NOT_TESTED',
        'method':'Actual consolidated meshes rotated in 0.25deg samples to locate first positive-volume overlap; normal 5deg samples and named removal paths every1mm. Additional full-model combined motion and routing checks in validation.json.',
        'limits':['Finite sampling/volume threshold, not exact continuous contact angle or continuous collision proof.',
            'Normal commanded yaw remains +/-60deg. No permission to drive against mechanical stops.',
            'Bearing envelope and clearances are trial dimensions; actual bearing, tolerance stack, friction and printed distortion remain unqualified.',
            'No load, impact, fatigue, creep, slicer or physical print test.']}
    save_json(ROOT/'reports/integrated_stop_check.json',result)
    return result
