"""Actual SCS0009 solids, four ear seats, datums and finite bench assembly paths."""
from common import *
from head_servo_detail import poses
from validate_head_cleanup import geometry_record


def declared_changes():
    s=P.get('head_servo_detail',{})
    result=set(s.get('changed_existing_ids',[])+s.get('new_ids',[])) if s.get('enabled') else set()
    w=P.get('waveshare_detail',{})
    if w.get('enabled'):result.update(w.get('changed_existing_ids',[])+w.get('new_ids',[])+w.get('approved_mount_change_ids',[]))
    h=P.get('head_mount_simplification',{})
    if h.get('enabled'):result.update(h['changed_existing_ids'])
    a=P.get('assembly_completion',{})
    if a.get('enabled'):result.update(a['changed_existing_ids']+a['new_ids'])
    result.update(declared_cap_edge_changes())
    return result


def declared_retirements():
    s=P.get('head_servo_detail',{})
    return set(s.get('retired_ids',[])) if s.get('enabled') else set()


def validate_front_foot(solids,check):
    s=P['head_servo_detail'];f=s.get('front_corner_cleanup',{})
    if s.get('centered_yaw_pads',{}).get('enabled'):
        from validate_yaw_pad_centering import validate_centered_pads
        validate_centered_pads(solids,check)
        return
    if not f.get('enabled'):return
    base=json.loads((PROJECT/f['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    retired=sorted(set(base['parts'])-set(now))
    old=base['Pitch_Yoke'];old=manifold.Manifold(manifold.Mesh64(np.array(old['vertices_mm']),np.array(old['triangles'],dtype=np.uint64)))
    new=solids['Pitch_Yoke'].m;added=new-old;removed=old-new
    h=P['head_print_cleanup'];m=s['mount'];half=m['yaw_pad_width_x_mm']/2
    local_half=max(half,f['cleanup_half_width_mm'])
    z0,z1=[D['head_z']+z for z in h['yoke_floor_z_from_head_mm']]
    seat=(poses()['Yaw']@Vector((0,0,s['ear_top_mm']))).z
    bottom=seat-m['yaw_pad_thickness_mm'];edge=h['floor_depth_mm']/2
    def region(lo,hi):
        return manifold.Manifold.cube([b-a for a,b in zip(lo,hi)]).translate(lo)
    # Local material operations, not AABB nonoverlap as a collision claim.
    allowed=region([-local_half-.02,edge-.01,z0-.01],
                   [local_half+.02,m['yaw_front_support_y_max_mm']+.01,z1+.01])
    outside=max(0,(added-allowed).volume())+max(0,(removed-allowed).volume())
    pad=region([-half-.01,m['yaw_front_support_y_min_mm']-.01,bottom+.001],
               [half+.01,m['yaw_front_support_y_max_mm']+.01,seat+.01])
    pad_delta=max(0,(added^pad).volume())+max(0,(removed^pad).volume())
    original_post=region([-half,m['yaw_front_support_y_min_mm'],z0],
                         [half,m['yaw_front_support_y_max_mm'],seat])
    post_delta=max(0,(added^original_post).volume())+max(0,(removed^original_post).volume())
    corner=region([-local_half-.02,edge+.001,z0-.01],
                  [local_half+.02,m['yaw_front_support_y_max_mm']+.01,z1-.001])
    remaining=max(0,((new^corner)-original_post).volume())
    continuous=sum(v.volume()>.001 for v in new.decompose())==1
    later=set(P.get('waveshare_detail',{}).get('changed_existing_ids',[]))
    later.update(set(P.get('head_mount_simplification',{}).get('changed_existing_ids',[]))-{'Pitch_Yoke'})
    a=P.get('assembly_completion',{})
    if a.get('enabled'):later.update(a['changed_existing_ids']+a['new_ids'])
    later.update(declared_cap_edge_changes())
    ok=set(changed)-later=={'Pitch_Yoke'} and not retired and outside<.005 and added.volume()<.005 and pad_delta<.005 and post_delta<.005 and remaining<.005 and continuous
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','baseline_revision':base['revision'],
        'changed_parts':changed,'retired_parts':retired,'part_count_delta':len(now)-len(base['parts']),
        'local_added_volume_mm3':max(0,added.volume()),'local_removed_volume_mm3':max(0,removed.volume()),
        'change_outside_declared_local_region_mm3':outside,'ear_pad_and_pilot_difference_mm3':pad_delta,
        'corner_infill_remaining_mm3':remaining,'original_rectangular_post_difference_mm3':post_delta,
        'one_connected_solid':continuous,'sloped_support_added':False,
        'retained_post_forward_projection_mm':m['yaw_front_support_y_max_mm']-edge,
        'base_front_y_mm':edge,'ear_seat_top_z_mm':seat,
        'limits':['Finite model geometry checks only; printed stiffness, fatigue, insert pullout and real assembly are NOT_TESTED.',
                  'Complete original rectangular post, servo mount datums and ear pad remain unchanged; wiring design remains deferred.']}
    save_json(ROOT/'reports/head_seat_foot_validation.json',result)
    check('head_servo_front_foot',result['status'],'仅清除原直角接角处的残留填充；原直角柱、座面和所有硬件保持',result,
          'Per-part mesh/matrix SHA comparison with M1.30; actual manifold difference/intersection volumes in declared local regions and connected-solid count.')


def validate_head_servo(solids,Solid,iv,check):
    s=P.get('head_servo_detail',{})
    if not s.get('enabled'):return
    validate_front_foot(solids,check)
    before=json.loads((PROJECT/s['baseline_geometry']).read_text())['parts']
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=before.get(n));retired=sorted(set(before)-set(now))
    unexpected=sorted(set(changed)-declared_changes());unexpected_retired=sorted(set(retired)-declared_retirements())
    missing_new=sorted(set(s['new_ids'])-set(now));rows=[];bad=[];trs=poses()
    geom=json.loads((ROOT/'reports/head_servo_geometry.json').read_text())
    for axis,tr in trs.items():
        a=solids[axis+'_Servo'];v=np.array([tuple(tr.inverted()@Vector(x)) for x in a.v]);lo=v.min(0);hi=v.max(0)
        components=a.m.decompose();positive=sum(m.volume()>.001 for m in components)
        target=np.array([[s['ear_outer_x_mm'][0],-s['case_width_mm']/2,0],
                         [s['ear_outer_x_mm'][1],s['case_width_mm']/2,s['gearbox_top_mm']]])
        error=float(np.max(np.abs(np.array([lo,hi])-target)))
        shaft=solids[axis+'_Output'];vv=np.array([tuple(tr.inverted()@Vector(x)) for x in shaft.v])
        radial=np.linalg.norm(vv[:,:2],axis=1);outer_d=float(radial.max()*2)
        shaft_gap=float(vv[:,2].min()-hi[2])
        holes=[]
        for x in s['output_to_ear_hole_mm']:
            p0=tr@Vector((x,0,s['ear_bottom_mm']-.3));p1=tr@Vector((x,0,s['ear_top_mm']+.3))
            hits=a.m.ray_cast(list(p0),list(p1))
            z=(s['ear_bottom_mm']+s['ear_top_mm'])/2
            rim=[]
            for direction in [(1,0),(-1,0),(0,1),(0,-1)]:
                q0=tr@Vector((x,0,z));q1=tr@Vector((x+direction[0]*1.4,direction[1]*1.4,z))
                hh=a.m.ray_cast(list(q0),list(q1))
                rim.append((Vector(hh[0].position)-q0).length if hh else None)
            skin0=tr@Vector((x,2,s['ear_bottom_mm']-1));skin1=tr@Vector((x,2,s['ear_top_mm']+1))
            skin=a.m.ray_cast(list(skin0),list(skin1))
            skin_z=sorted((tr.inverted()@Vector(h.position)).z for h in skin)
            holes.append({'center_local_x_mm':x,'axial_ray_hits':len(hits),'four_radial_bore_samples_mm':rim,
                          'ear_bottom_top_from_mesh_mm':skin_z})
            if hits:bad.append({'id':a.name,'error':'Ear centre not open','x_mm':x})
            if any(r is None or abs(r-s['ear_hole_diameter_mm']/2)>.003 for r in rim):bad.append(holes[-1])
            if len(skin_z)!=2 or max(abs(z-t) for z,t in zip(skin_z,[s['ear_bottom_mm'],s['ear_top_mm']]))>.003:bad.append(holes[-1])
        row={'id':a.name,'case_positive_components':positive,'local_bounds_mm':[lo.tolist(),hi.tolist()],
             'maximum_envelope_error_mm':error,'output_enclosing_diameter_mm':outer_d,
             'case_to_output_axial_gap_mm':shaft_gap,'ear_holes':holes,
             'case_motion_group':a.group,'output_motion_group':shaft.group}
        rows.append(row)
        if positive!=1 or error>.003 or abs(shaft_gap)>.003 or abs(outer_d-s['spline_outer_diameter_mm'])>.003:
            bad.append(row)
    seats=[];tools=[];assembly=[];m=s['mount']
    for row in geom['mounts']:
        name=row['id'];point=Vector(row['seat_plane_point_mm']);axis=row['axis'];d=Vector((0,0,1)) if axis=='Z' else Vector((1,0,0))
        o=ring('seat_backing_probe',point-d*.6,1.95,1.65,.4,axis,n=64);a=Solid(o)
        missing=max(0,(a.m-solids['Pitch_Yoke'].m).volume());seats.append({'id':name,'missing_ring_material_mm3':missing})
        SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
        if missing>.005:bad.append(seats[-1])
        screw=solids[name+'_Screw'];start=Vector(row['ear_top_point_mm'])+d*1.9
        tool=cyl('servo_driver',start+d*15,2.1,30,axis,n=64);toolsolid=Solid(tool)
        removed={n for n,a in solids.items() if a.group=='pitch'}|{'Head_Front','Head_Rear','Body_Upper','Body_Lower'}
        if name.startswith('Head_Pitch_'):removed|={'Yaw_Servo','Yaw_Output','Yaw_Lock_Screw'}|{n for n in solids if n.startswith('Head_Yaw_Ear_')}
        removed.add(name+'_Screw')
        hits=[{'part':n,'mm3':v} for n,a in solids.items() if n not in removed and (v:=iv(toolsolid,a))>.01]
        tools.append({'id':name,'driver_diameter_mm':4.2,'length_mm':30,'removed':sorted(removed),'hits':hits})
        SOLIDS.pop(tool.name,None);bpy.data.objects.remove(tool,do_unlink=True)
    # Pitch case enters from the open central bay along its own output axis,
    # before the yaw servo and optical/pitch-head assembly are fitted.
    names=['Pitch_Servo','Pitch_Output'];removed={n for n,a in solids.items() if a.group=='pitch'}|{'Yaw_Servo','Yaw_Output','Yaw_Lock_Screw','Head_Front','Head_Rear','Body_Upper','Body_Lower'}|{n for n in solids if n.startswith(('Head_Pitch_Ear_','Head_Yaw_Ear_'))}
    for dx in np.arange(0,35.001,1):
        tr=Matrix.Translation((float(dx),0,0))
        for name in names:
            a=Solid(solids[name].o,solids[name],tr)
            for n,b in solids.items():
                if n in removed or n in names:continue
                if (v:=iv(a,b))>.01:assembly.append({'travel_mm':float(dx),'moving':name,'obstacle':n,'mm3':v})
    preserved=not unexpected and not unexpected_retired and not missing_new
    ok=preserved and not bad and not any(t['hits'] for t in tools) and not assembly
    result={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','source':s['source'],
            'changed':changed,'retired':retired,'unexpected_changes':unexpected,'unexpected_retired':unexpected_retired,'missing_new':missing_new,
            'servos':rows,'interface_failures':bad,'seat_material':seats,'tools':tools,'pitch_case_insertion_failures':assembly,
            'pitch_insertion':{'direction':'+X withdrawal / -X installation','travel_mm':35,'step_mm':1,'prerequisites':sorted(removed)},
            'retained_datums':'Original output tip and axis locations; all undeclared world/local mesh hashes and matrices unchanged from M1.29.',
            'limits':s['unknowns']+['Geometric continuity/contact and finite insertion samples only. Heat-set pilot holes, pullout, screw tightening, bearing fit and strength require physical trial.','Routing deferred, not checked as a working cable assembly.']}
    check('head_servo_detailed_interfaces',result['status'],'小舵机壳体连续、安装耳孔座对齐、输出轴原位及台面装配路径',result,
          'Exact per-part geometry baseline plus manifold component count, actual mesh envelopes, hole rays, material-volume probes,4.2mm driver rods and1mm finite insertion samples. Not supplier CAD or physical qualification.')
    check('head_routing_deferred','NOT_TESTED','按用户要求延后走线；撤掉头部预估线孔、线夹并隐藏旧线束示意',P['head_routing'])
    check('head_servo_horn_engagement','BLOCKED','输出轴按厂图定位；现有舵盘仍为占位，不可据此加工花键配合',
          {'documented_spline':'20T / nominal diameter3.95mm / M2x0.4 lock',
           'parts':['Yaw_Horn','Pitch_Horn'],'status':'Horn family/revision, tooth profile, engagement length and lock screw must match bought units.'})
    save_json(ROOT/'reports/head_servo_validation.json',result)
