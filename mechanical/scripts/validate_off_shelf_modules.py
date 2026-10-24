"""Independent saved-main adoption, source fidelity and affected assembly checks."""
import hashlib, time
from common import *
from off_shelf_modules import cylinder, hexagon


def raw_solid(row):
    return manifold.Manifold(manifold.Mesh64(np.array(row['vertices'],dtype=float,order='C'),
                                           np.array(row['triangles'],dtype=np.uint64,order='C')))


def scope_check(ss):
    q=P['off_shelf_modules'];path=PROJECT/q['baseline'];base=json.loads(path.read_text());root=path.parent
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha(path)==q['baseline_sha256']
    for f,h in base['reference_files'].items():assert sha(root/f)==h,f
    dock=json.loads((root/'evaluated_dock_reference.json').read_text())
    assert sha(dock['source_file'])==dock['source_file_sha256'] and dock['preserved_main_sha256']==base['source_main_sha256']
    actual={o.name.removeprefix(PREFIX):o for o in parts()};errors=[];moved=[];same=0
    new=set(q['modules'][k]['id'] for k in q['modules'])
    new|={f'{prefix}_{kind}_{i}' for prefix,num in [('BMI323',2),('Buck6V',2),('UPS_Direct',4)] for kind in ['Screw','Nut'] for i in range(num)}
    changed_prints={'Load_Frame'}
    if P.get('dc_inlet_trial',{}).get('enabled'):
        new.update(P['dc_inlet_trial']['reference_ids']);changed_prints.add('Body_Rear')
    retired=set(q['retired_ids'])
    controls=P.get('ups_rear_controls',{})
    if controls.get('enabled'):
        retired.update(controls['retired_ids']);new.update(controls['reference_ids']);changed_prints.add('Body_Rear')
    expected=(set(base['parts'])-retired)|new
    if set(actual)!=expected:errors.append(dict(kind='inventory',missing=sorted(expected-set(actual)),extra=sorted(set(actual)-expected)))
    transform=np.asarray(q['controller_pose']['matrix_world']);diffs={}
    for n,row in base['parts'].items():
        if n in retired:continue
        o=actual[n];o.data.calc_loop_triangles()
        vv=np.array([list(v.co) for v in o.data.vertices],dtype=np.float32)
        ff=np.array([list(t.vertices) for t in o.data.loop_triangles],dtype=np.uint32)
        unchanged=(hashlib.sha256(vv.tobytes()).hexdigest()==row['local_vertices_sha256'] and
                   hashlib.sha256(ff.tobytes()).hexdigest()==row['local_faces_sha256'])
        if n not in changed_prints and not unchanged:errors.append(dict(kind='unexpected_mesh_change',part=n))
        before=np.array(dock['matrices'].get(n,row['matrix_world']));want=transform@before if n in q['controller_group_ids'] else before
        delta=float(np.max(np.abs(np.array(o.matrix_world)-want)));diffs[n]=delta
        if delta>2e-5:errors.append(dict(kind='pose',part=n,max_matrix_error=delta))
        if n in q['controller_group_ids']:moved.append(n)
        elif n not in changed_prints and unchanged:same+=1
    ref=json.loads((root/'direct_reference.json').read_text());center=json.loads((root/'center_reference.json').read_text())
    comparisons={}
    for n,row in ref.items():
        target='Load_Frame' if n=='Load_Frame_Direct' else n.replace('Direct_UPS','UPS_Direct')
        m=raw_solid(row);s=ss[target].m
        delta=float((m-s).volume()+(s-m).volume());comparisons[target]=delta
        if delta>.05:errors.append(dict(kind='approved_solid',part=target,volume_difference_mm3=delta))
    for n,row in center.items():
        if n=='Load_Frame':continue
        target=n.replace('imu_','BMI323_').replace('buck_','Buck6V_');m=raw_solid(row);s=ss[target].m
        delta=float((m-s).volume()+(s-m).volume());comparisons[target]=delta
        if delta>.005:errors.append(dict(kind='approved_fastener',part=target,volume_difference_mm3=delta))
    source_rows=[]
    for key,spec in q['modules'].items():
        cache=json.loads((PROJECT/q['sources'][key+'_cache']['file']).read_text());vv=[];ff=[]
        tr=np.array(spec['matrix_world'])
        rows=[r for r in cache['solids'] if r['index'] not in spec['omit_solid_indices']]
        if key=='imu':rows.append(json.loads((PROJECT/q['sources']['imu_socket']['file']).read_text()))
        for row in rows:
            ff.extend((np.array(row['triangles'])+len(vv)).tolist());vv.extend((np.array(row['vertices'])@tr[:3,:3].T+tr[:3,3]).tolist())
        o=actual[spec['id']];o.data.calc_loop_triangles()
        av=np.array([list(o.matrix_world@v.co) for v in o.data.vertices]);af=np.array([list(t.vertices) for t in o.data.loop_triangles])
        error=float(np.max(np.abs(np.array(vv)-av))) if av.shape==np.shape(vv) else 1e6
        ok=error<3e-5 and np.array_equal(af,np.array(ff)) and o['category']==spec['category'] and o['data_status']==spec['data_status']
        source_rows.append(dict(part=spec['id'],status='PASS' if ok else 'FAIL',max_vertex_roundoff_mm=error,
                               original_source_entities=len(rows),source_triangles_retained=True,scale=1.))
        if not ok:errors.append(dict(kind='vendor_source',part=spec['id']))
    protected=base['protected_hardware'];owner_updates={}
    if controls.get('enabled'):
        received=controls['sources']['hardware_receipt'];assert sha(PROJECT/received['file'])==received['sha256']
        receipt=json.loads((PROJECT/received['file']).read_text());protected=receipt['protected_hardware'];owner_updates=receipt['owner_changes_since_M1_56']
    hardware_drift=[n for n,h in protected.items() if not (PROJECT/n).exists() or sha(PROJECT/n)!=h]
    if hardware_drift:errors.append(dict(kind='hardware_modified',files=hardware_drift))
    return dict(status='PASS' if not errors else 'FAIL',errors=errors,part_count=len(actual),
        changed_prints=sorted(changed_prints),unchanged_parts=same,transformed_ids=moved,new_ids=sorted(new),retired_ids=sorted(retired),
        maximum_transform_error_mm=max(diffs.values()),approved_mesh_volume_differences_mm3=comparisons,
        vendor_sources=source_rows,protected_hardware_files=len(base['protected_hardware']),hardware_drift=hardware_drift,received_owner_updates=owner_updates,
        limits='Mesh/source and finite floating-point comparison only; not a fit tolerance or hardware qualification')


