"""Publish scoped joint-wire progress and newly exposed assembly blockers."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'CAM_H02_joint_lift'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
sources={}


def receive(path,script,helper=None):
    d=read(path)
    assert d['script_sha256']==sha(A8/script),script
    for p in [path,A8/script]:sources[str(p.relative_to(ROOT))]=sha(p)
    if helper:
        assert d['helper_sha256']==sha(A8/helper)
        sources[str((A8/helper).relative_to(ROOT))]=sha(A8/helper)
    for name,h in d.get('source_files',{}).items():
        assert sha(ROOT/name)==h,name
        sources[name]=h
    for name,h in d.get('outputs',{}).items():
        assert sha(path.parent/name)==h,name
        sources[str((path.parent/name).relative_to(ROOT))]=h
    if 'curves_sha256' in d:
        assert sha(path.parent/'curves.npz')==d['curves_sha256']
        sources[str((path.parent/'curves.npz').relative_to(ROOT))]=d['curves_sha256']
    return d


screen=receive(OUT/'screen.json','screen_CAM_H02_lift_copacking.py','screen_CAM_feed_lift_transition.py')
check=receive(OUT/'verification.json','verify_CAM_H02_joint_lift.py')
assert screen['status']==check['status']=='PASS'
assert check['source_screen_sha256']==sha(OUT/'screen.json')
assert check['wire_solids_sha256']==sha(OUT/'wire_solids.json')
sources[str((OUT/'wire_solids.json').relative_to(ROOT))]=sha(OUT/'wire_solids.json')
assert len(check['joint_lift'])==37 and all(r['status']=='PASS' for r in check['joint_lift'])
assert len(check['open_deck_insertion'])==201 and all(r['status']=='PASS' for r in check['open_deck_insertion'])
assert check['head_poses']==130 and not check['head_solid_intersections']
assert sum(r['checked_positions'] for r in check['rigid_stages'])==408
assert all(r['status']=='PASS' for r in check['rigid_stages']+check['static'])
assert len(screen['selected']['cam'])==4 and len(screen['selected']['h02'])==2
assert len(screen['selected']['cam_pairs'])==6
assert len(screen['selected']['route_cam_pairs'])==8
gap=min(r['surface_gap_lower_bound_mm'] for r in screen['selected']['cam_pairs'])
assert gap>=.3
back=receive(ORDER/'CAM_H02_back_transition/screen.json','screen_CAM_H02_back_transition.py','screen_CAM_feed_lift_transition.py')
vertical=receive(ORDER/'CAM_H02_vertical_withdrawal/screen.json','screen_CAM_H02_vertical_withdrawal.py','screen_CAM_H02_back_transition.py')
shell=receive(ORDER/'CAM_H02_shell_first/screen.json','screen_CAM_H02_shell_first.py','screen_CAM_H02_vertical_withdrawal.py')
schedule=receive(ORDER/'CAM_H02_shell_schedule/screen.json','screen_CAM_H02_shell_schedule.py','screen_CAM_H02_shell_first.py')
assert all(d['status']=='BLOCKED' for d in [back,vertical,shell,schedule])
assert len(schedule['candidates'])==6
assert all(r['stages'][0]['failure']['a']=='Plug_rear_J2' for r in schedule['candidates'])
projection=receive(OUT/'projections.json','extract_CAM_H02_review.py')
plot=receive(OUT/'plot.json','plot_CAM_H02_review.py')
assert projection['status']==plot['status']=='PASS'
protected=screen['protected_sources']
for p,h in protected.items():assert sha(ROOT/p)==h,p
assert not screen['main_applied'] and not check['manufacturing_release']
old_len=plot['old_H02_2_length_mm'];new_len=plot['new_H02_2_length_mm']
overlap=projection['rear_J2_witness']['intersection_mm3']
md=f'''# CAM 与 H02 联合走向：局部通过，完整装配仍未完成

## 这次实际解决的部分

此前 CAM 第4根线与 H02 的抬升走向没有配合起来。本次只调整 H02 第二根线的中段，保留两个原接口、针序、端后5mm直段和原弯曲半径。
H02 第一根未改。第二根名义路线 {old_len:.3f} → {new_len:.3f}mm，增加 {new_len-old_len:.3f}mm；这是几何路线长度，不是供应商裁线长度。
模型折线的最高点 {plot['old_H02_2_polyline_peak_z_mm']:.3f} → {plot['new_H02_2_polyline_peak_z_mm']:.3f}mm。不要与旧控制点142.4mm混用。

![H02 新旧走向](H02_comparison.png)

| 检查对象 | 范围 | 结果 |
|---|---|---|
| 4根CAM线＋2根H02线 | 桥上抬0–18mm，每0.5mm，共37个有限位置；14根身体线均保留 | PASS，仅线形与所列障碍物 |
| CAM相互间隙 | 6对导线，端子相互及端子对他线检查 | 最小保守线间隙{gap:.3f}mm |
| 新H02实体 | 当前209件、29个插头分配、其他12根身体线 | PASS |
| 新H02提前装入 | 开敞机身、两端插头与线一起，201个位置 | PASS；早于CAM/H01/H04/桥/上壳 |
| 新H02后续占用 | 408个身体位置、130个头部姿态 | PASS，仅H02对运动零件 |

![同一组导线的三个抬升位置](lift_comparison.png)

上述37个位置不是整套装配通过。该阶段的线束检查没有把“上壳及其插头对托板”的完整刚体路径当作通过条件。
本次补查这项后发现了下文问题。无连续区间证明，无人手/支承验证。

## 还卡在哪里

1. **继续后移桥**：当前圆弯形式在中途出现无解或不足间隙，未形成4根线的完整后移组合。
2. **桥和外壳直接继续竖直抬高**：桥抬至22mm时，外壳与H04第3根的线包络有名义重叠。
3. **把外壳先单独后移**：加入后板插头后，原“外壳倾斜15°、抬高14mm”的保持位置，J2插头包络与Load Frame重叠约{overlap:.5f}mm³。6种提前后移动作也在释放途中未通过这处。

![后板J2与托板的包络重叠](rear_J2_overlap.png)

J2采用厂家胶壳尺寸加保守法向包络，尚不足以断言实物一定相撞。下一步先核对后板连接器拔插/接线的装配时机和准确外形，再连接完整外壳路径；不靠缩小插头或删除托板来消除检查结果。
这些属于可继续做的设计工作，不应全部归为“等实物”。

## 当前范围

- 使用此前尚未采用的Yaw Base/Pitch Yoke/Pitch Cradle研究几何；主模型M1.47和PCB保持。
- H02的201位置检查是单独的早期装配工序，不能代替H01/H04及后板带线拔插工序。
- CAM完整名义线长保留。自由端子的1×1.8×4.1mm仍是明确标注的空间分配，实际压接外形待来源/首件。
- 其他跨关节线、FPC、扎带、人手支承和完整连续装配顺序仍未完成。供应商制作方式已确认；裁线图仍未放行。

[联合检查](verification.json) · [后移诊断](../CAM_H02_back_transition/screen.json) · [竖直诊断](../CAM_H02_vertical_withdrawal/screen.json) · [包含插头的动作诊断](../CAM_H02_shell_schedule/screen.json) · [来源清单](publication.json)。
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM与H02联合走向</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1080px;padding:24px;margin:auto;color:#263e45;background:#f4f7f7}}section{{background:white;padding:22px;margin:20px 0;border-radius:10px}}a{{color:#076c7b}}img{{width:100%;height:auto}}.note{{background:#fff0db}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #dae1e3}}table{{border-collapse:collapse;width:100%}}</style>
<p><a href="../../../../../../../../../supplier_source_update/index.html">← 厂家资料与设计进度</a> · <a href="../feed_pose_packing/index.html">此前独立排布</a></p>
<h1>CAM与H02的抬升走向已配合起来</h1>
<section class="note"><p>37个有限位置的线束检查通过。完整装配仍有外壳、后板插头和后续送线问题，主模型及制造图尚未更新。</p></section>
<section><h2>只调整H02第二根线的中段</h2><p>端口、针序、端后直段和弯曲半径保持；名义路线 {old_len:.3f} → {new_len:.3f}mm，增加 {new_len-old_len:.3f}mm。这不是供应商裁线尺寸。</p><a href="H02_comparison.png"><img src="H02_comparison.png" alt="H02第二根线的旧、新路线，两个端点不动"></a></section>
<section><h2>已经通过的检查</h2><table><tr><th>范围</th><th>结果</th></tr><tr><td>四根CAM与两根H02，桥抬升0–18mm</td><td>37个有限位置；14根身体线均保留</td></tr><tr><td>CAM六对导线</td><td>最小保守间隙{gap:.3f}mm</td></tr><tr><td>H02提前装入</td><td>201个开敞装入位置</td></tr><tr><td>H02对后续运动零件</td><td>408个身体位置及130个头部姿态</td></tr></table><p>这些是分别限定范围的几何结果，不能相加当作完整装配验证。</p><a href="lift_comparison.png"><img src="lift_comparison.png" alt="同一组CAM线在桥抬升0、9、18毫米时的正面和侧面投影"></a></section>
<section class="note"><h2>新增的明确卡点：后板插头随外壳运动</h2><p>补查后板插头与托板的相对运动后，原“15°倾斜、14mm抬高”的位置，J2插头包络与托板有约{overlap:.5f}mm³重叠。提前后移外壳的6种动作仍未通过此处。</p><a href="rear_J2_overlap.png"><img src="rear_J2_overlap.png" alt="后板J2插头包络与Load Frame的局部重叠"></a><p>此胶壳模型含保守包络，不等于实物相撞已经确认。需要核对拔插时机和实际外形。直接继续抬高还会遇到H04线；继续后移桥的弯线动作也尚未完成。</p></section>
<section><h2>后续工作</h2><p>先完成后板接口的装配时机与外壳路径，再连接后续送线动作。H01/H04带线装入、其他跨关节线、FPC、扎带和人手支承仍待完成。</p><p>使用既有未采用的结构候选；主模型M1.47与PCB保持。供应商制作方式已确认，裁线图仍未放行。</p><p><a href="README.md">完整说明</a> · <a href="verification.json">联合检查</a> · <a href="../CAM_H02_shell_schedule/screen.json">插头动作诊断</a> · <a href="publication.json">来源和范围</a></p></section></html>'''
(OUT/'index.html').write_text(html)
report=dict(status='PASS',scope='Publication and source consistency, not complete assembly',
            generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
            source_files=sources,protected_sources=protected,
            joint_wire_finite_lift='PASS',joint_wire_lift_positions=37,body_wires_present=14,
            CAM_pair_gap_lower_bound_mm=gap,H02_open_deck_positions=201,H02_rigid_positions=408,H02_head_poses=130,
            later_bridge_shift='BLOCKED',direct_vertical_continuation='BLOCKED',shell_connector_path='BLOCKED',
            rear_J2_held_pose_overlap_mm3=overlap,continuous_assembly='NOT_TESTED',
            complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False,
            outputs={n:sha(OUT/n) for n in ['README.md','index.html','projections.json','plot.json',
                                          'lift_comparison.png','H02_comparison.png','rear_J2_overlap.png']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
path=A8.parent/'work_status.json';state=read(path)
state['CAM_H02_joint_lift']=dict(publication=str((OUT/'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT/'publication.json'),wire_lift_positions=37,joint_wire_geometry='PASS',
    H02_open_deck_positions=201,H02_head_poses=130,shell_connector_path='BLOCKED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
state['CAM_segmented_body_feed']['joint_lift_followup']=str((OUT/'publication.json').relative_to(A8.parent))
for item in state['remaining']:
    if item['id']=='harness':
        item['latest_joint_lift_evidence']=str((OUT/'index.html').relative_to(A8.parent))
        item['latest_joint_lift_detail']='调整H02第二根线中段后，CAM与H02的37个有限抬升位置通过；H02开敞装入201位置、身体408位置和头部130姿态复核通过。整套装配未通过：后板J2插头包络随外壳移动时与托板重叠，后移桥/继续竖直抬升及后续线束工序仍待完成。'
        item['latest_segmented_feed_detail']='历史两处独立排布通过；其中CAM4/H02的抬升问题已在后续联合研究中取得37位置通过，见latest_joint_lift_evidence。完整装配和裁线图仍BLOCKED。'
state['updated_utc']=report['generated_utc']
path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('CAM_H02_JOINT_REVIEW_PUBLISHED wire lift PASS37; full assembly BLOCKED')
