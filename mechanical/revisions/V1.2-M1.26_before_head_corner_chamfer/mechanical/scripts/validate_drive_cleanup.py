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
    extra=sorted(set(changed)-set(s['changed_print_ids']));removed=sorted(set(baseline)-set(now))
    unchanged=not extra and not removed
    check('drive_cleanup_preserved_datums','PASS' if unchanged else 'FAIL','轮驱两件打印结构修改；电机、金属传动、全部紧固件与头部保持原位',
          {'changed':changed,'unexpected':extra,'removed':removed,'baseline':s['baseline_revision']},
          'World vertex and triangle hashes against immutable M1.25; every part except the three declared prints must match.')
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
