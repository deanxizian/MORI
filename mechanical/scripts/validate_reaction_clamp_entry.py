"""Fresh saved-model R2 scope/entry/wall/shell/transfer and core validation.

Historical geometry is not replaced with a regenerated reference. Compare the
one changed print to the independently approved mesh and all other parts to
their pre-adoption fingerprints. Physical interfaces remain explicitly open.
"""
from common import *
import hashlib,time,copy
from review_geometry_fingerprint import record
from neck_capacity import local_curves
from reaction_clamp_entry import construct
from mathutils.bvhtree import BVHTree

def translated_entry(m,fixture,a,b,gap,depth_limit=18):
    stack=[(float(a),float(b),0)];intervals=[];failure=None
    while stack:
        a,b,depth=stack.pop();mid=(a+b)/2;motion=(b-a)/2+.0001;posed=m.translate([0,0,mid])
        distance=float(posed.min_gap(fixture,gap+motion+.001));overlap=float((posed^fixture).volume());lower=distance-motion
        if lower<gap or overlap>1e-5:
            if depth<depth_limit:stack.extend([(mid,b,depth+1),(a,mid,depth+1)]);continue
            failure=dict(start_Z_mm=a,end_Z_mm=b,gap_lower_mm=lower,overlap_mm3=overlap);break
        intervals.append(dict(start_Z_mm=a,end_Z_mm=b,gap_lower_mm=lower,depth=depth))
    ok=failure is None and intervals
    if ok:assert all(x['end_Z_mm']==y['start_Z_mm'] for x,y in zip(intervals[:-1],intervals[1:]))
    return dict(status='PASS' if ok else 'FAIL',interval_count=len(intervals),intervals=intervals,first_failure=failure,
                minimum_gap_lower_mm=min((r['gap_lower_mm'] for r in intervals),default=0))

