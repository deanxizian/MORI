"""Publish public-source progress separately from unfinished assembly design.

Read-only with respect to main CAD, geometry, contracts and electrical sources.
One local upright terminal sweep passed; the complete procedure is unfinished.
"""
from pathlib import Path
import hashlib
import html
import json
from datetime import datetime, timezone

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
ROOT = A8.parents[3]
OUT = A8 / 'supplier_source_update'
OUT.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
protected = {
    'mechanical/mori_v1_2.blend': 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f',
    'config/geometry.json': '0caa6c209c2e699a89f3d5111ffaf1b54b9b89bb361f885d70b50cbfbc26aeb4',
    'contracts/mechanical_interfaces.json': '39d5c3bc786daed52251c9c1669175e7fda374be4b2cec78c56b7019a2457268',
}
for p, digest in protected.items():
    assert sha(ROOT / p) == digest, p
protected['contracts/components.json'] = sha(ROOT / 'contracts/components.json')
base = A8 / 'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating'
specs = [
    ('upper_terminal_feed', 'screen_CAM_upper_terminal_feed.py', 'refine_CAM_root_seating.py'),
    ('upright_staging', 'plan_CAM_upper_wire_staging.py', 'refine_CAM_root_seating.py'),
    ('raised_staging', 'plan_CAM_raised_wire_staging.py', 'plan_CAM_upper_wire_staging.py'),
]
inputs = {}
records = {}
for folder, script, helper in specs:
    p = base / folder / 'screen.json'
    d = read(p)
    assert d['source_main_sha256'] == protected['mechanical/mori_v1_2.blend']
    assert d['script_sha256'] == sha(A8 / script)
    assert d['helper_sha256'] == sha(A8 / helper)
    assert d['source_seating_sha256'] == sha(base / 'aligned_tails/verification.json')
    assert not d['main_applied'] and not d['manufacturing_release']
    assert d['whole_harness'] == 'BLOCKED' and d['continuous_motion'] == 'NOT_TESTED'
    cache = 'failure_poses.npz' if folder == 'upper_terminal_feed' else 'curves.npz'
    key = 'failure_poses_sha256' if folder == 'upper_terminal_feed' else 'curves_sha256'
    assert d[key] == sha(p.parent / cache)
    for q in [p, p.parent / cache, A8 / script, A8 / helper]:
        inputs[str(q.relative_to(ROOT))] = sha(q)
    records[folder] = d
uf, us, ls = (records[k] for k, _, _ in specs)
assert len(uf['rows']) == 16 and all(r['status'] == 'BLOCKED' for r in uf['rows'])
assert len(us['rows']) == 21 and us['status'] == 'BLOCKED'
assert ls['status'] == 'BLOCKED' and ls['selected_raise_mm'] is None
assert [t['maximum_raise_mm'] for t in ls['trials']] == [2., 3., 4.]
assert all(len(t['rows']) == 21 and t['status'] == 'BLOCKED' for t in ls['trials'])
assert ls['source_direct_staging_sha256'] == sha(base / 'upright_staging/screen.json')
for trial in [us, *ls['trials']]:
    for row in trial['rows']:
        for curve in row['curves']:
            assert abs(curve['polyline_length_change_mm']) < 1e-8

apsh = A8 / 'ssh_catalogue_addendum/apsh'
retrieval = read(apsh / 'retrieval.json')
assert retrieval['http_status'] == 200 and retrieval['content_type'] == 'application/pdf'
assert retrieval['sha256'] == sha(apsh / 'JST_eAPSH.pdf')
assert (apsh / 'JST_eAPSH.pdf').read_bytes().startswith(b'%PDF-')
for filename in ['JST_eAPSH.pdf', 'retrieval.json', 'page1_mupdf.png', 'README.md']:
    p = apsh / filename
    inputs[str(p.relative_to(ROOT))] = sha(p)
lbt = A8 / 'ssh_catalogue_addendum'
lbt_retrieval = read(lbt / 'live_recheck_142240.json')
assert lbt_retrieval['http_status'] == 200 and lbt_retrieval['content_type'] == 'application/pdf'
assert lbt_retrieval['sha256'] == sha(lbt / 'JST_eLBT.pdf')
assert lbt_retrieval['pages'] == 3 and lbt_retrieval['rendered_page'] == 2
assert lbt_retrieval['matches_existing_archive'] and not lbt_retrieval['new_dimension_evidence']
for filename in ['JST_eLBT.pdf', 'retrieval.json', 'live_recheck_142240.json', 'contact_page2.png', 'README.md']:
    p = lbt / filename
    inputs[str(p.relative_to(ROOT))] = sha(p)
extension = A8 / 'public_source_extensions'
extcheck = read(extension / 'inspection.json')
assert extcheck['status'] == 'PASS' and extcheck['source_pdf_matches_existing']
assert extcheck['complete_servo_horn_interface'] == 'BLOCKED'
assert not extcheck['main_applied'] and not extcheck['manufacturing_release']
for name, digest in extcheck['source_files'].items():
    assert sha(ROOT / name) == digest, name
    inputs[name] = digest
for name, digest in extcheck['outputs'].items():
    assert sha(extension / name) == digest, name
    inputs[str((extension / name).relative_to(ROOT))] = digest
inputs[str((extension / 'inspection.json').relative_to(ROOT))] = sha(extension / 'inspection.json')
ps = read(base / 'progressive_staging/screen.json')
vf = read(base / 'vertical_free_feed/screen.json')
for name, d, script, helper in [
    ('progressive_staging', ps, 'plan_CAM_progressive_wire_staging.py', 'plan_CAM_upper_wire_staging.py'),
    ('vertical_free_feed', vf, 'check_CAM_vertical_free_feed.py', 'refine_CAM_root_seating.py'),
]:
    assert d['source_main_sha256'] == protected['mechanical/mori_v1_2.blend']
    assert d['script_sha256'] == sha(A8 / script)
    assert d['helper_sha256'] == sha(A8 / helper)
    assert not d['main_applied'] and not d['manufacturing_release']
    assert d['whole_harness'] == 'BLOCKED'
    for p in [base / name / 'screen.json', A8 / script, A8 / helper]:
        inputs[str(p.relative_to(ROOT))] = sha(p)
