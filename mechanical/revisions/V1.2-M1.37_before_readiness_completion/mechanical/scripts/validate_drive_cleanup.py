"""Datums, flat faces, motor floors and clamp bearing material on actual solids."""
from common import *
from validate_head_cleanup import geometry_record

def validate_drive_cleanup(solids,Solid,iv,check):
    s=P.get('drive_print_cleanup',{})
    if not s.get('enabled'):return
    report=json.loads((ROOT/'reports/drive_print_cleanup.json').read_text())
    baseline=json.loads((PROJECT/s['baseline_geometry']).read_text())['parts']
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=[n for n in now if n not in baseline or now[n]!=baseline[n]]
    head=P.get('head_print_cleanup',{})
    later_head={'Pitch_Cradle'} if head.get('cradle_rear_corner_chamfer_mm',0)>0 or head.get('cradle_rear_profile')=='folded_u' else set()
    from validate_head_servo import declared_changes,declared_retirements
    later_head|=declared_changes()
    extra=sorted(set(changed)-set(s['changed_print_ids'])-later_head);removed=sorted(set(baseline)-set(now))
    unchanged=not extra and not (set(removed)-declared_retirements())
    check('drive_cleanup_preserved_datums','PASS' if unchanged else 'FAIL','轮驱既有修改范围核对；本轮头部变化另行验证',
          {'changed':changed,'unexpected':extra,'removed':removed,'baseline':s['baseline_revision'],'later_head_corner_change_checked_separately':sorted(later_head),'head_corner_baseline':head.get('corner_baseline_revision')},
          'World vertex and triangle hashes against immutable M1.25; Only the two declared drive prints plus the separately audited rear head corners may differ.')
    connected=[]
    for n in s['reviewed_print_ids']:
        pieces=[x for x in solids[n].m.decompose() if abs(x.volume())>.01]
        connected.append({'part':n,'positive':sum(x.volume()>0 for x in pieces),'cavities':sum(x.volume()<0 for x in pieces)})
    contiguous=all(x['positive']==1 and x['cavities']==0 for x in connected)
    check('drive_cleanup_continuous_solids','PASS' if contiguous else 'FAIL','上座、底盖与主托板各为连续闭合实体',connected,'Actual manifold decomposition; no strength certification.')
    wall=[];bad=[];drive=solids['Drive_Bridge']
    hx,hy=[x/2 for x in s['central_outer_xy_mm']]
    for sign in [-1,1]:
        for x in [-20,0,20]:
            for z in [48,55,61]:
                hits=drive.m.ray_cast([x,sign*50,z],[x,0,z]);actual=abs(hits[0].position[1]) if hits else None
                row={'surface':'end','sign':sign,'x_mm':x,'z_mm':z,'abs_face_mm':actual};wall.append(row)
                if actual is None or abs(actual-hy)>.002:bad.append(row)
        for y in [-20,-15,15,20]:
            for z in [48,57,64]:
                hits=drive.m.ray_cast([sign*60,y,z],[0,y,z]);actual=abs(hits[0].position[0]) if hits else None
                row={'surface':'side','sign':sign,'y_mm':y,'z_mm':z,'abs_face_mm':actual};wall.append(row)
                if actual is None or abs(actual-hx)>.002:bad.append(row)
    # The cap top must meet square case corners without the small steps
    # caused by carrying the lower shell chamfer up the entire cap height.
    for sx in [-1,1]:
        for sy in [-1,1]:
            for axis in ['end','side']:
                z=s['case_cap_split_z_mm']-1
                start=[sx*(hx-1),sy*50,z] if axis=='end' else [sx*60,sy*(hy-1),z]
                end=[start[0],0,z] if axis=='end' else [0,start[1],z]
                k=1 if axis=='end' else 0;expected=hy if axis=='end' else hx
                hits=solids['Motor_Retainer'].m.ray_cast(start,end);actual=abs(hits[0].position[k]) if hits else None
                row={'surface':'cap_upper_'+axis,'signs':[sx,sy],'z_mm':z,'abs_face_mm':actual};wall.append(row)
                if actual is None or abs(actual-expected)>.002:bad.append(row)
    check('drive_cleanup_flat_faces','FAIL' if bad else 'PASS','轮驱外侧壁平齐，无锁紧柱凸条与顶沿台阶',{'rays':wall,'failures':bad},'Actual ray intersections away from functional bearing/output openings and nut pockets.')
    floors=[]
    for side in ['L','R']:
        a=solids['Drive_Motor_'+side];center=(a.lo+a.hi)/2
        for dx,dy in [(-6,-10),(0,0),(6,10)]:
            x,y=center[0]+dx,center[1]+dy;hits=solids['Motor_Retainer'].m.ray_cast([x,y,44.2],[x,y,34])
            actual=float(hits[0].position[2]) if hits else None
            floors.append({'motor':side,'x_mm':float(x),'y_mm':float(y),'floor_z_mm':actual})
    clamp=[]
    for i,(x,y) in enumerate(P['wheel_interface']['clamp_bolt_xy_mm']):
        # Closed material immediately above the head seat, and immediately
        # below the nut. Excludes clearance bore and avoids exact surfaces.
        for target,z in [('Motor_Retainer',40.5),('Drive_Bridge',61.0)]:
            o=ring('clamp_backing_probe',(x,y,z),2.6,1.75,1.6);a=Solid(o)
            missing=max(0,(a.m-solids[target].m).volume());clamp.append({'index':i,'part':target,'tested_thickness_mm':1.6,'missing_mm3':missing})
            SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
    bearing_ok=all(x['floor_z_mm'] is not None and abs(x['floor_z_mm']-s['cap_motor_floor_z_mm'])<.002 for x in floors) and all(x['missing_mm3']<.005 for x in clamp)
    check('drive_cleanup_contact_material','PASS' if bearing_ok else 'FAIL','原电机软垫平面与M3锁紧承压材料保留',{'motor_floors':floors,'clamp_backing':clamp},'Solid rays and material-volume probes; retained pad positions checked by hashes. No preload or print-strength claim.')
    report.update(status='PASS' if unchanged and contiguous and not bad and bearing_ok else 'FAIL',changed_geometry=changed,
                  unexpected_changes=extra,connected=connected,wall_failures=bad,motor_floors=floors,clamp_backing=clamp,
                  related_checks=['wheel_drive_service_sequence','complete_wheel_drive_sweep','wheel_cap_tools','wide_battery_tray_flat_sides','static_rigid_solids'])
    save_json(ROOT/'reports/drive_cleanup_validation.json',report)
    validate_cap_edge_cleanup(solids,check)