def focused_checks(ss):
    from validate import rigidtr
    settings=P['reaction_clamp_entry'];neck=P['neck_harness_capacity'];candidate=ss['Pitch_Yoke'].m
    q=copy.deepcopy(neck);q['candidate_parameters']['neck_profile']['reference_reaction_bore_r_mm']=settings['parameters']['reference_reaction_bore_r_mm']
    original={n:s.m for n,s in ss.items() if n in neck['changed_existing_ids']}
    replay,features=construct(original,settings,neck)
    sym=lambda a,b:float((a-b).volume()+(b-a).volume())
    source_difference=sym(replay,candidate)
    entry=[]
    for label,names in [('bare_print',['Yaw_Reaction_Link']),('trial_hardware',['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut']),
                        ('horn_placeholder',['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn'])]:
        moving=manifold.Manifold.batch_boolean([ss[n].m for n in names],manifold.OpType.Add)
        row=translated_entry(moving,candidate,*settings['entry_Z_range_mm'],settings['required_nominal_gap_mm'])
        row.update(group=label,moving_ids=names,actual_hardware_qualified=False);entry.append(row)
        print('R2_SAVED_ENTRY',label,row['status'],row['interval_count'],flush=True)
    shells=[]
    for name in ['Head_Front','Head_Rear']:
        target=ss[name];radius=float(np.linalg.norm(target.v-[0,0,D['head_z']],axis=1).max())
        stack=[(-20.,25.,0)];intervals=[];failure=None
        while stack:
            a,b,depth=stack.pop();mid=(a+b)/2;tr=np.asarray(rigidtr(0,mid));m=target.m.transform(tr[:3,:])
            bound=2*radius*math.sin(math.radians((b-a)/2)/2)+.0001
            distance=float(candidate.min_gap(m,settings['required_nominal_gap_mm']+bound+.001));vol=float((candidate^m).volume());lower=distance-bound
            if lower<settings['required_nominal_gap_mm'] or vol>1e-5:
                if depth<18:stack.extend([(mid,b,depth+1),(a,mid,depth+1)]);continue
                failure=dict(start_pitch_deg=a,end_pitch_deg=b,gap_lower_mm=lower,overlap_mm3=vol);break
            intervals.append(dict(start_pitch_deg=a,end_pitch_deg=b,gap_lower_mm=lower,depth=depth))
        ok=failure is None and intervals and intervals[0]['start_pitch_deg']==-20 and intervals[-1]['end_pitch_deg']==25
        if ok:assert all(x['end_pitch_deg']==y['start_pitch_deg'] for x,y in zip(intervals[:-1],intervals[1:]))
        shells.append(dict(part=name,status='PASS' if ok else 'FAIL',interval_count=len(intervals),intervals=intervals,first_failure=failure,
                           yaw_scope='all yaw by shared rigid yaw invariance',minimum_gap_lower_mm=min((r['gap_lower_mm'] for r in intervals),default=0)))
    surfaces=[]
    for m in [features['inner'],features['outer']]:
        mesh=m.to_mesh64();v=np.asarray(mesh.vert_properties)[:,:3];f=np.asarray(mesh.tri_verts);f=f[np.ptp(v[f][:,:,2],axis=1)>1e-6]
        surfaces.append((v,f,BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)))
    walls=[];p=settings['parameters']
    for i,(v,f,_) in enumerate(surfaces):
        points=np.vstack([v[np.unique(f)],v[f].mean(axis=1)]);points=points[(points[:,2]>=157)&(points[:,2]<=173.1)];rows=[]
        for point in points:
            found=surfaces[1-i][2].find_nearest(Vector(point));other=np.array(found[0])
            if all(a[1]>p['rear_open_max_Y_mm']+.01 or a[2]<p['rear_open_start_Z_mm']-.01 for a in [point,other]):rows.append((float(found[3]),point.tolist()))
        value,point=min(rows);walls.append(dict(direction='inner_to_outer' if i==0 else 'outer_to_inner',sample_count=len(rows),minimum_mm=value,point_mm=point))
    journal=[];missing=[]
    for z in np.linspace(149.5,155.9,33):
        for angle in range(0,360,3):
            a=math.radians(angle);hits=candidate.ray_cast([0,0,float(z)],[100*math.cos(a),100*math.sin(a),float(z)])
            if len(hits)<2:missing.append(dict(z_mm=float(z),angle_deg=angle));continue
            journal.append(dict(z_mm=float(z),angle_deg=angle,radial_backing_mm=float((hits[1].distance-hits[0].distance)*100)))
    pack,data,curve_rows=local_curves(q);_,before_curves,_=local_curves(neck);assert all(np.array_equal(data[k],before_curves[k]) for k in data)
    mesh=candidate.to_mesh64();v=np.asarray(mesh.vert_properties)[:,:3];f=np.asarray(mesh.tri_verts);tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
    wires=[]
    for i,slot in enumerate(pack['selected']):
        for yaw in range(-60,61,10):
            a=math.radians(-yaw);r=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
            points=data[f'wire{i}_y{yaw}']@r.T;distance=min(float(tree.find_nearest(Vector(pt))[3]) for pt in points)
            lower=distance-slot['OD_mm']/2-max(row['chord_error_mm'] for row in curve_rows)-np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2-.0001
            wires.append(dict(wire=i,yaw_deg=yaw,gap_lower_mm=float(lower),status='PASS' if lower>=settings['required_nominal_gap_mm'] else 'FAIL'))
    keeper=ss['Yaw_Anti_Lift_Keeper'].m;bench=[];transfer=[]
    for dy in np.arange(0,60.01,.5):
        vol=float((keeper.translate([0,float(dy),0])^candidate).volume())
        if vol>1e-5:bench.append(dict(Y_mm=float(dy),overlap_mm3=vol))
    yawset={n for n,s in ss.items() if s.group=='yaw'}|{'Yaw_Anti_Lift_Keeper','Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Output','Yaw_Lock_Screw'}
    fixture=set(ss)-yawset-{n for n,s in ss.items() if s.group=='pitch'}-{'Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1','Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1','Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut'}
    for dz in np.arange(0,90.01,.5):
        moved=candidate.translate([0,0,float(dz)]);bb=np.asarray(moved.bounding_box())
        for n in fixture:
            target=ss[n]
            if np.any(bb[:3]>target.hi) or np.any(bb[3:]<target.lo):continue
            vol=float((moved^target.m).volume())
            if vol>1e-5:transfer.append(dict(Z_mm=float(dz),part=n,overlap_mm3=vol))
    capture=[]
    for yaw in range(-60,61,10):
        for dz in [.39,.41,1.]:
            tr=np.asarray(rigidtr(yaw,0));m=candidate.transform(tr[:3,:]).translate([0,0,dz]);vol=float((m^keeper).volume())
            capture.append(dict(yaw_deg=yaw,lift_mm=dz,overlap_mm3=vol,status='PASS' if ((vol<=.01)==(dz==.39)) else 'FAIL'))
    ok=source_difference<settings['numerical_comparison_limit_mm3'] and all(r['status']=='PASS' for r in entry+shells+wires+capture) and min(r['minimum_mm'] for r in walls)>=settings['retained_wall_reserve_mm'] and not missing and min(r['radial_backing_mm'] for r in journal)>=settings['retained_wall_reserve_mm'] and not bench and not transfer
    return dict(status='PASS' if ok else 'FAIL',scope='Saved-model source replay, continuous prototype entry/shell motion, retained bulk wall/radial journal/local curves and finite keeper/drop/capture checks',
        source_replay_difference_mm3=source_difference,continuous_entry=entry,continuous_shell_rotation=shells,
        retained_side_wall_samples=walls,journal_radial_samples=dict(sample_count=len(journal),minimum_mm=min(r['radial_backing_mm'] for r in journal),missing=missing),
        local_11_curve_checks=wires,keeper_side_entry=dict(samples=121,hits=bench),body_vertical_transfer=dict(samples=181,hits=transfer),axial_capture=dict(samples=capture),
        actual_horn_and_fasteners='BLOCKED',full_harness='BLOCKED',global_wall_or_strength='NOT_TESTED',physical_hand_access='NOT_TESTED',manufacturing_release=False)

