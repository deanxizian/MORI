"""Independent approved-mesh and exact-scope check, plus fresh core validation."""
from common import *
import hashlib,time
from review_geometry_fingerprint import record


def run_current():
    import validate as v
    start=time.time();bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
    for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
    assembled();bpy.context.view_layer.update();v.CHECKS.clear()
    ss={o.name.removeprefix(PREFIX):v.Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
    baseline=json.loads((ROOT/'input_assets/M1_53_C6_baseline.json').read_text())
    approval=json.loads((ROOT/'input_assets/C6_approval.json').read_text())
    assert approval['status']=='USER_APPROVED'
    reference=ROOT/'input_assets/C6_Yaw_Base_approved.npz'
    assert hashlib.sha256(reference.read_bytes()).hexdigest()==approval['reference_sha256']
    now={n:record(s.v,s.f.tolist()) for n,s in ss.items()}
    assert set(now)==set(baseline['parts'])
    changed=[n for n in now if now[n]['exact_sha256']!=baseline['parts'][n]['exact_sha256']]
    assert changed==['Yaw_Base'],changed
    data=np.load(reference)
    expected=manifold.Manifold(manifold.Mesh64(data['vertices_mm'],data['triangles'].astype(np.uint64)))
    current=ss['Yaw_Base'].m
    delta=(expected-current).volume()+(current-expected).volume()
    assert delta<.003,delta  # Saved Blender float32 mesh versus float64 Boolean reference.
    before=np.load(ROOT/'input_assets/M1_52_Yaw_Base_before_C6.npz')
    old=manifold.Manifold(manifold.Mesh64(before['vertices_mm'],before['triangles'].astype(np.uint64)))
    removed=old-current;added=(current-old).volume()
    assert added<.003 and len(current.decompose())==1
    q=P['neck_entry_relief']
    prior_path=PROJECT/q['baseline']/'config/geometry.json'
    assert hashlib.sha256(prior_path.read_bytes()).hexdigest()==baseline['config_sha256'],'Changed pre-adoption configuration'
    prior=json.loads(prior_path.read_text())
    settings=json.loads(json.dumps(P));settings.pop('neck_entry_relief');settings.pop('revision');prior.pop('revision')
    assert settings==prior,'Unapproved configuration change'
    scope=dict(changed_ids=changed,unchanged_native_parts=len(ss)-1,
        candidate_symmetric_difference_mm3=delta,numerical_volume_tolerance_mm3=.003,
        removed_volume_mm3=removed.volume(),added_volume_mm3=added,
        connected_solids=len(current.decompose()),configuration_delta=['revision','neck_entry_relief'],
        hardware_transforms_unchanged=True,datums_unchanged=True)
    v.check('C6_exact_scope','PASS','仅加宽固定偏航桥现有左槽外边缘0.8mm，其余200件原生实体保持',scope,
        'Canonical world triangles against reviewed M1.52; independent approved candidate mesh, not a generated reference. Float32 storage tolerance is numerical, not a physical fit tolerance.')
    v.actual_checks(ss);v.geometry_checks(ss);v.camera_checks(ss)
    v.access_checks(ss,core_only=True);v.mass_checks(ss);v.v12_checks(ss)
    v.check('full_harness','BLOCKED','本次只采用C6通道；完整走线、固定、恒定长度与带线闭壳仍未完成')
    v.check('historical_extended_checks','NOT_TESTED','其他历史局部装配检查本次未重跑，保留原日期和输入边界',
        {'prior_snapshot':q['baseline'],'current_reruns':'core rigid motion, topology, optics, access and approved C6 scope'})
    source=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()
    result=dict(revision=P['revision'],source_blend_sha256=source,checks=v.CHECKS,
        counts={s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},
        elapsed_s=time.time()-start,historical_superseded_checks=[],physical_validation='NOT_TESTED',manufacturing_release=False)
    save_json(ROOT/'reports/neck_entry_relief_validation.json',dict(status='PASS',source_blend_sha256=source,scope=scope,
        full_harness='BLOCKED',physical_strength='NOT_TESTED',manufacturing_release=False))
    save_json(ROOT/'reports/validation.json',result)
    print('C6_VALIDATION_COMPLETE',result['counts'],flush=True)
    if result['counts']['FAIL']:raise RuntimeError('Current C6 geometry checks failed')
    return result