def mounting_checks(ss):
    q=P['off_shelf_modules'];parts={n:s.m for n,s in ss.items()};bbs={n:np.array(m.bounding_box()) for n,m in parts.items()}
    def hits(m,names):
        bb=np.array(m.bounding_box());out=[]
        for n in names:
            b=bbs[n]
            if np.any(bb[3:]<b[:3]) or np.any(b[3:]<bb[:3]):continue
            volume=float((m^parts[n]).volume())
            if volume>1e-4:out.append(dict(part=n,overlap_mm3=volume))
        return out
    upfast={n for n in parts if n.startswith('UPS_Direct_')};fixed=set(parts)-upfast
    service=fixed-set(q['service']['shells_removed']);rows=[];all_pass=True
    for i,(x,y) in enumerate(q['ups_mount']['centers_xy_mm']):
        sc=parts[f'UPS_Direct_Screw_{i}'];nu=parts[f'UPS_Direct_Nut_{i}']
        screw_bad=[dict(dz_mm=float(z),hits=h) for z in np.arange(0,26,.5) if (h:=hits(sc.translate([0,0,float(z)]),fixed))]
        nut_bad=[dict(dz_mm=float(z),hits=h) for z in np.arange(0,12.01,.5) if (h:=hits(nu.translate([0,0,-float(z)]),fixed))]
        socket=cylinder(x,y,82.5,95.15,4.,96);direction=1 if y>0 else -1
        socket_bad=[dict(travel_mm=float(z),hits=h) for z in np.arange(0,100.01,2.) if (h:=hits(socket.translate([0,direction*float(z),0]),service))]
        options=[]
        for short in [18.,22.]:
            zz=116.7+short
            for angle in range(-180,180,15):
                a=math.radians(angle);axis=np.array([math.sin(a),math.cos(a),0.])
                arm=manifold.Manifold.cylinder(80.,1.55,circular_segments=32).transform(
                    np.c_[np.column_stack(([0.,0.,1.],np.cross(axis,[0.,0.,1.]),axis)),[x,y,zz]])
                key=cylinder(x,y,116.7,zz,1.55,96)+arm
                if all(not hits(key.translate([0,0,z]),service) for z in [0.,.5,1.,2.,3.,4.]):
                    options.append(dict(short_leg_mm=short,azimuth_deg=angle))
        support=cylinder(x,y,99.082,99.092,3.,96)-cylinder(x,y,99.081,99.093,1.66,96)
        missing=float((support-parts['UPS_Module']).volume())
        ok=not screw_bad and not nut_bad and not socket_bad and options and missing<1e-4
        all_pass=all_pass and bool(ok)
        rows.append(dict(site=i,status='PASS' if ok else 'FAIL',screw_entry_hits=screw_bad,nut_entry_hits=nut_bad,
            socket_entry_hits=socket_bad,L_key_clear_options=options,missing_PCB_support_mm3=missing,
            long_driver_hits=hits(cylinder(x,y,117.9,210.,1.55,96),fixed)))
    # Release the bearing face by the already-reviewed 0.5mm drop before sliding.
    # Seated Z=0 is covered by the static-solid test and approved-source check;
    # do not drag a float32 contact plane along the deck and call its micron-scale
    # numeric overlap a physical sliding-clearance test.
    removal=[]
    for drop in np.linspace(.1,.5,5):
        h=hits(parts['UPS_Module'].translate([0,0,-float(drop)]),service-{'UPS_Module'})
        if h:removal.append(dict(drop_mm=float(drop),dy_mm=0,hits=h))
    for dy in np.arange(0,120.01,2.):
        h=hits(parts['UPS_Module'].translate([0,float(dy),-.5]),service-{'UPS_Module'})
        if h:removal.append(dict(drop_mm=.5,dy_mm=float(dy),hits=h))
    bench={n for n,s in ss.items() if s.group not in ('pitch','yaw') and not n.startswith('Yaw_')}-set(body_shell_names())
    board_rows=[]
    for name in ['IMU_BMI323','Head_Buck_6V','MCU_Carrier','MCU_Motion']:
        own={name}
        if name.startswith('MCU'):own.update(q['controller_group_ids'])
        own.update(n for n in parts if n.startswith(('BMI323_','Buck6V_')))
        bad=[]
        for z in range(0,41,2):
            h=hits(parts[name].translate([0,0,z]),bench-own)
            if h:bad.append(dict(dz_mm=z,hits=h))
        board_rows.append(dict(part=name,status='FAIL' if bad else 'PASS',positions=21,hits=bad))
    return dict(status='PASS' if all_pass and not removal and all(r['status']=='PASS' for r in board_rows) else 'FAIL',
        ups_sites=rows,ups_removal=dict(status='FAIL' if removal else 'PASS',positions=66,initial_drop_mm=.5,travel_mm=120,hits=removal,
            seated_endpoint='Current whole-model static contact and independent approved-source comparison'),
        board_insertions=board_rows,frame_connected_components=len(parts['Load_Frame'].decompose()),
        scope='Saved main rigid geometry. Four UPS fastener paths, short-key axial entry, socket side entry, PCB support and front extraction; board insertion before bridge/head.',
        flexible_wires='NOT_TESTED',hand_grip_and_wrench_swing='NOT_TESTED',physical_strength='NOT_TESTED',manufacturing_release=False)


