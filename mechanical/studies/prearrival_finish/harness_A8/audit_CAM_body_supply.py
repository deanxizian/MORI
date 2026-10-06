"""Expose the missing material reserve in the fixed-body upper-feed study.

This is a length/state dependency audit, not a validated reserve-loop model.
The body plug must remain loose until an explicit whole-wire installation
path is designed. A detached head assembly is the next candidate to screen.
"""
from pathlib import Path
import hashlib,json,datetime
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
BASE=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating'
OUT=BASE/'body_supply';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
feed_path=BASE/'shifted_ordered_feed_handle05/screen.json';feed=json.loads(feed_path.read_text())
selected=next(r for r in feed['rows'] if r['allocation']=='requested_space_only' and r['status']=='PASS')
rows=[]
for c in selected['curves']:
    total=float(c['allocation_mm'])
    rows.append(dict(geometric_slot=c['slot'],upper_material_allocation_mm=total,
        neck_staged_upper_length_mm=13.,unrepresented_reserve_before_retraction_mm=total-13.,
        unrepresented_reserve_after_retraction_mm=total,
        unrepresented_reserve_after_full_feed_mm=0.,electrical_pin_assignment='Unchanged; this is a geometric slot, not a pin number'))
old_sequence=ROOT/'mechanical/studies/prearrival_closure/dual_body_sequence.py'
source_text=old_sequence.read_text()
assert "bridge={'Yaw_Base','Yaw_Bearing'}" in source_text
old_report=old_sequence.with_suffix('.json');old=json.loads(old_report.read_text())
main=ROOT/'mechanical/mori_v1_2.blend';main_hash=sha(main);assert main_hash==feed['source_main_sha256']
report=dict(status='BLOCKED',audit_status='PASS',scope='Material reserve and assembly dependency audit; no body reserve geometry checked',
    script_sha256=sha(SCRIPT),source_main_sha256=main_hash,source_feed_sha256=sha(feed_path),
    rows=rows,source_allocation_is_polyline=True,final_cut_lengths=False,
    finding='A fixed body centreline plus a growing upper prefix does not contain the remaining cable material. Endpoint-only checks do not solve this.',
    existing_body_sequence=dict(script=str(old_sequence.relative_to(ROOT)),script_sha256=sha(old_sequence),
        report=str(old_report.relative_to(ROOT)),report_sha256=sha(old_report),
        report_source_matches_current_main=old.get('source_blend_sha256')==main_hash,
        moving_bridge_scope='Yaw_Base, Yaw_Bearing and selected bridge nuts; not a complete prewired head',
        complete_prewired_head_insertion='NOT_TESTED'),
    next_candidate='Prewire the detached head/neck assembly with the body connector loose, then check complete module insertion and final body-side routing',
    required_next_checks=['Full moving-module membership and source solids',
        'Continuous full-wire length, loose-tail and common PH housing poses',
        'Head-module lowering path with wires and temporarily held upper body shell',
        'Final body routing, retention and plug insertion; reverse service path'],
    no_structure_change_authorized_by_this_audit=True,main_applied=False,
    body_end_material_supply='NOT_TESTED',whole_harness='BLOCKED',manufacturing_release=False)
(OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
table='\n'.join(f"| {r['geometric_slot']} | {r['upper_material_allocation_mm']:.2f} | {r['unrepresented_reserve_before_retraction_mm']:.2f} | {r['unrepresented_reserve_after_retraction_mm']:.2f} |" for r in rows)
(OUT/'README.md').write_text(f'''# CAM 身体端供线：尚缺的整段余线

**当前状态 BLOCKED：本页完成长度与工序审查，没有完成余线实体和装配验证。**

上部连续检查将身体侧导线保持在既有路线，再让上部前缀逐渐变长。
这能检查局部空间，却没有放置尚未送入的那一段材料。如果身体端插头已经
接好并锁定，则不能直接从这个模型推导实际送料过程。

## 当前上部候选的材料账

| 几何槽位（不是针脚号） | 上部分配 / mm | 暂存 13 mm 时尚未放置的余线 / mm | 退回起点后尚未放置的余线 / mm |
|---|---:|---:|---:|
{table}

这些是现有上部折线长度分配，**不是供应商裁线尺寸**。表格只覆盖这次上部
工序，尚未把更早的颈部穿线、内部松量变化和完整身体尾线统一到材料坐标。
余线是现有材料的暂存需求，不是给最终线束额外增加同样长度。

## 接下来评估的装配顺序

先在机身外完成头部/颈部穿线，身体端插头保持松散；再核对带线的完整头部
总成落位、身体侧理线与插头接入。该顺序还没有验证或应用，暂不新增打印件。

已有身体装配研究只移动承重桥、轴承及对应螺母，并没有把完整带线头部包含
进去，所以不能直接复用它的 PASS。需要重新检查总成成员、全长余线、PH
胶壳暂存位置、下放过程、最后的固定和插接，以及反向拆装。

[计算和来源记录](audit.json) · [已检查的上部路线](../ordered_feed_recovery/index.html)
''')
print('CAM_BODY_SUPPLY_AUDIT PASS; full supply BLOCKED; upper reserve ranges',
      min(r['unrepresented_reserve_before_retraction_mm'] for r in rows),max(r['unrepresented_reserve_after_retraction_mm'] for r in rows))
