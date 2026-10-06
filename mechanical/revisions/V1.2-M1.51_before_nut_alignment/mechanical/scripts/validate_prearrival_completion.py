"""Verify accepted M1.39 scope, four nut seats, bench entry and aperture rays."""
from common import *
from validate_head_cleanup import geometry_record
from prearrival_completion import ear_change_region,aperture_region
from optics_mount import camera_transform,camera_pupil

def validate_prearrival_completion(solids,Solid,iv,check):
    s=P.get('prearrival_completion',{})
    if not s.get('enabled'):return
    base=json.loads((PROJECT/s['baseline_geometry']).read_text());now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if n in base['parts'] and now[n]!=base['parts'][n] and now[n]['group']!='dock');added=sorted(set(now)-set(base['parts']));retired=sorted(set(base['parts'])-set(now))
    results={};failed=[]
    def emit(n,ok,label,data):
        results[n]=data
        if not ok:failed.append(n)
        check('prearrival_'+n,'PASS' if ok else 'FAIL',label,data,'Current actual solids and immutable M1.38 mesh/transform records; finite nominal checks only.')
    scope={'changed':changed,'added':added,'retired':retired,'dock_note':'Maintenance cradle presentation position excluded; robot-part scope checked exactly.', 'print_count':sum(o.get('category')=='PRINTABLE' for o in parts() if o.get('group')!='dock')}
    scope['subsequent_changes_checked_separately']=sorted(declared_mount_root_changes())
    expected=(set(s['changed_existing_ids'])|declared_mount_root_changes())-set(s['new_ids'])-declared_retention_additions()
    emit('scope',set(changed)==expected and set(added)==set(s['new_ids'])|declared_retention_additions() and set(retired)==set(s['retired_ids']) and scope['print_count']==P['part_consolidation']['target_robot_print_count'],'M1.39耳座与相机孔范围核对；后续修复单独检查',scope)
    delta=[]
    for name,region in [('Pitch_Yoke',ear_change_region()),('Head_Front',aperture_region())]:
        if P.get('interface_completion',{}).get('enabled'):
            from interface_completion import change_regions
            region+=change_regions().get(name,manifold.Manifold())
        b=base[name];old=manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)));new=solids[name].m
        from validate_thin_cleanup import prior_solid
        audit_new=prior_solid(name,new);plus=audit_new-old;minus=old-audit_new
        delta.append(dict(id=name,added_mm3=max(0,plus.volume()),removed_mm3=max(0,minus.volume()),outside_approved_region_mm3=max(0,(plus-region).volume())+max(0,(minus-region).volume()),positive_components=sum(x.volume()>.001 for x in new.decompose())))
    emit('local_solids',all(x['outside_approved_region_mm3']<.02 and x['positive_components']==1 for x in delta),'孔窝与壳孔局部范围、连续实体检查',delta)
    rows=json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears'];paths=[];seats=[];clearance=[]
    for row in rows:
        name=row['id']+'_Nut';axis=np.array([0,0,-1.]) if row['axis']=='Z' else np.array([-1.,0,0]);n=solids[name];hits=[]
        entry=np.array(row.get('nut_entry_direction',axis.tolist()))
        for d in np.arange(.25,12.01,.25):
            v=max(0,(n.m.translate((entry*d).tolist())^solids['Pitch_Yoke'].m).volume())
            if v>.02:hits.append({'travel_mm':float(d),'volume_mm3':v})
        paths.append({'id':name,'direction':entry.tolist(),'travel_mm':12,'step_mm':.25,'collisions':hits,'prerequisite':'Detached yoke; nuts inserted before servos and pitch cradle.'})
        bearing=np.array(row['nut_bearing_mm']);out=-axis
        tr=Matrix.Translation(Vector(bearing+out*.03))@Vector(out).to_track_quat('Z','Y').to_matrix().to_4x4()
        ring=manifold.Manifold.cylinder(.2,1.9,1.9,64)-manifold.Manifold.cylinder(.2,1.25,1.25,64)
        probe=ring.transform(np.array(tr)[:3,:]);missing=max(0,(probe-solids['Pitch_Yoke'].m).volume())
        seats.append({'id':name,'missing_bearing_ring_mm3':missing,'projection_beyond_nut_mm':row['screw_thread_projection_beyond_nut_mm']})
        for ident in [name,row['id']+'_Screw']:
            for other,a in solids.items():
                if other==ident:continue
                v=iv(solids[ident],a)
                if v>.02:clearance.append({'a':ident,'b':other,'mm3':v})
    emit('nut_seats_and_entry',not any(p['collisions'] for p in paths) and all(r['missing_bearing_ring_mm3']<.005 and r['projection_beyond_nut_mm']>=0 for r in seats) and not clearance,'穿栓螺母承压、螺纹穿出及台面装入路径',{'paths':paths,'bearing_rings':seats,'static_overlaps':clearance})
    rot=np.array(camera_transform().to_3x3())@np.array([[1,0,0],[0,0,1],[0,-1,0]]);p=np.array(camera_pupil());blocked=[];count=0
    for h in np.linspace(-P['camera']['assumed_hfov_deg']/2,P['camera']['assumed_hfov_deg']/2,31):
        for v in np.linspace(-P['camera']['assumed_vfov_deg']/2,P['camera']['assumed_vfov_deg']/2,25):
            count+=1;d=rot@np.array([math.tan(math.radians(h)),math.tan(math.radians(v)),1]);d/=np.linalg.norm(d)
            if solids['Head_Front'].bvh().ray_cast(Vector(p),Vector(d),200)[0] is not None:blocked.append([float(h),float(v)])
    q=s['camera_aperture'];kh=math.sqrt(2)*math.tan(math.radians(P['camera']['assumed_hfov_deg']/2));kv=math.sqrt(2)*math.tan(math.radians(P['camera']['assumed_vfov_deg']/2))
    pts=[[math.cos(a)*(q['pupil_margin_mm']+kh*w),math.sin(a)*(q['pupil_margin_mm']+kv*w),w] for w in [0,q['length_mm']] for a in np.linspace(0,2*math.pi,q['segments'],endpoint=False)]
    b=base['Head_Front'];old_front=manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)))
    witness=Solid(bpy.data.objects[PREFIX+'Integrated_Face_Region']).m
    removed_bezel=max(0,((old_front-solids['Head_Front'].m)^witness).volume())
    emit('camera_rays',not blocked and removed_bezel<.001,'连续椭圆扩口775条名义视线与黑色边圈保留',{'rays':count,'blocked':blocked,'removed_bezel_mm3':removed_bezel,'FOV':'ASSUMED; physical lens calibration pending'})
    material=[o.name.removeprefix(PREFIX) for o in parts(True) if o.get('category')=='PRINTABLE' and o.get('selected_print_material')!='PA12']
    emit('material',not material,'首轮全部打印件标记为PA12，质量使用完整建模体积',{'wrong_material_ids':material,'density_basis':s['printing']['density_basis'],'IMU_native_model_unchanged':now['Body_IMU']==base['parts']['Body_IMU']})
    results.update(revision=P['revision'],status='FAIL' if failed else 'PASS',failed=failed,strength='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/prearrival_validation.json',results)