assert ps['source_target_seating_sha256'] == sha(base / 'aligned_tails/verification.json')
assert ps['curves_sha256'] == sha(base / 'progressive_staging/curves.npz')
inputs[str((base / 'progressive_staging/curves.npz').relative_to(ROOT))] = ps['curves_sha256']
assert ps['status'] == 'BLOCKED' and len(ps['rows']) == 41
assert ps['continuous_motion'] == ps['staged_radius_certificate'] == 'NOT_TESTED'
assert vf['status'] == 'PASS' and len(vf['rows']) == 8
assert all(r['status'] == 'PASS' and not r['failures'] for r in vf['rows'])
assert vf['target_seating_source_sha256'] == sha(base / 'aligned_tails/verification.json')
assert vf['neck_pose_source_sha256'] == sha(A8 / 'assembly_feed_v3/relaxation_curves.npz')
assert vf['complete_neck_sequence_identity'] == vf['actual_terminal_profile'] == 'NOT_TESTED'
assert vf['body_end_slack_supply_and_hands'] == 'NOT_TESTED'
dr = read(base / 'delayed_recovery/screen.json')
assert dr['source_main_sha256'] == protected['mechanical/mori_v1_2.blend']
assert dr['source_target_seating_sha256'] == sha(base / 'aligned_tails/verification.json')
assert dr['source_progressive_sha256'] == sha(base / 'progressive_staging/screen.json')
assert dr['script_sha256'] == sha(A8 / 'plan_CAM_delayed_recovery_staging.py')
assert dr['helper_sha256'] == sha(A8 / 'plan_CAM_progressive_wire_staging.py')
assert dr['curves_sha256'] == sha(base / 'delayed_recovery/curves.npz')
assert dr['status'] == 'BLOCKED' and dr['selected_lead_mm'] is None
assert [t['lead_pulse_max_mm'] for t in dr['trials']] == [4., 8., 12., 16.]
assert all(t['status'] == 'BLOCKED' and len(t['rows']) == 1 for t in dr['trials'])
assert not dr['main_applied'] and not dr['manufacturing_release']
assert dr['whole_harness'] == 'BLOCKED'
assert dr['continuous_motion'] == dr['staged_radius_certificate'] == 'NOT_TESTED'
for p in [base / 'delayed_recovery/screen.json', base / 'delayed_recovery/curves.npz',
          A8 / 'plan_CAM_delayed_recovery_staging.py']:
    inputs[str(p.relative_to(ROOT))] = sha(p)
ordered_path = base / 'ordered_feed_recovery/publication.json'
ordered = read(ordered_path)
assert ordered['status'] == 'PASS' and ordered['feed_finite_positions'] == 4205
assert ordered['recovery_finite_positions'] == 41 and ordered['retraction_sweeps'] == 4
assert ordered['script_sha256'] == sha(A8 / 'publish_CAM_ordered_feed.py')
assert ordered['feed_continuous'] == ordered['recovery_continuous'] == 'PASS'
assert ordered['feed_continuous_intervals'] == 1228 and ordered['recovery_continuous_intervals'] == 256
assert ordered['body_supply'] == 'BLOCKED' and ordered['body_supply_audit'] == 'PASS'
assert ordered['larger_contact_seating'] == ordered['larger_contact_forming'] == 'PASS'
assert ordered['larger_contact_seating_intervals'] == 256 and ordered['larger_contact_forming_intervals'] == 1735
for name, digest in ordered['source_files'].items():
    assert sha(ROOT / name) == digest
    inputs[name] = digest