def validate_cap_edge_cleanup(solids,check):
    s=P.get('drive_edge_cleanup',{})
    if not s.get('enabled'):return
    base=json.loads((PROJECT/s['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n))
    retired=sorted(set(base['parts'])-set(now))
    r=base['Motor_Retainer'];old=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)))
    new=solids['Motor_Retainer'].m;removed=old-new;added=new-old
    q=P['drive_print_cleanup'];hx=q['central_outer_xy_mm'][0]/2;mid=q['bearing_bar_bottom_transition_x_mm'];hy=q['bearing_bar_depth_mm']/2
    z0=q['bearing_bar_bottom_inner_z_mm'];z1=q['bearing_bar_bottom_outer_z_mm']
    region=manifold.Manifold();regions=[]
    for side in s['sides']:
        sign=1 if side=='R' else -1;x0,x1=sorted([sign*hx,sign*mid]);lo=[x0,-hy,z0];hi=[x1,hy,z1]
        region+=manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
        regions.append({'side':side,'bounds_xyz_mm':list(zip(lo,hi))})
    positive=lambda m:max(0.,m.volume())
    outside=positive(removed-region);remaining=positive(new^region)
    expected=positive(old^region);pieces=[v for v in new.decompose() if abs(v.volume())>.001]
    # Explicitly protect the curved bearing seats and their neighboring walls.
    seats=[];w=P['wheel_interface']
    for sign in [-1,1]:
        for x in w['bearing_centers_abs_x_mm']:
            envelope=manifold.Manifold.cylinder(w['bearing_width_mm']+2,7.5,7.5,96).rotate([0,90,0]).translate([sign*x-(w['bearing_width_mm']+2)/2,0,D['wheel_z']])
            seats.append({'x_mm':sign*x,'changed_seat_region_mm3':positive(removed^envelope)+positive(added^envelope)})
    left=manifold.Manifold.cube([100,100,100]).translate([-100,-50,0])
    tol=s['local_volume_tolerance_mm3']
    later=declared_speaker_changes()
    ok=set(changed)-later=={'Motor_Retainer'} and not retired and len(now)==len(base['parts']) and positive(added)<tol and outside<tol and remaining<tol and abs(positive(removed)-expected)<tol and len(pieces)==1 and pieces[0].volume()>0 and all(v['changed_seat_region_mm3']<tol for v in seats)
    result={'revision':P['revision'],'baseline_revision':base['revision'],'status':'PASS' if ok else 'FAIL','changed_parts':changed,'retired_parts':retired,'part_count_delta':len(now)-len(base['parts']),'later_speaker_changes_checked_separately':sorted(later),
            'regions':regions,'removed_volume_mm3':positive(removed),'expected_region_volume_mm3':expected,'added_volume_mm3':positive(added),
            'change_outside_approved_region_mm3':outside,'remaining_lip_volume_mm3':remaining,'connected_positive_solids':sum(v.volume()>0 for v in pieces),
            'left_side_difference_mm3':positive(removed^left)+positive(added^left),'protected_bearing_seats':seats,'new_parts':0,'new_fasteners':0,
            'method':'All-part geometry/matrix fingerprints versus immutable M1.35; actual closed-solid set differences, curved-seat neighborhood protection and component decomposition.','physical_strength':'NOT_TESTED','manufacturing_release':False}
    save_json(ROOT/'reports/cap_edge_cleanup_validation.json',result)
    check('cap_edge_local_cleanup',result['status'],'仅移除圈出的右侧底盖窄边；其余零件、轴承座与五金保持',result,result['method'])
