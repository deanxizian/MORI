"""M1.38 exact scope, real solid fastening, bearing material and bench access.

All sizes are nominal trial interfaces. These checks do not qualify thread
engagement, heat-set insertion, printing strength or purchased tolerances.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate_head_cleanup import geometry_record
from optics_mount import display_transform
import hashlib

def validate_readiness_completion(solids,Solid,iv,check):
    s=P.get('readiness_completion',{})
    if not s.get('enabled'):return
    result={'revision':P['revision']};fail=[]
    def emit(key,ok,title,data,method):
        result[key]=data
        if not ok:fail.append(key)
        check('readiness_'+key,'PASS' if ok else 'FAIL',title,data,method)
    def volume(m):return max(0,float(m.volume()))
    def cylinder(p,axis,r,length):
        tr=Matrix.Translation(Vector(p))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
        return manifold.Manifold.cylinder(length,r,r,64).transform(np.array(tr)[:3,:])
    def ringprobe(p,axis,rout,rin,length):
        return cylinder(p,axis,rout,length)-cylinder(p,axis,rin,length)
    def cube(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)
    def hits(m,ids,tol=.01):
        bb=np.array(m.bounding_box());out=[]
        for n in ids:
            a=solids[n]
            if np.any(bb[3:]<a.lo) or np.any(a.hi<bb[:3]):continue
            v=volume(m^a.m)
            if v>tol:out.append({'part':n,'volume_mm3':v})
        return out
    base=json.loads((PROJECT/s['baseline_geometry']).read_text())
    now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    added=sorted(set(now)-set(base['parts']));retired=sorted(set(base['parts'])-set(now))
    changed=sorted(n for n in now if n in base['parts'] and now[n]!=base['parts'][n])
    snap=json.loads((ROOT/'revisions/V1.2-M1.37_before_readiness_completion/snapshot.json').read_text())
    contract_hash=next(r['sha256'] for r in snap['files'] if r['path']=='contracts/components.json')
    contract_same=hashlib.sha256((PROJECT/'contracts/components.json').read_bytes()).hexdigest()==contract_hash
    scope={'changed_existing':changed,'added':added,'retired':retired,'hardware_contract_unchanged':contract_same,
           'baseline':base['revision'],'print_count':sum(o.get('category')=='PRINTABLE' for o in parts() if o.get('group')!='dock')}
    current=P.get('prearrival_completion',{}) if P.get('prearrival_completion',{}).get('enabled') else {}
    expected_changed=set(s['changed_existing_ids'])|set(current.get('changed_existing_ids',[]))|declared_mount_root_changes()
    expected_added=set(s['new_ids'])|set(current.get('new_ids',[]))|declared_retention_additions()
    expected_changed-=expected_added
    expected_retired=set(s['retired_ids'])|set(current.get('retired_ids',[]))
    hardware_preserved=contract_same
    if P.get('head_axial_retention',{}).get('enabled'):
        snap=PROJECT/Path(P['head_axial_retention']['baseline_blend']).parents[1]/'hardware_hashes.json'
        hashes=json.loads(snap.read_text())
        hardware_preserved=hashlib.sha256((PROJECT/'contracts/components.json').read_bytes()).hexdigest()==hashes['contracts/components.json']
        scope['hardware_contract_unchanged_since_current_task_start']=hardware_preserved
        scope['historical_contract_change_note']='Received newer hardware contract is separate from immutable geometry; main native-board sources remain unchanged.'
    if P.get('camera_cam_completion',{}).get('enabled'):
        receipt=json.loads((PROJECT/P['camera_cam_completion']['approval_record']).read_text())
        expected_hash=receipt['protected_hardware']['contracts/components.json']
        hardware_preserved=hashlib.sha256((PROJECT/'contracts/components.json').read_bytes()).hexdigest()==expected_hash
        scope['hardware_contract_unchanged_since_current_task_start']=hardware_preserved
        scope['current_task_start_receipt']=P['camera_cam_completion']['approval_record']
    scope['unexpected_changed']=sorted(set(changed)-expected_changed)
    scope['declared_but_unchanged']=sorted(expected_changed-set(changed))
    emit('scope',set(changed)==expected_changed and set(added)==expected_added
         and set(retired)==expected_retired and hardware_preserved,'头部紧固与后续已批准修改范围；采购件基准保持',scope,
         'Every part world/local mesh and transform SHA vs immutable M1.37; exact declared additions/retirements. Contract hash is separate from current source provenance checks.')
    geom=json.loads((ROOT/'reports/readiness_geometry.json').read_text())
    tr=display_transform();hz=D['head_z'];fy=D['face_y'];q=s['head_shell']
    region={}
    region['Head_Front']=cylinder(tr@Vector((0,fy-1,hz)),tr.to_3x3()@Vector((0,1,0)),31.05,2)
    if current:
        from prearrival_completion import aperture_region
        region['Head_Front']+=aperture_region()
    region['Pitch_Cradle']=manifold.Manifold()
    if P.get('mount_root_cleanup',{}).get('enabled'):
        from validate_mount_roots import cam_change_region
        region['Pitch_Cradle']+=cam_change_region()
    for sign in [-1,1]:
        x,y=head_shell_mount_xy_mm(sign)
        region['Head_Front']+=cylinder((x,y,hz+17),(0,0,1),q['counterbore_radius_mm']+.01,65)
        region['Pitch_Cradle']+=cylinder((x,y,hz+q['insert_top_from_head_mm']-q['insert_length_mm']-.21),(0,0,1),q['pilot_radius_mm']+.01,5.5)
    l=s['lcd'];bottom=hz+l['original_crossbar_bottom_from_head_mm'];top=hz+l['crossbar_top_from_head_mm']
    oldrear=l['crossbar_center_y_mm']-l['crossbar_depth_mm']/2;rear=oldrear+l['crossbar_forward_shift_mm'];front=rear+l['crossbar_depth_mm']
    region['Display_Frame']=cube([-l['crossbar_width_mm']/2-.02,oldrear-.02,bottom-l['lower_crossbar_extension_mm']-.02],[l['crossbar_width_mm']/2+.02,45.01,top+.02])
    region['Display_Frame']+=cube([-8.01,oldrear-.01,hz+l['mast_connection_bottom_from_head_mm']-.01],[8.01,front+.01,hz+l['mast_connection_top_from_head_mm']+.01])
    if P.get('display_frame_simplification',{}).get('enabled'):
        from display_frame_simplification import change_region
        region['Display_Frame']+=change_region()
    for row in geom['LCD']:
        axis=np.array(row['axis']);p=np.array(row['post_face_mm']);f=np.array(row['head_bearing_mm'])
        region['Display_Frame']+=cylinder(p-axis*45,axis,s['lcd']['clearance_radius_mm']+.01,60.1)
        region['Display_Frame']+=cylinder(f-axis*20.01,axis,s['lcd']['spotface_radius_mm']+.01,20.02)
    rear_record=json.loads((ROOT/'reports/rear_interface_geometry.json').read_text());z=rear_record['switch_actuator_axis_z_mm']
    region['Body_Upper']=cube([-3.01,-91.01,z-1.61],[3.01,-60.99,z+1.61])
    if P.get('interface_completion',{}).get('enabled'):
        from interface_completion import change_regions
        for n,m in change_regions().items():region[n]=region.get(n,manifold.Manifold())+m
    deltas=[]
    for n in s['changed_existing_ids']:
        b=base[n];old=manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)))
        from validate_camera_cam import prior_solid
        new=solids[n].m;audit_new=prior_solid(n,new);plus=audit_new-old;minus=old-audit_new
        deltas.append({'part':n,'added_mm3':volume(plus),'removed_mm3':volume(minus),
            'outside_local_region_mm3':volume(plus-region[n])+volume(minus-region[n]),
            'positive_components':sum(v.volume()>.001 for v in new.decompose())})
    emit('local_solids',all(r['outside_local_region_mm3']<.015 and r['positive_components']==1 for r in deltas),
         '面圈与原壳连为一体，孔和沉孔改动限于已确认位置',deltas,'Exact manifold symmetric difference restricted to optical rim, existing hole axes and retired switch opening; positive solid components counted.')
    check('readiness_LCD_thread_mating','BLOCKED','LCD原厂CAD含内螺纹；螺钉啮合段仅检查牙底代理，螺纹配合和有效拧入深度待实物',s['lcd']['thread_validation'])
    new_hits=[]
    for n in s['new_ids']:
        own=next((r['host'] for r in P.get('interface_completion',{}).get('inserts',[]) if r['id']==n),None)
        hh=hits(solids[n].m,[a for a in solids if a!=n and a!=own])
        if hh:new_hits.append({'new':n,'hits':hh})
    emit('new_hardware_clearance',not new_hits,'新增头部紧固件与装配实体的名义干涉检查',new_hits,'Closed solids, with declared root-only proxies inside the three threaded LCD cavities. Full thread crest mating remains BLOCKED; other contacts do not waive volume overlap.')
    seats=[];tools=[];insertion=[];engagement=[]
    for row in geom['LCD']+geom['head']:
        n=row['id'];f=np.array(row['head_bearing_mm']);axis=np.array(row['axis']);lcd=n.startswith('LCD_');seam=n.startswith('Head_Seam_')
        target='Display_Frame' if lcd else 'Head_Rear' if seam else 'Head_Front'
        bearing=ringprobe(f+axis*.03,axis,1.8,1.25,.2)
        seats.append({'screw':n,'bearing_part':target,'bearing_probe_thickness_mm':.2,'missing_ring_material_mm3':volume(bearing-solids[target].m)})
        # LCD screws are installed on the detached optical fork, before camera,
        # servos and cradle. Shell screws use access on the assembled head.
        obstacles=['Display_Frame','Display_PCB'] if lcd else list(solids)
        obstacles=[a for a in obstacles if a!=n]
        driver=cylinder(f-axis*1.6,-axis,1.5,35)
        tools.append({'screw':n,'diameter_mm':3,'length_mm':35,'bench_only':lcd,'hits':hits(driver,obstacles)})
        path=[]
        for d in np.arange(0,25.01,.5):
            hh=hits(solids[n].m.translate((-axis*d).tolist()),obstacles)
            if hh:path.append({'distance_mm':float(d),'hits':hh})
        insertion.append({'screw':n,'travel_mm':25,'step_mm':.5,'failures':path})
        engagement.append({'screw':n,'nominal_engagement_mm':row.get('engagement_mm',row.get('trial_engagement_mm')),'approved_thread_depth':'NOT_TESTED'})
    emit('bearing_and_tool_access',all(r['missing_ring_material_mm3']<.005 for r in seats) and not any(r['hits'] for r in tools) and not any(r['failures'] for r in insertion),
         '头部螺钉座下有连续承压材料，螺钉与直杆工具可达',{'bearing_rings':seats,'tools':tools,'screw_insertion':insertion,'engagement':engagement},
         'Material-volume probes plus straight3mm rods and51 screw insertion samples. LCD fastens on detached fork; driver handles, heat-set tool, torque and actual threads remain untested.')
    closed=[]
    for row in geom['LCD'][1:]:
        x=row['post_face_mm'][0];probe=cube([x-2,rear+.1,bottom-l['lower_crossbar_extension_mm']+.05],[x+2,front-.1,bottom-l['lower_crossbar_extension_mm']+1.25])
        rays=solids['Display_Frame'].m.ray_cast([x,rear+.1,205],[x,rear+.1,215]);zs=sorted(h.position[2] for h in rays)
        closed.append({'screw':row['id'],'missing_bottom_strip_mm3':volume(probe-solids['Display_Frame'].m),'surface_hits_z_mm':zs,'sample_bottom_wall_mm':zs[1]-zs[0] if len(zs)>=2 else None})
    emit('LCD_closed_counterbores',all(r['missing_bottom_strip_mm3']<.005 and r['sample_bottom_wall_mm'] is not None and r['sample_bottom_wall_mm']>1.4 for r in closed),'整条横板下延4mm、前移3mm，沉孔下沿连续且无开口缺口',closed,'Actual ray intersections plus full bottom-strip volume; local wall only, no strength proof.')
    lug=[]
    for sign in [-1,1]:
        x,y=head_shell_mount_xy_mm(sign);bottom=hz+q['insert_top_from_head_mm']-q['insert_length_mm']
        shell=ringprobe((x,y,bottom+.2),(0,0,1),2.25,1.55,q['insert_length_mm']-.4)
        r=next((v for v in P.get('interface_completion',{}).get('inserts',[]) if v['id']=='Head_Cradle_Insert_'+str(sign)),None)
        if r:
            bottom=r['entry_mm'][2]-r['length_mm']-.2
            shell=ringprobe((x,y,bottom+.1),(0,0,1),2.35,r['pilot_mm']/2+.05,r['length_mm']-.2)
        lug.append({'side':sign,'axis_mm':[x,y],'radial_material_sample_mm':.7,'missing_mm3':volume(shell-solids['Pitch_Cradle'].m)})
    emit('lug_material',all(r['missing_mm3']<.005 for r in lug),'原凸台孔轴保留，嵌件孔周有连续材料',lug,'Full annulus containment over3.6mm insert length; no insert pullout or print-strength inference.')
    closure=[]
    for name,direction,omit in [('Head_Front',[0,1,0],{'Head_Rear'}),('Head_Rear',[0,-1,0],set())]:
        obstacles=[n for n in solids if n!=name and n not in omit and not n.startswith(('Head_Cradle_Screw_','Head_Seam_Screw_','Head_Seam_Insert_'))]
        path=[]
        for d in np.arange(0,35.01,.5):
            hh=hits(solids[name].m.translate((np.array(direction)*d).tolist()),obstacles)
            if hh:path.append({'distance_mm':float(d),'hits':hh})
        closure.append({'part':name,'direction':direction,'travel_mm':35,'step_mm':.5,'failures':path})
    emit('shell_paths',not any(r['failures'] for r in closure),'头壳松开螺钉后的分离与合拢路径',closure,
         '71 rigid samples per shell, screws removed first. Rear shell removed before front shell; no wiring or flexible seal included.')
    front=bpy.data.objects[PREFIX+'Head_Front'];dark=sum(f.material_index==1 for f in front.data.polygons)
    optical={'retired_parts_absent':not set(s['retired_ids'])&set(solids),'rim_black_polygons':dark,
             'original_LCD_unchanged':now['Display_PCB']==base['parts']['Display_PCB'],
             'camera_package_unchanged':all(now[n]==base['parts'][n] for n in ['Camera_PCB','Camera_Lens'])}
    emit('optical_simplification',all(v for k,v in optical.items()),'取消额外片件与独立面圈，保留原厂屏幕盖板和独立相机开口',optical,'Retired physical objects absent, integral shell polygon finish, exact vendor geometry hashes.')
    old=base['Body_Upper'];old=manifold.Manifold(manifold.Mesh64(np.array(old['vertices_mm']),np.array(old['triangles'],dtype=np.uint64)))
    patch=solids['Body_Upper'].m-old
    usb_region=cube([-9,-92,rear_record['USB_axis_z_mm']-3.3],[9,-60,rear_record['USB_axis_z_mm']+3.3])
    later=manifold.Manifold()
    if P.get('interface_completion',{}).get('enabled'):
        from interface_completion import change_regions
        later=change_regions()['Body_Upper']
    sw={'filled_volume_mm3':volume(patch),'USB_region_change_mm3':volume((patch-later)^usb_region),
        'native_SW1_preserved':now['Power_Switch']==base['parts']['Power_Switch'],
        'electrical_handoff':'SW1 deletion and power-cut/emergency-stop design must be confirmed by electrical owner before board/source release.'}
    emit('rear_switch_shell',volume(patch)>.1 and sw['USB_region_change_mm3']<.01 and sw['native_SW1_preserved'],
         '机械取消后开关孔；Type-C与收到的原生接口板保持',sw,'Exact shell difference and source-geometry comparison. Native SW1 kept visibly pending electrical revision, not a working switch.')
    check('readiness_physical_interfaces','NOT_TESTED','新增紧固方案仍需试打与实物螺纹深度、嵌件配合验证',{'LCD_screws_mm':s['lcd']['screw_lengths_mm'],'head_cradle_screws_mm':[12,12],'head_seam_screws_mm':[16,16],'release':False})
    result.update(status='FAIL' if fail else 'PASS',failed_sections=fail,manufacturing_release=False)
    save_json(ROOT/'reports/readiness_validation.json',result)

if __name__=='__main__':
    from validate import Solid,intersect_volume,check,CHECKS
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
    assembled();ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
    validate_readiness_completion(ss,Solid,intersect_volume,check)
    save_json(ROOT/'reports/readiness_local_checks.json',{'revision':P['revision'],'checks':CHECKS})
