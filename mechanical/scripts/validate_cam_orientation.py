"""Current-model rigid scope and native/service checks for the approved CAM pose."""
from common import *
import hashlib,time
from review_geometry_fingerprint import record

def run_current():
    import validate as v
    from cam_orientation import transform
    from validate_cam_right_services import run as service_check
    started=time.time();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
    assembled();bpy.context.view_layer.update();v.CHECKS.clear()
    q=P['cam_orientation'];base=json.loads((PROJECT/q['baseline']).read_text())
    approval=json.loads((PROJECT/q['approval']).read_text());assert approval['status']=='USER_APPROVED'
    for name,h in approval['tool_sources'].items():assert sha(PROJECT/name)==h,name
    ss={o.name.removeprefix(PREFIX):v.Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
    now={n:record(s.v,s.f.tolist()) for n,s in ss.items()};assert set(now)==set(base['parts'])
    changed=sorted(n for n in now if now[n]['exact_sha256']!=base['parts'][n]['exact_sha256'])
    assert changed==sorted(q['changed_existing_ids']),changed
    visual_base=json.loads((PROJECT/q['visual_baseline']).read_text());tr=transform();r=tr[:3,:3];t=tr[:3,3]
    rows=[]
    for n,s in ss.items():
        o=s.o;o.data.calc_loop_triangles();vv=np.asarray([tuple(p) for p in vertices_world(o)],dtype=np.float64)
        ff=np.asarray([tuple(p.vertices) for p in o.data.loop_triangles],dtype=np.uint64)
        assert hashlib.sha256(ff.tobytes()).hexdigest()==visual_base[n]['triangles_sha256'],n
        if n not in changed:
            assert hashlib.sha256(vv.tobytes()).hexdigest()==visual_base[n]['vertices_sha256'],n
            continue
        old=np.load(PROJECT/base['assets'][n]['file']);expected=old['vertices_mm']@r.T+t
        assert np.array_equal(s.f,old['triangles']) and np.max(np.abs(s.v-expected))<1e-8,n
        old_visual=np.load(ROOT/('input_assets/M1_53_'+n+'_visual_before_right.npz'))
        error=float(np.max(np.abs(vv-(old_visual['vertices_mm']@r.T+t))))
        assert error<.00003,(n,error)
        refs=json.loads(o['component_reference_index']);prior=base['assets'][n]['component_reference_index']
        assert [p['reference'] for p in refs]==[p['reference'] for p in prior]
        for row in refs:
            points=vv[slice(*row['vertices'])]
            assert np.max(np.abs(np.asarray(row['bounds_xyz_mm'])-np.array([points.min(0),points.max(0)]).T))<1e-8
        rows.append(dict(id=n,visual_coordinate_error_mm=error,solid_vertices_exact=True,
                         triangles_unchanged=True,component_count=len(refs)))
    old_config_path=PROJECT/base['snapshot']/'config/geometry.json'
    assert sha(old_config_path)==base['config_sha256'],'Changed pre-adoption configuration'
    old_config=json.loads(old_config_path.read_text())
    current=json.loads(json.dumps(P));current.pop('cam_orientation');current.pop('revision');old_config.pop('revision')
    assert current==old_config,'Unapproved configuration change'
    # The historical snapshot accidentally included one Python bytecode cache.
    # Keep that receipt intact, but protect source files rather than requiring a
    # machine/ABI-specific cache in a clean checkout.
    runtime_caches=[n for n in base['protected_hardware']
                    if '__pycache__' in Path(n).parts and Path(n).suffix=='.pyc']
    protected_sources={n:h for n,h in base['protected_hardware'].items() if n not in runtime_caches}
    protected=[n for n,h in protected_sources.items() if sha(PROJECT/n)!=h];assert not protected,protected
    center=np.array(P['layout']['cam_board_center_from_head_mm']);center[2]+=D['head_z'];half=P['waveshare_detail']['cam']['hole_grid_mm']/2
    holes=np.array([[center[0]+x,center[1],center[2]+z] for x in [-half,half] for z in [-half,half]])
    moved=holes@r.T+t;axis_error=max(min(np.linalg.norm(p-a) for a in holes) for p in moved)
    assert axis_error<1e-8
    scope=dict(changed_ids=changed,unchanged_native_parts=len(ss)-len(changed),new_parts=0,
        printed_parts_unchanged=True,visual_and_validation_meshes_checked=True,rigid_rows=rows,
        mounting_axis_set_error_mm=float(axis_error),protected_hardware_files=len(protected_sources),
        excluded_runtime_caches=runtime_caches,
        hardware_sources_unchanged=True,configuration_delta=['revision','cam_orientation'])
    v.check('cam_right_exact_scope','PASS','CAM整板及板载双麦转向右侧；其余198件和全部打印件保持',scope,
        'Exact quarter-turn of independent pre-adoption solid/visual vertices, unchanged triangles and per-component bounds; no part scaling.')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss)
    v.access_checks(ss,core_only=True);v.mass_checks(ss);v.v12_checks(ss)
    services=service_check(ss)
    v.check('cam_right_services',services['status'],'CAM右向USB分配空间、原螺钉工具与装入路径复核',
            {'report':'cam_right_service_validation.json','scope':services['scope']},services['method'])
    v.check('cam_right_full_harness','BLOCKED','CAM上端信号／电源／FPC出口已变；此前完整上端路线不可沿用，仍需重排和验证')
    v.check('historical_extended_checks','NOT_TESTED','其他历史局部装配检查保留原日期；本次不冒充全部重新执行',
            {'baseline':base['snapshot'],'current':'full native motion/topology/optics/core access plus CAM services'})
    source=sha(ROOT/'mori_v1_2.blend')
    result=dict(revision=P['revision'],source_blend_sha256=source,checks=v.CHECKS,
        counts={s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},
        elapsed_s=time.time()-started,historical_superseded_checks=[],physical_validation='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/cam_orientation_validation.json',dict(status='PASS' if not result['counts']['FAIL'] else 'FAIL',
        revision=P['revision'],source_blend_sha256=source,scope=scope,services=services['status'],
        full_harness='BLOCKED',physical_validation='NOT_TESTED',manufacturing_release=False))
    save_json(ROOT/'reports/validation.json',result)
    print('CAM_RIGHT_VALIDATION_COMPLETE',result['counts'],flush=True)
    if result['counts']['FAIL']:raise RuntimeError('Current CAM orientation checks failed')
    return result
