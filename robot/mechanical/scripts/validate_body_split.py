"""Current changed-system checks plus explicitly dated, unaffected evidence.

Historical local CAD checks are not rerun against invented upper/lower aliases.
The saved M1.50 receipt is immutable. Exact geometry/config invariance permits
reuse for unchanged interfaces; body-dependent service tests are superseded.
"""
from pathlib import Path
import hashlib, json, time
from common import *


def run_current():
    import validate as v
    from harness_context import Context, sha
    from validate_interface_completion import run as inserts
    started=time.time(); ctx=Context(); ss=ctx.ss; v.CHECKS.clear()
    q=P['body_front_rear_split']; snapshot=PROJECT/q['baseline']
    evidence=ROOT/'reports/body_split_validation.json'
    current=json.loads(evidence.read_text())
    assert current['status']=='PASS' and current['source_blend_sha256']==ctx.source_hash
    before=json.loads((PROJECT/q['baseline_part_fingerprints']).read_text())['native_fingerprints']
    retired={'Body_Upper','Body_Lower'}|{s+str(i) for s in ['Shell_Screw_','Shell_Insert_'] for i in range(4)}
    assert set(before)-set(ctx.print_fingerprints)==retired
    assert all(ctx.fingerprint(ss[n])==h for n,h in before.items() if n not in retired)
    prior_path=snapshot/'mechanical/reports/validation.json'; prior=json.loads(prior_path.read_text())
    assert prior['counts']['FAIL']==0
    # Fresh whole-model collision, combined motion, wheel motion, optical,
    # topology, ground/dock and mass checks consume the saved new shells.
    v.actual_checks(ss); v.geometry_checks(ss); v.camera_checks(ss)
    v.access_checks(ss,core_only=True); v.mass_checks(ss); v.v12_checks(ss)
    r=inserts(rows_only=True)
    v.check('interface_completion',r['status'],'当前嵌件孔壁、盲孔底和螺钉啮合复核；已移除旧拼缝嵌件',
            {'report':'current_insert_validation.json','rows':len(r['rows'])},r['scope'])
    v.check('body_split_exact_scope','PASS','两片新外壳替换旧上下壳；移除8件旧拼缝五金，另199件实体保持',
            current['scope'],'Exact world mesh fingerprints and unchanged unrelated configuration against immutable M1.50.')
    v.check('body_split_module_paths',current['status'],'带喇叭／后接口板及插头包络的前后壳平移，车轮保留',
            current['paths'],'275 positions per module; opposite shell closed; finite samples, no flexible-wire proof.')
    v.check('body_split_frame_tool_access',current['status'],'闭壳后4枚框架螺钉及工具从底部进入',
            current['frame_tool_access'],'Actual fastener hulls + conservative shaft/handle 150 mm axial sweeps; physical drive/hand fit untested.')
    v.check('body_split_locator_walls','PASS','两组一体插舌定位，接收座侧壁和顶壁实测网格1.7mm',current['locators'],
            'Rays through saved mesh; 0.3mm trial gap per side, PA12 coupon and strength NOT_TESTED.')
    v.check('body_split_wired_closure','BLOCKED','前后壳刚体路径已检查；完整带线闭壳仍未完成',
            {'reason':current['complete_wired_assembly']})
    fresh={r['id'] for r in v.CHECKS}
    # These tests explicitly depend on the retired split or broad historical
    # comparisons. Keep them as dated history, never relabel them current PASS.
    superseded={
        'wheel_pocket_service_wall_samples','speaker_SP3040_scope','readiness_scope',
        'prearrival_scope','mount_roots_scope','display_frame_scope','completion_scope',
        'waveshare_source_and_scope','six_fixes_scope','six_fixes_body_service',
        'six_fixes_shell_walls','wheel_drive_service_sequence','wheel_shell_local_walls',
        'merged_frame_and_rear_PCB_removal','physical_part_consolidation',
        'other_fastener_feature_cleanup','speaker_shell_attachment','speaker_shell_tool_access',
        'speaker_blind_boss_skin','speaker_max_box_envelope','speaker_removal_path',
        'speaker_front_grille_paths','readiness_rear_switch_shell','readiness_local_solids',
        'readiness_new_hardware_clearance','readiness_shell_paths','rear_mesh_export_repair',
        'approved_thin_cleanup','camera_CAM_approved_completion','approved_neck_capacity',
        'head_axial_retention','cam_entry_exact_scope'}
    historical=[]
    for row in prior['checks']:
        if row['id'] in fresh:continue
        record=dict(row,evidence_revision='V1.2-M1.50',evidence_file=str(prior_path.relative_to(PROJECT)),
                    evidence_file_sha256=sha(prior_path),rerun_this_revision=False)
        if row['id'] in superseded:
            record['current_applicability']='Historical receipt only; body scope/path replaced by current split checks. Retained-head proofs use exact unchanged part fingerprints.'
            historical.append(record)
        else:
            record['current_applicability']='Unchanged component/config evidence; current whole-model collisions and affected body paths rerun separately.'
            v.CHECKS.append(record)
    ctx.assert_unchanged()
    result=dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,
        status_vocabulary=['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE'],
        elapsed_s=round(time.time()-started,1),checks=v.CHECKS,
        counts={s:sum(c['status']==s for c in v.CHECKS) for s in ['PASS','FAIL','NOT_TESTED','BLOCKED','NOT_APPLICABLE']},
        current_rerun_ids=sorted(fresh),historical_superseded_checks=historical,
        inherited_evidence_basis=dict(prior_revision='V1.2-M1.50',prior_report=str(prior_path.relative_to(PROJECT)),
            prior_report_sha256=sha(prior_path),unchanged_native_parts=199,scope_report='body_split_validation.json'),
        limits='Explicit current reruns and dated unchanged-interface evidence. No invented shell aliases, physical fit, wire deformation, strength or manufacturing approval.')
    save_json(ROOT/'reports/validation.json',result)
    print('CURRENT_BODY_VALIDATION_COMPLETE',result['counts'],flush=True)
    return result
