"""M1.43: independent scope, seats, axial stack and assembled shell service.

All tests consume final float32 Blender meshes. Finite nominal geometry is not
print strength, tolerance, physical assembly or manufacturing qualification.
"""
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from export import topology
from interface_completion import axial
from assembly_issue_fixes import change_regions,boxm
import hashlib

def validate_assembly_issue_fixes(ss,check):
    q=P['assembly_issue_fixes'];base=json.loads((PROJECT/q['baseline_geometry']).read_text())
    report={'revision':P['revision'],'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'baseline_revision':base['revision'],'items':[1,2,3,4,5,6]};failed=[]
    def emit(key,ok,label,data):
        report[key]=data
        if not ok:failed.append(key)
        check('six_fixes_'+key,'PASS' if ok else 'FAIL',label,data,'Final actual solid geometry; finite sampling and declared local changes only. Physical validation NOT_TESTED.')
    def old(n):
        b=base[n];return manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)))
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if n in base['parts'] and now[n]!=base['parts'][n]);added=sorted(set(now)-set(base['parts']));retired=sorted(set(base['parts'])-set(now))
    later=P.get('head_axial_retention',{}) if P.get('head_axial_retention',{}).get('enabled') else {}
    expected=set(q['changed_existing_ids'])|set(later.get('changed_existing_ids',[]))|declared_p5r7_changes()|declared_rear_mesh_repair_changes()|declared_camera_cam_changes()|(declared_neck_capacity_changes()&set(base['parts']))
    emit('scope',set(changed)==expected and set(added)==set(later.get('new_ids',[]))|declared_p5r7_additions() and not retired,'六项变更及后续已确认防脱、P5R7接口逐件核对',dict(changed=changed,expected=sorted(expected),added=added,retired=retired,print_count=sum(o.get('category')=='PRINTABLE' for o in parts() if o.get('group')!='dock')))
    from validate_thin_cleanup import prior_solid
    deltas=[];tops=[]
    for n,region in change_regions().items():
        m=ss[n].m;b=old(n);audit_m=prior_solid(n,m);plus=audit_m-b;minus=b-audit_m
        if later and n in later['changed_existing_ids']:
            from head_axial_retention import change_region
            region=region+change_region()
        deltas.append(dict(id=n,added_mm3=max(0,plus.volume()),removed_mm3=max(0,minus.volume()),outside_declared_region_mm3=max(0,(plus-region).volume())+max(0,(minus-region).volume())))
        top=topology(ss[n].v,ss[n].f);top.update(id=n,positive_components=sum(x.volume()>.001 for x in m.decompose()));tops.append(top)
    emit('local_solids',all(r['outside_declared_region_mm3']<.02 for r in deltas) and all(r['positive_components']==1 and not any(r[k] for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles']) for r in tops),'变化限制在确认部位；六个打印实体闭合连续',dict(deltas=deltas,topology=tops))
    fill=boxm(*q['camera_floor']['fill_bounds_mm']);missing=max(0,(fill-ss['Display_Frame'].m).volume())
    emit('camera_floor',missing<.005,'旧相机避让槽已填平，立柱外轮廓和光学基准保持',dict(missing_fill_mm3=missing,nominal_mast_depth_mm=3))
    # Four drive nuts remain at identical coordinates and enter before the
    # Load_Frame is installed. Stop checks establish geometric antirotation.
    paths=[]
    for n in q['drive_nuts']['ids']:
        s=ss[n];c=(s.lo+s.hi)/2;axis=np.array([0,1 if c[1]>0 else -1,0]);hits=[]
        for d in np.arange(.25,q['drive_nuts']['entry_travel_mm']+.01,.25):
            v=max(0,(s.m.translate((axis*d).tolist())^ss['Drive_Bridge'].m).volume())
            if v>.02:hits.append(dict(distance_mm=float(d),overlap_mm3=v))
        stops={}
        for sign in [-1,1]:
            stops[str(sign)]=None
            for angle in range(1,31):
                tr=Matrix.Translation(Vector(c))@Matrix.Rotation(math.radians(sign*angle),4,'Z')@Matrix.Translation(-Vector(c))
                if (s.m.transform(np.array(tr)[:3,:])^ss['Drive_Bridge'].m).volume()>.02:stops[str(sign)]=angle;break
        bearing_gaps=[]
        for dx,dy in [(1.5,0),(-1.5,0),(0,1.5),(0,-1.5)]:
            start=[c[0]+dx,c[1]+dy,s.hi[2]+.001];h=ss['Drive_Bridge'].m.ray_cast(start,[start[0],start[1],start[2]+5])
            bearing_gaps.append(5*h[0].distance+.001 if h else None)
        paths.append(dict(nut=n,direction=axis.tolist(),travel_mm=q['drive_nuts']['entry_travel_mm'],step_mm=.25,hits=hits,rotation_stops_deg=stops,bearing_face_gap_samples_mm=bearing_gaps))
    emit('drive_nut_entry',all(not r['hits'] and all(x is not None for x in r['rotation_stops_deg'].values()) and all(x is not None and x<.03 for x in r['bearing_face_gap_samples_mm']) for r in paths),'四枚轮驱螺母有侧向装入、止转和连续承压面',paths)
    rows={r['id']:r for r in json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears']};r=rows['Head_Yaw_Ear_0'];seat=r['seat_point_mm'][2];y=r['nut_center_mm'][1];roof=[]
    for x in [-1.65,1.65]:
        probe=boxm([x-.12,y-.12,seat-2.59],[x+.12,y+.12,seat-.01]);roof.append(max(0,(probe-ss['Pitch_Yoke'].m).volume()))
    upper=rows['Head_Pitch_Ear_0'];emit('head_nut_seats',max(roof)<.005 and upper['screw_length_mm']==8 and upper['screw_thread_projection_beyond_nut_mm']>=0,'头部两处螺母入口规整；后座2.6mm顶壁、上耳M2×8',dict(yaw_roof_missing_mm3=roof,yaw_roof_mm=2.6,pitch_screw_length_mm=upper['screw_length_mm'],pitch_nut_center_mm=upper['nut_center_mm'],pitch_thread_projection_mm=upper['screw_thread_projection_beyond_nut_mm'],entry_and_bearing_checks='prearrival_validation.json'))
    pn=q['pitch_nut'];z=upper['seat_point_mm'][2];x=pn['pocket_center_x_mm'];roof_probe=boxm([x-.2,-.2,z+2.101],[x+.2,.2,z+3.299]);roof_missing=max(0,(roof_probe-ss['Pitch_Yoke'].m).volume())
    floor_probe=boxm([x-.2,-.2,z-3.0],[x+.2,.2,z-2.101]);floor_remaining=max(0,(floor_probe^ss['Pitch_Yoke'].m).volume());stops={};nut=ss[pn['id']+'_Nut'];c=(nut.lo+nut.hi)/2
    for sign in [-1,1]:
        stops[str(sign)]=None
        for angle in range(1,31):
            tr=Matrix.Translation(Vector(c))@Matrix.Rotation(math.radians(sign*angle),4,'X')@Matrix.Translation(-Vector(c))
            if (nut.m.transform(np.array(tr)[:3,:])^ss['Pitch_Yoke'].m).volume()>.02:stops[str(sign)]=angle;break
    emit('pitch_seat_roof',roof_missing<.005 and floor_remaining<.005 and all(v is not None and v<=10 for v in stops.values()),'用户确认的上耳补充：1.2mm顶壁、取消薄底边，保持止转',dict(roof_mm=1.2,roof_missing_mm3=roof_missing,floor_remaining_mm3=floor_remaining,rotation_stops_deg=stops,hardware_moved=False))
    p=np.array(upper['ear_top_mm'])+[q['pitch_nut']['screw_head_height_mm']-.7,0,0];a=np.array([1,0,0])
    tool=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
    bench={n:s for n,s in ss.items() if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!='Head_Pitch_Ear_0_Screw'};hits=[]
    for angle in range(-120,121,2):
        tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));m=tool.transform(np.array(tr)[:3,:])
        for n,s in bench.items():
            v=max(0,(m^s.m).volume())
            if v>.02:hits.append(dict(angle=angle,id=n,mm3=v))
    longest=run=0
    for angle in range(-120,121,2):run=run+2 if not any(h['angle']==angle for h in hits) else 0;longest=max(longest,run)
    emit('upper_pitch_tool',longest>=60,'上侧M2×8内六角螺钉与1.5mm扳手的台面装配空间',dict(tool='PB210.1,5; long leg50mm, short leg14mm; conservative circumscribed shaft radius0.87mm',clear_sampled_span_deg=longest,hits=hits,prerequisite='Detached yoke; install pitch servo before yaw servo'))
    w=P['wheel_interface'];stack=[];walls=[]
    for side,sign in [('L',-1),('R',1)]:
        n='Wheel_Bearing_'+side+'_Inner';m=ss[n].m;b=old(n).translate([sign*q['wheel_bearing']['outward_shift_mm'],0,0]);rigid_delta=max(0,(m-b).volume())+max(0,(b-m).volume())
        sp=ss['Wheel_Spacer_'+side+'_0'];spans=sorted([sign*sp.lo[0],sign*sp.hi[0]])
        a=ss['Wheel_Axle_'+side].m;shoulder=max(0,(m.translate([-sign*.2,0,0])^a).volume())
        stack.append(dict(side=side,bearing_rigid_translation_difference_mm3=rigid_delta,inner_center_abs_x_mm=float(sign*(ss[n].lo[0]+ss[n].hi[0])/2),spacer_span_abs_x_mm=spans,spacer_length_mm=float(sp.hi[0]-sp.lo[0]),shoulder_interference_if_bearing_pushed_in_0_2_mm3=shoulder,shaft_shoulder_end_abs_x_mm=w['shoulder_end_abs_x_mm']))
        for host,dz in [('Drive_Bridge',5.7),('Motor_Retainer',-5.7)]:
            h=ss[host].m.ray_cast([sign*34.61,0,D['wheel_z']+dz],[sign*36.5,0,D['wheel_z']+dz]);thick=1.89*h[0].distance+.01 if h else None
            walls.append(dict(side=side,host=host,sampled_axial_lip_mm=thick))
    emit('bearing_stack',all(r['bearing_rigid_translation_difference_mm3']<.02 and abs(r['spacer_length_mm']-4.5)<.002 and r['shoulder_interference_if_bearing_pushed_in_0_2_mm3']>.1 for r in stack) and all(r['sampled_axial_lip_mm'] is not None and r['sampled_axial_lip_mm']>=1.249 for r in walls),'内轴承外移0.5mm；止挡1.25mm，轴肩和4.5mm隔套配套',dict(stack=stack,wall_samples=walls,outer_bearing_and_motor_and_hub='Exact unchanged signatures checked in scope',rotation_and_cartridge_removal='wheel_interface_validation.json'))

    names=set(ss);select=lambda *p:{n for n in names if n.startswith(p)}
    def collisions(m,fixed):
        bb=np.array(m.bounding_box());hits=[]
        for k in fixed:
            s=ss[k]
            if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
            v=max(0,(m^s.m).volume())
            if v>.02:hits.append(dict(part=k,mm3=v))
        return hits
    wheels=select('Tire_','Wheel_Hub','Wheel_End','Wheel_Spacer_L_1','Wheel_Spacer_R_1')
    head={n for n,s in ss.items() if s.group in ['yaw','pitch']}|select('Yaw_')
    lower=[];fixed=names-{'Body_Lower'}-select('Shell_Screw')-wheels
    for d in np.arange(0,120.01,.5):
        hs=collisions(ss['Body_Lower'].m.translate([0,0,-float(d)]),fixed)
        if hs:lower.append(dict(travel_mm=float(d),hits=hs));break
    tools=[]
    for n in sorted(select('Shell_Screw','Frame_Screw')):
        screw=ss[n];axis=np.array([0,0,-1]);xy=(screw.lo+screw.hi)[:2]/2;face=np.array([*xy,screw.lo[2]]);bench=names-{n}
        if n.startswith('Frame_'):bench-=head|wheels|{'Body_Lower'}|select('Shell_Screw')
        tested=[]
        for remove_battery in [False,True]:
            fixed=bench-(select('Battery') if remove_battery else set());hs=[]
            for label,shape in [('blade',axial(3,100,face+axis*50.03,axis)),('handle_reserve',axial(17.5,105,face+axis*152.53,axis))]:hs.extend([dict(kind=label,**h) for h in collisions(shape,fixed)])
            tested.append(dict(battery_removed=remove_battery,hits=hs))
        tools.append(dict(screw=n,status='PASS' if any(not r['hits'] for r in tested) else 'FAIL',trials=tested))
    moving=['Body_Upper']+sorted(select('Frame_Insert','Shell_Insert','Speaker','Rear_Interface','USB_Receptacle','Power_Switch'))
    removed=head|wheels|{'Body_Lower'}|set(P.get('head_axial_retention',{}).get('new_ids',[]))|select('Frame_Screw','Shell_Screw');fixed=names-set(moving)-removed;origin=Vector((0,0,D['body_z']));poses=[]
    sb=q['body_seam'];b=dict(tilt_x_deg=sb['service_tilt_deg'],initial_lift_mm=sb['service_lift_mm'],rear_translation_mm=sb['service_back_mm'],final_lift_mm=sb['service_final_lift_mm'])
    def pose(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
    for u in np.linspace(0,1,61):poses.append(('tilt_lift',float(u),pose(b['tilt_x_deg']*u,0,b['initial_lift_mm']*u)))
    for y in np.linspace(0,-b['rear_translation_mm'],57)[1:]:poses.append(('back',float(y),pose(b['tilt_x_deg'],y,b['initial_lift_mm'])))
    for z in np.arange(b['initial_lift_mm']+.5,b['final_lift_mm']+.01,.5):poses.append(('up',float(z),pose(b['tilt_x_deg'],-b['rear_translation_mm'],z)))
    hits=[]
    for phase,t,tr in poses:
        for n in moving:hits.extend([dict(phase=phase,parameter=t,moving=n,**h) for h in collisions(ss[n].m.transform(np.array(tr)[:3,:]),fixed)])
    emit('body_service',not lower and not hits and all(r['status']=='PASS' for r in tools),'配对移孔后的上下壳拆装与工具空间；扬声器和接口板随上壳取出',dict(lower_shell=dict(travel_mm=120,step_mm=.5,wheels_removed=True,hits=lower),upper_shell=dict(samples=len(poses),hits=hits,moving=moving,removed_first=sorted(removed),path=b),tools=tools,tool_basis='PB190.2-100/6 blade diameter6x100mm; conservative handle diameter35x105mm. Wires disconnected; hand access unqualified.'))
    walls=[]
    for n in ['Body_Upper','Body_Lower','Drive_Bridge']:
        s=ss[n];tri=s.v[s.f];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);ar=np.linalg.norm(cross,axis=1)/2;norm=cross/np.maximum(ar[:,None]*2,1e-15);indices=np.unique(np.searchsorted(np.cumsum(ar),np.linspace(0,ar.sum(),30002)[1:-1]));rays=[];tree=s.bvh()
        for i in indices:
            p=tri[i].mean(0);nv=norm[i];h,hn,j,d=tree.ray_cast(Vector(p-nv*.0001),Vector(-nv),300)
            if h is not None and j!=i and nv@np.array(hn)<-.95 and d>.02:rays.append((float(d+.0001),p.tolist()))
        rays.sort();walls.append(dict(id=n,opposed_surface_ray_count=len(rays),sampled_minimum_mm=rays[0][0] if rays else None,lowest=rays[:10]))
    emit('shell_walls',all(r['sampled_minimum_mm'] is not None and r['sampled_minimum_mm']>=1.19 for r in walls),'下壳与旧轮驱孔腔薄片消除；壳体和轮驱上座厚度抽查',walls)
    motion=json.loads((ROOT/'reports/head_motion.json').read_text());static=json.loads((ROOT/'reports/static_interference.json').read_text())
    emit('combined_motion',motion['poses']==130 and not motion['failures'] and not static['failed_pairs'],'六项组合后130个头部姿态及静态实体复核',dict(poses=motion['poses'],motion_collisions=motion['failures'],static_collisions=static['failed_pairs'],exact_purchased_fit='BLOCKED: declared vendor connector proxies and unmeasured interfaces remain'))
    report.update(status='FAIL' if failed else 'PASS',failed=failed,physical_strength='NOT_TESTED',manufacturing_release=False,part_count_change=0,issue7='BLOCKED; delegated to hardware thread '+q['hardware_task_id'])
    save_json(ROOT/'reports/assembly_issue_validation.json',report)
    print('SIX_ISSUES_VALIDATED',report['status'],failed,flush=True)