inputs[str(ordered_path.relative_to(ROOT))] = sha(ordered_path)
inputs[str((A8 / 'publish_CAM_ordered_feed.py').relative_to(ROOT))] = sha(A8 / 'publish_CAM_ordered_feed.py')
body_review_path=base/'body_supply/complete_head/publication.json'
body_review=read(body_review_path)
assert body_review['status']=='PASS' and body_review['script_sha256']==sha(A8/'publish_CAM_body_supply_review.py')
assert body_review['full_head_old_sequence']==body_review['larger_contact_neck']=='BLOCKED'
assert body_review['larger_neck_candidate']=='PASS' and not body_review['larger_neck_candidate_main_applied']
assert body_review['complete_four_wire_material_present'] and body_review['full_material_supply']=='BLOCKED'
for name,digest in body_review['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in body_review['outputs'].items():assert sha(body_review_path.parent/name)==digest
inputs[str(body_review_path.relative_to(ROOT))]=sha(body_review_path)
inputs[str((A8/'publish_CAM_body_supply_review.py').relative_to(ROOT))]=sha(A8/'publish_CAM_body_supply_review.py')
cam_first_dir=base/'body_supply/complete_head/bridge_wire_stock/install_order/review'
cam_first=read(cam_first_dir/'publication.json')
assert cam_first['status']=='PASS' and cam_first['body_finite_positions']==408 and cam_first['bare_plug_paths']==6
assert cam_first['free_sweep_nominal_margin_mm']==.3 and cam_first['full_harness']=='BLOCKED'
assert cam_first['script_sha256']==sha(A8/'publish_CAM_first_order_review.py')
for name,digest in cam_first['source_files'].items():assert sha(ROOT/name)==digest
for name,digest in cam_first['outputs'].items():assert sha(cam_first_dir/name)==digest
inputs[str((cam_first_dir/'publication.json').relative_to(ROOT))]=sha(cam_first_dir/'publication.json')
inputs[str((A8/'publish_CAM_first_order_review.py').relative_to(ROOT))]=sha(A8/'publish_CAM_first_order_review.py')
h02_path=cam_first_dir.parent/'H02_preinstalled/publication.json'
h02=read(h02_path)
assert h02['status']=='PASS' and h02['H02_preinstalled_candidate']=='PASS'
assert cam_first['H02_preinstalled_publication_sha256']==sha(h02_path)
assert h02['H02_open_deck_positions']==201 and h02['remaining_later_harnesses']==['H01','H04']
for name,digest in h02['source_files'].items():assert sha(ROOT/name)==digest
for name,digest in h02['outputs'].items():assert sha(h02_path.parent/name)==digest
inputs[str(h02_path.relative_to(ROOT))]=sha(h02_path)
order_diagnostics_path=cam_first_dir.parent/'body_fixed_CAM/publication.json'
order_diagnostics=read(order_diagnostics_path)
assert order_diagnostics['status']=='PASS'
assert order_diagnostics['script_sha256']==sha(A8/'publish_CAM_body_order_diagnostics.py')
assert order_diagnostics['complete_assembly']=='BLOCKED'
for name,digest in order_diagnostics['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in order_diagnostics['outputs'].items():
    assert sha(order_diagnostics_path.parent/name)==digest
inputs[str(order_diagnostics_path.relative_to(ROOT))]=sha(order_diagnostics_path)
inputs[str((A8/'publish_CAM_body_order_diagnostics.py').relative_to(ROOT))]=sha(A8/'publish_CAM_body_order_diagnostics.py')
segmented_path=cam_first_dir.parent/'feed_pose_packing/publication.json'
segmented=read(segmented_path)
assert segmented['status']=='PASS' and segmented['verified_single_poses']==2
assert segmented['script_sha256']==sha(A8/'publish_CAM_segmented_feed_review.py')
assert segmented['complete_attached_assembly']=='BLOCKED' and not segmented['main_applied']
for name,digest in segmented['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in segmented['outputs'].items():assert sha(segmented_path.parent/name)==digest
inputs[str(segmented_path.relative_to(ROOT))]=sha(segmented_path)
inputs[str((A8/'publish_CAM_segmented_feed_review.py').relative_to(ROOT))]=sha(A8/'publish_CAM_segmented_feed_review.py')
joint_path=cam_first_dir.parent/'CAM_H02_joint_lift/publication.json'
joint=read(joint_path)
assert joint['status']=='PASS' and joint['joint_wire_finite_lift']=='PASS'
assert joint['joint_wire_lift_positions']==37 and joint['shell_connector_path']=='BLOCKED'
assert joint['complete_attached_assembly']=='BLOCKED' and not joint['main_applied']
assert joint['script_sha256']==sha(A8/'publish_CAM_H02_joint_review.py')
for name,digest in joint['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in joint['outputs'].items():assert sha(joint_path.parent/name)==digest
inputs[str(joint_path.relative_to(ROOT))]=sha(joint_path)
inputs[str((A8/'publish_CAM_H02_joint_review.py').relative_to(ROOT))]=sha(A8/'publish_CAM_H02_joint_review.py')
shell16_path=cam_first_dir.parent/'shell16_joint_feed/publication.json'
shell16=read(shell16_path)
assert shell16['status']=='PASS' and shell16['rigid_sample_records']==297
assert shell16['prefix_wire_status']=='PASS' and shell16['prefix_wire_sample_records']==98
assert shell16['complete_attached_assembly']=='BLOCKED' and not shell16['main_applied']
assert shell16['script_sha256']==sha(A8/'publish_shell16_review.py')
for name,digest in shell16['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in shell16['outputs'].items():assert sha(shell16_path.parent/name)==digest
inputs[str(shell16_path.relative_to(ROOT))]=sha(shell16_path)
inputs[str((A8/'publish_shell16_review.py').relative_to(ROOT))]=sha(A8/'publish_shell16_review.py')
packing_path=cam_first_dir.parent/'shell16_packing_diagnosis/publication.json'
packing=read(packing_path)
assert packing['status']=='PASS' and packing['complete_attached_assembly']=='BLOCKED'
assert packing['script_sha256']==sha(A8/'publish_shell16_packing_review.py')
assert not packing['main_applied'] and not packing['manufacturing_release']
for name,digest in packing['source_files'].items():
    assert sha(ROOT/name)==digest;inputs[name]=digest
for name,digest in packing['outputs'].items():assert sha(packing_path.parent/name)==digest
inputs[str(packing_path.relative_to(ROOT))]=sha(packing_path)
inputs[str((A8/'publish_shell16_packing_review.py').relative_to(ROOT))]=sha(A8/'publish_shell16_packing_review.py')
guided_path=base/'body_supply/complete_head/bridge_wire_stock/PH_guided_wire_entry/publication.json'
guided=read(guided_path)
assert guided['status']=='PASS' and guided['PH_with_full_CAM_wire_continuous']=='PASS'
assert guided['full_harness']=='BLOCKED' and not guided['main_applied']
assert guided['script_sha256']==sha(A8/'publish_PH_guided_wire_review.py')
for name,h in guided['source_files'].items():assert sha(ROOT/name)==h,name;inputs[name]=h
for name,h in guided['outputs'].items():
    p=guided_path.parent/name;assert sha(p)==h;inputs[str(p.relative_to(ROOT))]=h
inputs[str(guided_path.relative_to(ROOT))]=sha(guided_path)
native_order_path=base/'body_supply/complete_head/bridge_wire_stock/bridge_tail_order_review/publication.json'
native_order=read(native_order_path)
assert native_order['status']=='PASS' and native_order['original_bridge_order']=='BLOCKED'
assert native_order['bearing_deferred_order']=='BLOCKED' and not native_order['main_applied']
assert native_order['script_sha256']==sha(A8/'publish_bridge_tail_order_review.py')
for name,h in native_order['source_files'].items():assert sha(ROOT/name)==h,name;inputs[name]=h
for name,h in native_order['outputs'].items():
    p=native_order_path.parent/name;assert sha(p)==h;inputs[str(p.relative_to(ROOT))]=h
inputs[str(native_order_path.relative_to(ROOT))]=sha(native_order_path)
rel = '../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating'
md = f'''# 供应商按图制作：资料和设计进度分开记录

2026-10-05。供应商按图制作已经确定，不再等待制造方式确认。MORI 的线路、分支、长度基准和装配图由项目完成。未发送供应商消息或下单。

## 最新：原桥座的简化套线顺序未通过

已用原M1.47实体复核：带轴承桥座直接套线、4组左侧临时排布、轴承后装的4组直立排布均未通过。所试线尾位置的上下可通过范围错开；一处端子请求空间碰底面，另一候选的一处导线中心已在桥座材料内。中心小孔仍存在，不是桥座完全封闭。上壳的5条所试路线也未通过，涉及后接口插头对IMU线及线端对上壳的问题。
这只排除了具体测试路线；没有扩大孔口、改小配件或修改主模型。之前的PH带线插接局部通过保留，完整穿颈/装配还没接起来。
[原桥座剖面与装配诊断]({rel}/body_supply/complete_head/bridge_wire_stock/bridge_tail_order_review/index.html)。

## 此前：PH带四根完整导线的插接阶段通过

采用自由线尾先留在颈部外侧的顺序，PH随圆滑路径转向。171个全线位置、174个全线连续区间和875个插头/线根扫掠包络通过；保持原名义总长，未修改结构。
随后穿颈、H01/H04后装、其他跨关节线、FFC、扎带与手部工具仍未完成，完整线束图继续BLOCKED。
[带线动作图和连续检查]({rel}/body_supply/complete_head/bridge_wire_stock/PH_guided_wire_entry/index.html)。

## 此前：找到PH上方插接路径，继续核对带线装配

裸PH胶壳从上方开口进入的7段平移路径已通过封闭实体扫掠复核，采用H02/H03先装、H01/H04延后的顺序。四根导线前5mm直段另有24段扫掠通过，余下柔性导线随插头移动仍需检查。
颈部CAM1/2和身体插头附近CAM3/4的原局部间隙问题已单独定位；提前调高度和扭线仍未解决原带线后移路线。
又比较了上壳保持打开后连接身体端PH的顺序，裸胶壳结果和明确延后的H01/H04分别列出，不能当作完整线束通过。
[局部三向图、候选结果与范围]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/shell16_packing_diagnosis/index.html)。主模型和制造放行状态保持。

## 此前：外壳与桥的四段刚体路径已走通，完整线束仍待衔接

插头包络与零件尺寸保持。外壳倾斜16°并抬高14mm，桥上抬18mm，二者一起后移20mm，再向上提离。
297个刚体检查记录、294个不同位置通过，包含身体/后板插头与14根固定身体线。
前两段含四根CAM线的61+37个检查记录通过；CAM后移的单根分步路径也已取得结果，但四根线共同移动及后续提离仍未整体完成。
[装配顺序图、来源核对和每段检查范围]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/shell16_joint_feed/index.html)。
主模型M1.47和制造图保持；使用既有未采用的结构候选，完整线束仍BLOCKED。

## 此前：CAM 与 H02 抬升走向已配合，暴露了外壳插头路径问题

H02第二根线只调整中段，两个端口、针序、端后直段和弯曲半径保持，名义路线增加约0.55mm。
4根CAM与2根H02在桥上抬0–18mm的37个有限位置通过线形检查；H02的201个提前装入位置、
408个身体位置及130个头部姿态复核通过。这些是分别限定的检查，不能当作整套装配通过。
补查后板插头随外壳移动时，原保持位置的J2插头保守包络与Load Frame有约0.03635mm³重叠。
后移桥的弯线、继续抬高外壳及后板带线拔插时机仍需处理。
[新旧走向、阶段检查与插头重叠图]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/CAM_H02_joint_lift/index.html)。
这部分属于项目尚未完成的设计，不应归为等待实物；主模型和制造图状态保持。

## 此前：CAM 分段送线的位置检查与中途问题

保持身体端 PH 胶壳不动，桥上移18mm、以及再后移14mm，两处分别找到四根CAM线的排布。
两处对当前零件、14根身体线、29个插头空间、自绕、邻线及端子占位检查通过，完整名义线长保留。
当时从坐稳位置逐步抬升尚未闭合；第4根线与H02的走向问题现已在上面的联合研究中取得37位置通过。
六种收弯时序经细化仍有间隙不足或相交；还补查了临时降低中段的候选。
两处独立位置通过不代表完整装配通过。[对比图、检查与限制]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/feed_pose_packing/index.html)。

## H02 提前连接，H01 / H04 继续处理

六个裸插头路径加上现有名义线长后，H02 和 H04 部分位置不满足必要长度下界；裸插头通过不能代表整束可装。
H02 已有较低的新走向，保留针序、端点和弯曲半径，在开敞机身内提前接好。两端插头与完整线形的
201个装入位置、随后408个身体装配位置和130个头部姿态复核通过；不改打印结构或PCB。
H01/H04 的10根导线尚未完成带线装配工序。进一步尝试提前连接：H01 每根821组，
H04每根106组，均未形成完整通过的组合。让 CAM 插头和导线留在身体侧、桥单独运动，
又在桥上移18mm的保存位置发现实际相交。需要设计分段送线，不能直接沿用固定线形的桥路径。
[进一步诊断与范围]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/body_fixed_CAM/index.html)。
人手工具、线尾、扎带和供应商裁线图仍未完成。
[H02走向与线长复核]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/H02_preinstalled/index.html)。
此前六条裸插头路径作为对照保留，不能直接用于完整线束制作。
[顺序与路径图]({rel}/body_supply/complete_head/bridge_wire_stock/install_order/review/index.html)。

相机支架上沿另有局部清理候选，已通过名义几何复核，仍等待用户采用；主模型保持。
[相机上沿候选](../../camera_top_clearance/index.html)。

## 其他局部候选与此前装配检查

同一较大端子预留现在已有独立的颈部候选：临时下弯道改为 R10、竖直起点上移1 mm，
扩宽两件已有候选的通道；四方向连续穿入、颈部尾线和回位检查通过，保存网格已复核。
端子/导线间隙保守下界约0.308/0.306 mm；轴颈径向壁厚最小样本从1.60变为1.48 mm。
这是未采用的局部几何结果，强度、全长供线和整机顺序尚未完成。
[候选剖面与证据]({rel}/body_supply/complete_head/larger_neck_candidate/index.html)。

此前[分步装配与完整线长补查]({rel}/body_supply/complete_head/split_assembly/index.html)：
22件偏航与舵盘先装、14件头托与CAM后装的有限刚体路径通过。四根名义全长及共同PH插头已经
建入，约153–162mm线尾先存放在头部上方；当时身体线束已装的动作存在间隙或相交问题。
LCD代理姿态误报已修正。相机上角候选和新的CAM先装顺序见上节；主模型和主动画保持。

上部已通过的连续检查仍保留。原颈部路径此前沿用较小端子方盒，换成同样的
1×1.8×4.1 mm 空间分配后，下弯道首个间隙不足位置约0.252 mm，小于0.3 mm。
保持打印件不变的49组位置/滚转角尝试均未通过。该尺寸是请求的空间预留，
不是厂家完整压接成品外形。

原身体上壳动作只检查了承重桥，加入完整头部后有碰撞；10种同步动作和下部
框架直装也未通过。仍需设计分步穿线和身体端接入，不能把这些未完成设计归为
等实物。[本轮剖面与结果]({rel}/body_supply/complete_head/index.html)。

## 新取得的厂家资料

已从 [JST 官方网站](https://www.jst-mfg.com/product/pdf/eng/eAPSH.pdf)下载 APSH 目录，并查看第 1 页 Contact 图。图中端子为 **SSH-003T-P0.2-H**，与 SH 目录同料号；没有改选 APSH 胶壳。

相比 SH 简版目录，该图给出接触段及压接翼的轴向位置，并多出 **1.55 mm 的轴向尺寸**。它不是整个端子的高度。0.8 mm 宽、1.35 mm 接触体高度和 3.9 mm 长度均为图示名义值；接触体下方的小突出和压接后轮廓仍没有完整尺寸、公差。旧方盒不能因此升级为真实端子的完整最大外形。

本目录也明确列出 AP-K2N、MKS-L-10-3 和 APLMK SSH/L003-02 工装，以及 32–28 AWG / 0.4–0.8 mm 绝缘外径的适用范围。这些是可交供应商核对的来源，不能代替实际线材与模具组合的工艺确认。

[保存的厂家 PDF](../ssh_catalogue_addendum/apsh/JST_eAPSH.pdf) · [原页预览](../ssh_catalogue_addendum/apsh/page1_mupdf.png) · [尺寸解读](../ssh_catalogue_addendum/apsh/README.md) · [下载及哈希记录](../ssh_catalogue_addendum/apsh/retrieval.json)

复查 [JST LBT 官方目录](https://www.jst-mfg.com/product/pdf/eng/eLBT.pdf)后，确认下载与项目已存 PDF 逐字节相同，复用原文件，没有新版本或新增尺寸。第 2 页同料号 SSH-003T-P0.2-H 的尺寸与工装信息已记录；LBT 的 28 AWG / 0.6–0.8 mm 应用范围与 SH/APSH 的 32–28 AWG / 0.4–0.8 mm 分开保留，没有据此改选 MORI 线材或胶壳。[既有核对说明](../ssh_catalogue_addendum/README.md) · [原图](../ssh_catalogue_addendum/contact_page2.png) · [本次复查](../ssh_catalogue_addendum/live_recheck_142240.json)

### 新核对 M5Stack 的舵机资料和摇臂模型

[M5Stack 官方 StackChan 页面](https://docs.m5stack.com/en/base/StackChan_Body)提供 SCS0009 PDF 和结构仓库。下载的 PDF 与项目已有 A/0 规格书逐字节相同；已查看第 7 页，内容为 **No Accessories**，不是新增的配套舵盘图。

官方仓库另有自己的 `StackChan-ServoArm.stl`。已下载并按 Git blob 哈希核对；3744 个三角面，剖面确有带齿孔，径向轮廓的主要周期为 20。STL 不携带单位声明，不能把数值观察升级成飞特齿形、公差或 MORI 配套认证。它提供了一个官方整机连接参考，但还缺型号配套、材料/工艺和轴向装配确认，未替换主模型。

[M5Stack 原始摇臂](../public_source_extensions/StackChan-ServoArm.stl) · [模型预览](../public_source_extensions/m5_arm_views.png) · [剖面](../public_source_extensions/m5_arm_section.png) · [检查记录](../public_source_extensions/inspection.json)

另已实际读取 JST 德国站的 SSH 端子与 SHR-04V-S 胶壳页面，只有规格表，没有找到逐型号图纸/CAD 下载链接。TE 2151515 工装图的公开索引可检索，实际 PDF 下载仍失败；未将索引片段当作已取得、已检查的工艺图。

## 找到入口但尚未取得的文件

本次再次打开 [JST SH 官方页](https://www.jst-mfg.com/product/index.php?lang=2&series=231)的端子逐型号图、SHR-04V-S STEP 和 CHM 专用手册链接。三个入口均显示邮件附件申请页，需要填写联系资料；没有返回相应图纸。另核对 [JST 英国 SH 页面](https://www.jst.co.uk/productSeries.php?pid=7929)，其专用手册和2D/3D入口仍指向上述日本官网申请流程。未提交表单。应记录为“入口已找到、文件尚未取得”，不能称为资料不存在，也不能假称已下载。

微雪 [CAM 资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)仍提供 V1/V1.1 原理图；本次未在该页找到完整相机 FPC 尺寸图。SCS0009 的舵盘、CAM 实际板端连接器料号等缺项仍见[原资料清单](../../supplier_made_harness/SOURCE_REVIEW.md)。

## 现在仍要由项目完成的装配设计

**上部候选已有进展：**按几何槽位 3→2→1→0 逐根穿入，先暂缓上端收拢，再一起回到固定位置。较大端子请求空间通过 1228 个穿入连续区间和 256 个回位连续区间；同样预留尺寸的后续入座 256 个连续区间、四段弯线 1735 个连续区间也已通过。弯线调整了两处临时动作，结构和最终线形不变。本轮已补建四根完整名义线长、上方暂存线尾及共同PH插头；完整身体供线过程仍未通过，不是再加额外裁线长度。扎带和真实端子入壳仍未完成。[上部路线与材料账]({rel}/ordered_feed_recovery/index.html) · [后续尺寸统一复核]({rel}/large_contact_downstream/index.html)。

以下保留旧方案的具体失败范围，不代表新候选仍以同样方式失败：

| 具体尝试 | 检查范围 | 结果 |
|---|---|---|
| 端子沿最终上部弯线穿入 | 4 槽位 × 2 朝向 × 2 明示空间分配，共 16 组 | 16 组均未通过；有结构或邻线问题 |
| 先向上引出，再同步整理四线 | 21 个位置 | 未通过；整理途中对俯仰支架的预留间隙不足 |
| 整理时临时上抬弯曲段 | 2 / 3 / 4 mm 三种最大抬高量，各 21 个位置 | 均未通过；支架或舵机的间隙问题仍在 |
| 颈部出口先竖直引出端子 | 4 槽位 × 2 种明示空间分配，整段扫掠 | 8 组局部通过；实际端子外形、下方供线和手部操作未验证 |
| 从下往上逐段整理导线 | 41 个位置 | 未通过；中段支架和后段邻线的间隙界限不足 |
| 整理中先延长临时切线，再转向竖直 | 4 / 8 / 12 / 16 mm 四种最大延长量 | 四种均在首个检查位置未通过；未改打印件 |

保持了离散线段总长，机器人零件没有改变；只按工序暂不装根部扎带。检查中的 0.002 mm 数值余量是临时筛查分配，尚无完整积分误差证明；21 个位置也不是连续运动证明。记录里继承的目标线形半径值不能当作整个暂态线形的半径认证。间隙未达标不一概解释为实物相撞，失败也不证明所有装法都不可行。

端子两种检查对象分别为旧名义方盒和额外请求的空间分配。后者不是厂家最大尺寸，也不是把端子放大后认定为完整外形。没有因这些尝试失败而修改打印件、孔位或主模型。

竖直引出使用未应用的 J3M/CAM 研究几何，暂未安装根部扎带；端子对打印结构检查 0.3 mm 余量，对其他导线和端子检查名义不相交。整段方盒扫掠的局部通过不能代表完整穿线或真实端子入壳。逐段整理采用临时 0.003 mm 曲线误差分配，41 个位置不是连续证明；末段较保守的间隙界限未过，不等于已证明原目标线形发生实体相交。

[端子穿入诊断]({rel}/upper_terminal_feed/screen.json) · [直接整理]({rel}/upright_staging/screen.json) · [临时抬高整理]({rel}/raised_staging/screen.json) · [已完成的局部入座]({rel}/aligned_tails/README.md)

[竖直引出检查]({rel}/vertical_free_feed/screen.json) · [逐段整理诊断]({rel}/progressive_staging/screen.json)

延后转向的四个候选仍在俯仰支架或局部入线座附近未达到既定间隙；它们只排除了所测试的动作，不证明所有装法都不可行。[诊断记录]({rel}/delayed_recovery/screen.json)。该尝试与前面的 41 个位置使用临时 0.003 mm 曲线误差分配；都不构成全程曲率或连续装配证明。

完整穿线、扎带穿绕与收紧、真实端子入壳、其他七根跨关节线、LCD/相机 FPC 和最终裁线尺寸仍未完成。制造图继续 BLOCKED；不能全部归到“等待实物”。主模型、配置和硬件合同保持，来源校验见[本次记录](verification.json)。
'''
(OUT / 'README.md').write_text(md)
title = 'MORI · 供应商资料与尚未完成的装配设计'
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#233c3c;background:#f5f7f6;max-width:980px;margin:32px auto;padding:0 24px 60px}}a{{color:#086879}}section{{padding:20px;background:white;border-radius:10px;margin:22px 0}}.note{{background:#fff0dc}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ccd8d5}}table{{border-collapse:collapse;width:100%}}img{{width:100%;max-width:760px}}p{{margin:10px 0}}</style>
<p><a href="../index.html">← 线束研究</a> · <a href="../../supplier_made_harness/index.html">供应商资料总表</a></p>
<h1>供应商按图制作：资料在补，装配图仍要完成</h1>
<section class="note"><p>供应商制作方式已确定。长度、分支和装配要求由项目设计；不能把还没完成的设计统称为“等实物”。主模型 M1.47 未改，尚无制造图放行。</p></section>
<section><h2>最新：找到PH上方插接路径，带线装配继续补齐</h2><p>裸PH胶壳从上方开口进入的7段平移路径，已通过封闭实体扫掠复核。H02/H03先装、H01/H04延后；四根导线前5mm直段的24段扫掠通过，余下柔性导线随动尚未检查。</p><p>颈部CAM1/2和身体插头旁CAM3/4的原局部问题已定位，提前调整高度、临时扭线仍未使原带线后移路线通过。</p><p>另比较保持上壳打开、后连接身体端PH的顺序，以及明确延后H01/H04的候选。裸胶壳检查和完整带线装配分开记录。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/shell16_packing_diagnosis/index.html">查看局部图、候选结果和范围</a>。主模型保持M1.47，裁线图尚未放行。</p></section>
<section><h2>此前：外壳与桥的四段刚体路径已走通</h2><p>保留原插头包络，采用外壳16°/抬高14mm、桥上抬18mm，再一起后移20mm并提离。297个刚体检查记录通过，包含后板插头和14根固定身体线。</p><p>前两段含CAM导线的61+37个检查记录也通过。后续四根线的共同后移、竖直提离和其他线束仍未全部完成。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/shell16_joint_feed/index.html">查看顺序图、来源核对和各阶段范围</a>。主模型M1.47与制造图保持。</p></section>
<section><h2>此前：CAM与H02的37个抬升位置通过</h2><p>只调整H02第二根线的中段，端口、针序和弯曲半径保持，名义路线增加约0.55mm。四根CAM与两根H02在桥上抬0–18mm的37个有限位置通过线形检查；新H02的提前装入和后续占用复核也通过。</p><p>该阶段补查暴露了J2插头随外壳运动的问题；其刚体后续路径见上节，完整线束仍未闭合。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/CAM_H02_joint_lift/index.html">查看此前走向与插头重叠图</a>。</p></section>
<section><h2>此前：CAM分段送线的两个独立排布</h2><p>桥上移18mm、再后移14mm，两处曾分别找到四根线的排布。原第4根线与H02的中途问题已在上述联合研究中取得进展；两个独立端点仍不能代替完整后移过程。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/feed_pose_packing/index.html">此前排布和失败证据</a>。</p></section>
<section><h2>此前：H02先连接，H01/IMU线束继续处理</h2><p>线长复核发现原H02/H04裸插头路径部分位置不够长。H02采用更低走向，在开放机身内先接好：201个带线装入位置、随后408个身体位置及130个头部姿态通过。打印件与PCB不改；H01/H04的10根后装导线、人手工具、固定与其他线束仍需完成。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/H02_preinstalled/index.html">查看此前H02走向与线长问题</a> · <a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/review/index.html">此前裸插头路径对照</a>。相机支架另有<a href="../../camera_top_clearance/index.html">上沿清理候选</a>，待用户采用；主模型保持。</p></section>
<section class="note"><h2>进一步诊断：需要分段送线动作</h2><p>H01每根821组、H04每根106组提前连接候选，尚未形成完整通过的组合。CAM留在身体侧、桥单独移动也不能直接套用原路径：桥上移18mm时与导线相交。H02已有候选保留，完整带线装配仍未完成。</p><p><a href="{rel}/body_supply/complete_head/bridge_wire_stock/install_order/body_fixed_CAM/index.html">查看三种尝试的具体范围和失败证据</a>。这些是项目设计问题，不是只能等待厂家资料或实物。</p></section>
<section><h2>此前：分步装配与完整线长</h2><p>22件偏航与舵盘先装、14件头托与CAM后装的有限刚体路径通过。四根全长及PH插头已建入，153–162mm线尾暂存在头部上方。当时身体线束已装的动作有间隙/相交问题；新顺序见上节。</p><p><a href="{rel}/body_supply/complete_head/split_assembly/index.html">此前顺序图、完整线长和局部剖面</a>。未改主模型或主动画。</p></section>
<section class="note"><h2>颈部局部候选通过，完整装配仍未完成</h2><p>同一较大端子预留采用临时R10弯道及两件既有候选通道扩宽后，四方向连续穿入、导线回位与保存网格复核通过。端子/导线间隙下界约0.308/0.306mm；轴颈径向壁厚最小样本1.60→1.48mm，强度未验证，候选未应用主模型。</p><p><a href="{rel}/body_supply/complete_head/larger_neck_candidate/index.html">查看最新候选</a>。原整头/上壳动作仍有碰撞；身体余线、PH胶壳、完整顺序与其他线路仍待设计。<a href="{rel}/body_supply/complete_head/index.html">原失败证据与范围</a>保留。</p></section>
<section><h2>新取得同料号端子的官方细节图</h2><p>JST APSH 目录列出相同的 SSH-003T-P0.2-H，补充接触段和压接翼的轴向标注。图上的 1.55 mm 是轴向尺寸，并非总高度。接触体下方小突出及压接成品的完整外形仍未标全。</p>
<p><a href="../ssh_catalogue_addendum/apsh/JST_eAPSH.pdf">打开厂家原 PDF</a> · <a href="../ssh_catalogue_addendum/apsh/README.md">尺寸与工装信息</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/eAPSH.pdf">官方来源</a></p>
<img src="../ssh_catalogue_addendum/apsh/page1_mupdf.png" alt="JST APSH 官方目录第1页，底部是 SSH-003T-P0.2-H 端子图">
<p>专用手册、逐型号端子图和胶壳 STEP 的官方入口已找到，但返回的是邮件申请表，尚未取得文件。微雪当前资源页未列出完整相机 FPC 尺寸文件。</p></section>
<section><h2>官方 LBT 资料复查：文件未更新</h2><p>再次取得的 PDF 与已存文件逐字节相同，复用原文件，没有新增尺寸。第 2 页同料号 SSH-003T-P0.2-H 的局部尺寸及工装信息已记录。此目录的应用范围更窄，独立保留；没有据此变更 SH 胶壳、线材或实际压接工艺。</p><p><a href="../ssh_catalogue_addendum/README.md">既有核对说明</a> · <a href="../ssh_catalogue_addendum/contact_page2.png">厂家原页</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/eLBT.pdf">官方 PDF</a></p></section>
<section><h2>另找到官方整机的摇臂模型</h2><p>M5Stack 发布的 SCS0009 PDF 与已有版本相同，配件页仍为 No Accessories。其结构仓库另有带齿孔的 StackChan-ServoArm，可以参考连接形式；它并非我们采购套装的配套舵盘定稿，未应用主模型。</p><p><a href="https://docs.m5stack.com/en/base/StackChan_Body">官方资料入口</a> · <a href="../public_source_extensions/inspection.json">来源与剖面检查</a></p><img src="../public_source_extensions/m5_arm_views.png" alt="M5Stack 原始摇臂 STL 两面视图，未缩放、未用于主模型"><p><a href="../public_source_extensions/m5_arm_section.png">查看齿孔剖面</a> · <a href="../public_source_extensions/StackChan-ServoArm.stl">原 STL</a></p></section>
<section><h2>上部候选：统一预留尺寸的穿线与弯线</h2><p>按几何槽位 3→2→1→0 穿入，先暂缓上端收拢。同样较大端子预留尺寸下，穿入 1228、回位 256、入座 256、四段弯线 1735 个连续区间通过。弯线仅调整两处临时装配动作。</p><p>本轮已补建完整名义线长、上方暂存线尾和PH插头，身体供线过程仍未通过；不是额外裁线长度。扎带和真实端子入壳仍待完成。</p><p><a href="{rel}/ordered_feed_recovery/index.html">上部检查和材料账</a> · <a href="{rel}/large_contact_downstream/index.html">后续尺寸统一复核</a></p></section>
<section><h2>保留的旧方案诊断</h2><table><tr><th>路线</th><th>检查</th><th>结论</th></tr>
<tr><td>端子沿弯曲路线引入</td><td>16 组</td><td>均未通过结构或邻线检查</td></tr>
<tr><td>四线先竖直，再同步整理</td><td>21 个位置</td><td>支架间隙不足</td></tr>
<tr><td>整理时临时抬高 2、3、4 mm</td><td>3 × 21 个位置</td><td>仍有支架或舵机间隙问题</td></tr>
<tr><td>颈部出口先竖直引出端子</td><td>8 组整段方盒扫掠</td><td>局部通过；真实端子外形及下方供线仍待完成</td></tr>
<tr><td>从下向上逐段整理</td><td>41 个位置</td><td>支架与邻线间隙界限不足</td></tr>
<tr><td>临时延长切线后再转竖直</td><td>4、8、12、16 mm 四种候选</td><td>四种均在首个位置未通过；支架或入线座间隙不足</td></tr></table>
<p>整理动作目前只做有限位置诊断；竖直端子行程用整段扫掠检查。两者不可混为完整工序通过。研究使用未采用的线座候选，主模型未改；真实端子、扎带穿绕及完整装配仍未完成。</p>
<p><a href="{rel}/upper_terminal_feed/screen.json">端子诊断</a> · <a href="{rel}/upright_staging/screen.json">同步整理</a> · <a href="{rel}/raised_staging/screen.json">上抬整理</a> · <a href="{rel}/aligned_tails/README.md">局部入座结果</a></p></section>
<p><a href="{rel}/vertical_free_feed/screen.json">竖直引出检查</a> · <a href="{rel}/progressive_staging/screen.json">逐段整理诊断</a> · <a href="{rel}/delayed_recovery/screen.json">延后转向诊断</a></p>
<p><a href="README.md">完整说明及证据边界</a> · <a href="verification.json">来源校验记录</a></p></html>'''
native_order_section=f'''<section><h2>最新：原桥座的简化套线顺序未通过</h2><p>原M1.47桥座带轴承直接套线、4组左侧线尾排布及轴承后装的4组排布均未通过。所试线尾位置的上下可通过范围错开，中心小孔仍存在；端子请求空间碰底面，另一候选的导线中心在桥座材料内。上壳5条测试路线亦未通过。</p><p>这些结果只排除所试路线。之前PH带线插接局部通过仍有效，完整穿颈和装配仍未完成；主模型未改。<a href="{rel}/body_supply/complete_head/bridge_wire_stock/bridge_tail_order_review/index.html">查看原实体剖面和具体诊断</a>。</p></section>'''
guided_section=native_order_section+f'''<section><h2>此前：PH带四根完整导线的插接阶段通过</h2><p>自由线尾先留在颈部外侧，PH沿圆滑路径转向。171个全线位置、174个全线连续区间及875个插头/线根扫掠包络通过；原名义总长保持，主模型未改。</p><p>之后穿颈、H01/H04后装、其他跨关节线、FFC、扎带与手部工具仍待完成。<a href="{rel}/body_supply/complete_head/bridge_wire_stock/PH_guided_wire_entry/index.html">查看带线动作图与连续检查</a>。完整制造图尚未放行。</p></section>'''
page=page.replace('<section><h2>最新：找到PH上方插接路径，带线装配继续补齐</h2>',guided_section+'<section><h2>此前：裸PH胶壳的上方插接路径</h2>',1)
(OUT / 'index.html').write_text(page)
for path, digest in protected.items():
    assert sha(ROOT / path) == digest
report = dict(status='PASS', scope='Source receipt and local-route progress publication; not a whole harness or manufacturing pass',
    generated_utc=datetime.now(timezone.utc).isoformat(), script_sha256=sha(SCRIPT), protected_files=protected,
    source_files=inputs, public_APSH_catalogue='RETRIEVED', public_LBT_catalogue='RECHECKED_IDENTICAL',
    LBT_scope='Same SSH part cross-reference only; no SH wire or housing substitution',
    individual_JST_manual_and_CAD='BLOCKED',
    source_dimensions_are_complete_terminal_envelope=False,
    guide_feed_candidates=16, guide_feed_passes=0, upright_positions=21,
    raised_candidates=3, raised_positions_per_candidate=21, raised_candidate_passes=0,
    vertical_free_feed='PASS', vertical_feed_allocations=8,
    vertical_feed_scope=vf['scope'], vertical_feed_receipt_sha256=sha(base/'vertical_free_feed/screen.json'),
    progressive_staging='BLOCKED', progressive_staging_positions=41,
    delayed_recovery_staging='BLOCKED', delayed_recovery_candidates=4,
    ordered_feed_finite='PASS', ordered_feed_positions=ordered['feed_finite_positions'],
    ordered_recovery_finite='PASS', ordered_recovery_positions=ordered['recovery_finite_positions'],
    ordered_retraction_sweep='PASS', ordered_retraction_sweeps=ordered['retraction_sweeps'],
    ordered_boundary_match=ordered['boundary_match'], ordered_continuous='PASS',
    ordered_feed_continuous_intervals=ordered['feed_continuous_intervals'],
    ordered_recovery_continuous_intervals=ordered['recovery_continuous_intervals'],
    ordered_body_supply='BLOCKED',
    body_supply_review_sha256=sha(body_review_path),
    staged_supply_publication_sha256=body_review['staged_supply_publication_sha256'],
    complete_four_wire_material_present=True,full_material_supply='BLOCKED',
    CAM_first_body_finite_positions=408,CAM_first_body_finite_status='PASS',
    later_bare_plug_continuous_paths=6,later_bare_plug_nominal_gap_mm=.3,
    deferred_attached_harness_installation='NOT_TESTED',CAM_first_publication_sha256=sha(cam_first_dir/'publication.json'),
    H02_preinstalled_candidate='PASS',H02_preinstalled_publication_sha256=sha(h02_path),
    H02_open_deck_positions=201,remaining_later_harnesses=['H01','H04'],remaining_later_conductors=10,
    body_order_diagnostics_sha256=sha(order_diagnostics_path),
    H01_preinstalled_screen='BLOCKED',H04_preinstalled_screen='BLOCKED',
    body_fixed_CAM_screen='BLOCKED',segmented_body_wire_feed='BLOCKED',
    segmented_body_wire_feed_publication_sha256=sha(segmented_path),
    segmented_single_pose_count=2,segmented_single_pose_geometry='PASS',
    segmented_temporary_lowering=segmented['temporary_lowering'],
    joint_CAM_H02_publication_sha256=sha(joint_path),
    joint_CAM_H02_lift='PASS',joint_CAM_H02_positions=37,
    joint_CAM_H02_complete_assembly='BLOCKED',rear_J2_shell_path='BLOCKED',
    rear_J2_shell_path_scope='Historical 15-degree path, before shell16 followup',
    shell16_publication_sha256=sha(shell16_path),shell16_rigid_path='PASS',shell16_rigid_records=297,
    shell16_prefix_with_CAM='PASS',shell16_prefix_records=98,
    shell16_back20_four_wires=shell16['back20_four_wire_status'],shell16_complete_assembly='BLOCKED',
    PH_guided_wire_publication_sha256=sha(guided_path),PH_guided_full_wire_continuous='PASS',
    PH_guided_full_wire_intervals=174,PH_guided_finite_positions=171,PH_guided_root_sweeps=875,
    native_bridge_order_publication_sha256=sha(native_order_path),native_bridge_tail_order='BLOCKED',
    shell16_packing_publication_sha256=sha(packing_path),shell16_packing_diagnosis='PASS',
    shell16_stepped_PH_rigid=packing['stepped_PH_rigid'],shell16_stepped_PH_segments=7,
    shell16_stepped_PH_first5mm_leads='PASS',shell16_stepped_PH_lead_segments=24,
    shell16_late_PH_rigid=packing['open_PH_rigid'],shell16_deferred_PH_rigid=packing['deferred_PH_rigid'],
    source_proxy_pose_refresh='PASS',LCD_overlap_after_refresh_mm3=0.,
    full_head_body_sequence='BLOCKED',larger_contact_neck='BLOCKED',
    larger_neck_candidate='PASS',larger_neck_candidate_main_applied=False,
    larger_neck_candidate_publication_sha256=body_review['larger_neck_candidate_publication_sha256'],
    larger_contact_seating='PASS',larger_contact_seating_intervals=256,
    larger_contact_forming='PASS',larger_contact_forming_intervals=1735,
    larger_contact_publication_sha256=ordered['larger_contact_publication_sha256'],
    ordered_publication_sha256=sha(ordered_path),
    public_M5_reference='PASS', actual_servo_horn_interface='BLOCKED',
    initial_feed_to_root_seating='BLOCKED', continuous_staging='NOT_TESTED', staged_radius_certificate='NOT_TESTED',
    whole_harness='BLOCKED', manufacturing_release=False, main_applied=False,
    outputs={name:sha(OUT / name) for name in ['README.md','index.html']})
(OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('SUPPLIER_SOURCE_UPDATE PASS; initial feed BLOCKED; main unchanged', flush=True)