def run_current():
    import validate as v
    start=time.time();bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for n in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[n].hide_viewport=False
    assembled();bpy.context.view_layer.update();v.CHECKS.clear()
    ss={o.name.removeprefix(PREFIX):v.Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
    scope=scope_check(ss)
    save_json(ROOT/'reports/off_shelf_scope.json',scope)
    v.check('off_shelf_exact_scope',scope['status'],'已确认布局与保存主模型逐件比较；只改承重板、移动主控组并替换已退役模块',scope)
    if scope['status']!='PASS':raise RuntimeError('Adoption scope mismatch: '+str(scope['errors'][:8]))
    if P.get('ups_rear_controls',{}).get('enabled'):
        from validate_ups_rear_controls import validate_controls
        control=validate_controls(ss)
        v.check('ups_controls_exact_scope_and_seats',control['status'],'上充电下开关；保存主模型与批准候选、未改原件、两个孔座和工具容量对照',control)
        v.check('ups_controls_actual_fit','NOT_TESTED','充电及开关试孔、完整尾线穿入和实物锁紧尚未验证')
    elif P.get('dc_inlet_trial',{}).get('enabled'):
        from validate_dc_inlet_trial import validate_dc
        dc=validate_dc(ss)
        v.check('dc_trial_exact_scope_and_seat',dc['status'],'后壳试配孔座与批准候选对照、原件不变、材料及松散后壳工具空间检查',dc)
        v.check('dc_actual_hole_and_lead_fit','NOT_TESTED','Ø8试孔、螺纹及完整尾线/末端插头穿孔仍需实物试配；照片只确认安装关系')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss)
    mounting=mounting_checks(ss);save_json(ROOT/'reports/off_shelf_mount_validation.json',mounting)
    v.check('off_shelf_saved_mounting',mounting['status'],'当前主模型的UPS穿栓、短工具及取出路径；上层板卡预装检查',{'report':'off_shelf_mount_validation.json','scope':mounting['scope']})
    v.check('new_electrical_architecture','BLOCKED','UPS BAT能力、执行器物理断电、5V分配、BMI323 I2C和DC电气接入尚未完成')
    v.check('selected_buck_geometry','BLOCKED','6V版当前借用原厂7.2V系列CAD；精确装件和持续功率未确认')
    v.check('full_wired_assembly','BLOCKED','旧身体走线因架构和板位改变失效；局部插头研究不等于完整线束')
    v.check('actual_horns_and_installed_UPS','BLOCKED','SC-0090-C001舵盘锁紧与UPS完整电芯/绝缘/接口装件仍需到货资料或实测')
    v.check('PA12_strength_and_service','NOT_TESTED','PA12配合、强度、螺母手部操作与反复拆装待实物试验')
    v.check('mass_budget_current','NOT_TESTED','新UPS/电芯替换旧小电池；旧质量和重心估算不能沿用')
    result=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),
        checks=v.CHECKS,counts={s:sum(r['status']==s for r in v.CHECKS) for s in ['PASS','FAIL','BLOCKED','NOT_TESTED','NOT_APPLICABLE']},
        elapsed_s=time.time()-start,scope_report='off_shelf_scope.json',manufacturing_release=False)
    save_json(ROOT/'reports/validation.json',result)
    print('OFF_SHELF_VALIDATION_COMPLETE',result['counts'],flush=True)
    if result['counts']['FAIL']:raise RuntimeError('Current model checks failed')
    return result