def run_current():
    import validate as v
    from validate_cam_right_services import run as cam_services
    start=time.time();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();q=P['reaction_clamp_entry']
    assert q['approved']
    receipt=json.loads((PROJECT/q['approval']).read_text());baseline=json.loads((PROJECT/q['baseline']).read_text())
    assert receipt['approval']=='USER_APPROVED' and q['parameters']==receipt['parameters']
    assert sha(PROJECT/q['baseline'])==receipt['baseline_record']['sha256']
    for asset in receipt['source_geometry'].values():assert sha(PROJECT/asset['file'])==asset['sha256']
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
    assembled();bpy.context.view_layer.update();v.CHECKS.clear()
    ss={o.name.removeprefix(PREFIX):v.Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
    now={n:record(s.v,s.f.tolist()) for n,s in ss.items()}
    assert set(now)==set(baseline['parts'])
    changed=sorted(n for n in now if now[n]['exact_sha256']!=baseline['parts'][n]['geometry']['exact_sha256'])
    matrices=[n for n,s in ss.items() if not np.array_equal(np.asarray(s.o.matrix_world),np.asarray(baseline['parts'][n]['matrix_world']))]
    asset=receipt['source_geometry']['approved'];d=np.load(PROJECT/asset['file']);approved=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    d=np.load(PROJECT/receipt['source_geometry']['baseline']['file']);old=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    current=ss['Pitch_Yoke'].m;sym=lambda a,b:float((a-b).volume()+(b-a).volume());difference=sym(approved,current)
    roi=q['numerical_edit_ROI'];a,b=roi['z_mm'];region=manifold.Manifold.cylinder(b-a,roi['radius_mm'],roi['radius_mm'],256).translate([0,0,a])
    outside=float(((current-old)-region).volume()+((old-current)-region).volume())
    skin=q['preserved_fit_skin'];a,b=skin['z_mm'];probe=manifold.Manifold.cylinder(b-a,skin['outer_probe_radius_mm'],skin['outer_probe_radius_mm'],256).translate([0,0,a])
    probe-=manifold.Manifold.cylinder(b-a+.02,skin['inner_radius_mm'],skin['inner_radius_mm'],256).translate([0,0,a-.01])
    skin_diff=sym(current^probe,old^probe)
    before=json.loads((PROJECT/baseline['snapshot']/'config/geometry.json').read_text());config=copy.deepcopy(P);config.pop('reaction_clamp_entry');config.pop('revision');before.pop('revision')
    # Finder view metadata and Python bytecode are not native hardware sources.
    # Keep all PCB, contract, drawing and research source hashes protected.
    excluded=[n for n in baseline['protected_hardware'] if Path(n).name=='.DS_Store' or ('__pycache__' in Path(n).parts and Path(n).suffix=='.pyc')]
    drift=[n for n,h in baseline['protected_hardware'].items() if n not in excluded and sha(PROJECT/n)!=h]
    scope=dict(changed_ids=changed,unchanged_native_parts=len(ss)-len(changed),part_count=len(ss),new_ids=[],retired_ids=[],
        changed_transform_ids=matrices,approved_mesh_difference_mm3=difference,comparison_limit_mm3=q['numerical_comparison_limit_mm3'],
        outside_edit_ROI_difference_mm3=outside,bearing_fit_skin_difference_mm3=skin_diff,
        unchanged_config_except_revision_and_R2=(config==before),hardware_drift=drift,excluded_runtime_caches=excluded,protected_hardware_count=len(baseline['protected_hardware'])-len(excluded))
    scope_ok=changed==q['changed_existing_ids'] and not matrices and difference<q['numerical_comparison_limit_mm3'] and outside<q['numerical_comparison_limit_mm3'] and skin_diff<q['numerical_comparison_limit_mm3'] and config==before and not drift
    v.check('reaction_entry_exact_scope','PASS' if scope_ok else 'FAIL','已确认R2：仅Pitch_Yoke内部孔道和后侧颈壁改变；其余200件及全部硬件位姿保持',scope,'Independent pre-adoption fingerprints and approved mesh; finite numerical difference is not print-fit tolerance.')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss);v.access_checks(ss,core_only=True);v.mass_checks(ss);v.v12_checks(ss)
    focused=focused_checks(ss)
    v.check('reaction_entry_saved_geometry',focused['status'],'保存后的R2连续装入、完整壳体俯仰、保留孔壁与防脱／移入检查',{'report':'reaction_clamp_entry_validation.json','scope':focused['scope']})
    services=cam_services(ss)
    v.check('cam_right_services',services['status'],'保持USB朝右；当前模型CAM安装、原工具与接口分配空间复核',{'report':'cam_right_service_validation.json','scope':services['scope']},services['method'])
    v.check('reaction_actual_horn_locking','BLOCKED','裸打印件装入已修复；实际SC-0090-C001舵盘、花键和锁紧叠层按用户决定到货后核对')
    v.check('full_wired_assembly','BLOCKED','完整线材／端子、初始理线、最终整理、入壳和带线闭壳尚未完成；未采用任何线束候选')
    v.check('R2_print_strength','NOT_TESTED','开放端缘、PA12刚度、强度、疲劳与真实手操作仍待试打；径向／侧壁采样不等于强度放行')
    v.check('historical_extended_checks','NOT_TESTED','未重跑的历史局部试件保留原日期；本次只报告当前执行的检查',{'baseline':baseline['snapshot']})
    focused.update(revision=P['revision'],source_blend_sha256=sha(ROOT/'mori_v1_2.blend'),scope_readback=scope,
                   approved=True,elapsed_s=time.time()-start)
    save_json(ROOT/'reports/reaction_clamp_entry_validation.json',focused)
    result=dict(revision=P['revision'],source_blend_sha256=sha(ROOT/'mori_v1_2.blend'),checks=v.CHECKS,
        counts={s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},
        elapsed_s=time.time()-start,historical_superseded_checks=[],physical_validation='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/validation.json',result)
    print('REACTION_ENTRY_VALIDATION_COMPLETE',result['counts'],'changed',changed,'approved_delta',difference,flush=True)
    if result['counts']['FAIL']:raise RuntimeError('Current R2 saved-model validation failed')
    return result
