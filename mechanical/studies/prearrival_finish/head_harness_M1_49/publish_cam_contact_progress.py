"""Publish bounded neck-feed progress and its explicit remaining conflicts."""
from pathlib import Path
import datetime,hashlib,json,re,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
OUT=REST/'contact_continuous';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
specs=[
 ('contact_vertical','screen_cam_contact_vertical.py','cam_contact_vertical.log','CONTACT_VERTICAL_DONE'),
 ('contact_profile','screen_cam_contact_profile.py','cam_contact_profile.log','CONTACT_PROFILE_DONE'),
 ('contact_radial_orientation','screen_cam_contact_radial_orientation.py','cam_contact_radial_orientation.log','CONTACT_RADIAL_ORIENTATION_DONE'),
 ('contact_collar_follow','screen_cam_contact_collar_follow.py','cam_contact_collar_follow.log','CONTACT_COLLAR_FOLLOW_DONE'),
 ('contact_lower_inward','screen_cam_contact_lower_inward.py','cam_contact_lower_inward.log','CONTACT_LOWER_INWARD_DONE'),
 ('contact_continuous','verify_cam_contact_sweep.py','cam_contact_continuous.log','CONTACT_CONTINUOUS_DONE'),
 ('wire_body_arrival','screen_cam_wire_body_arrival.py','cam_wire_body_arrival.log','WIRE_BODY_ARRIVAL_DONE'),
 ('wire_body_arrival_refined','screen_cam_wire_body_arrival_refined.py','cam_wire_body_arrival_refined.log','WIRE_BODY_ARRIVAL_REFINED_DONE'),
 ('contact_with_upper_wires','verify_cam_contact_upper_wires.py','cam_contact_upper_wires.log','CONTACT_WITH_UPPER_WIRES_DONE')]
commands=[];assets=[]
for directory,script,log,token in specs:
    out=REST/directory;r=read(out/'review.json');s=HERE/script;l=BASE/log
    assert not r['main_changed'] and r['Yaw_Reaction_Link_present']
    assert token in l.read_text() and 'Blender quit' in l.read_text() and 'Traceback' not in l.read_text()
    assert sha(s)==r['script_sha256']
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
    for f,h in r.get('output_geometry',{}).items():assert sha(out/f)==h,f
    if 'state_sha256' in r:assert sha(out/'state.npz')==r['state_sha256']
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),
        result=str((out/'review.json').relative_to(ROOT)),result_sha256=sha(out/'review.json'),check_status=r['status']))
    assets.extend([s,l,*[p for p in out.iterdir() if p.is_file()]])
for result,script,log,token in [(OUT/'plot_review.json','plot_cam_contact_sections.py','cam_contact_sections.log','CAM_CONTACT_SECTIONS_PLOT_DONE'),
    (REST/'contact_with_upper_wires/explicit_witnesses.json','diagnose_cam_contact_neighbors.py','cam_contact_neighbor_witnesses.log','CAM_NEIGHBOR_WITNESSES_DONE')]:
    r=read(result);s=HERE/script;l=BASE/log;assert r['status']=='PASS' and sha(s)==r['script_sha256']
    assert token in l.read_text() and 'Traceback' not in l.read_text()
    for f,h in r['inputs'].items():assert sha(ROOT/f)==h,f
    commands.append(dict(argv=r['actual_command'],cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
        script_sha256=sha(s),result=str(result.relative_to(ROOT)),result_sha256=sha(result),check_status='PASS'))
    assets.extend([s,l,result])

rigid=read(OUT/'review.json');arrival=read(REST/'wire_body_arrival_refined/review.json')
witness=read(REST/'contact_with_upper_wires/explicit_witnesses.json')
assert rigid['status']=='PASS' and rigid['checked_intervals']==1047
assert arrival['status']=='BLOCKED' and witness['arrival_pair_witness']['clearance_status']=='FAIL'
assert {r['wire'] for r in witness['continuous_path_sample_witnesses'] if r['clearance_status']=='FAIL'}=={'P_J18_1','P_J18_2'}
main_delivery=read(HERE.parent/'neck_adoption/delivery.json');protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for file,h in {**main_delivery['files'],**protected}.items():assert sha(ROOT/file)==h,file
exports=read(ROOT/'mechanical/reports/export_manifest.json');animation=read(ROOT/'mechanical/animation/delivery.json')
for row in exports['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
for file,h in animation['files'].items():assert sha(ROOT/'mechanical'/file)==h,file
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,main_changed=False,main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),
    config_sha256=sha(ROOT/'config/geometry.json'),main_files_checked=len(main_delivery['files']),protected_hardware_files_checked=len(protected),
    STL_files_checked=len(exports['parts']),animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))

page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>颈部穿线：结构通路与线束顺序</title><style>
body{margin:0;background:#f4f5f6;color:#18272f;font:17px/1.65 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:32px 24px 70px}
h1{font-size:31px;line-height:1.35}h2{font-size:23px;margin-top:34px}a{color:#146d85}section{background:white;border:1px solid #dbe1e4;border-radius:12px;padding:22px;margin:22px 0}
.status{display:inline-block;padding:4px 13px;background:#fff0d9;color:#794b08;border-radius:20px;font-weight:650}.muted{color:#5e6e77}
table{width:100%;border-collapse:collapse}th,td{padding:13px 10px;border-bottom:1px solid #dbe1e4;text-align:left;vertical-align:top}th{background:#edf1f3}
img{width:100%;height:auto;border:1px solid #dde4e8}code{font-size:13px;overflow-wrap:anywhere}li{margin:8px 0}
@media(max-width:700px){main{padding:20px 12px}section{padding:14px}table{font-size:14px}h1{font-size:25px}}
</style><main>
<a href="../../index.html">← 完整走线工作页</a><h1>颈部通路已找到，线束装入顺序仍未闭合</h1>
<p><span class="status">完整线束 BLOCKED</span></p>
<p>主模型继续使用已确认的 M1.49 C5＋K1。以下是独立的穿线研究，使用尚未采用的 C6／导向／固定候选；本次未更改主模型或打印件。</p>
<section><h2>这轮得到的结果</h2><table><thead><tr><th>检查</th><th>结果</th><th>范围</th></tr></thead><tbody>
<tr><td>名义端子通过结构通道</td><td>PASS</td><td>保留反力连杆，从头内导向位置穿至身体侧。1,048 个位置及之间 1,047 段连续运动通过，净距下界约 0.306 mm。</td></tr>
<tr><td>其余 7 根线已占据候选位置时穿入</td><td>BLOCKED</td><td>CAM 的 +5V 和 GND 候选线会进入端子盒内部，属于明确相交。</td></tr>
<tr><td>第一根 CAM 信号线完整到达身体侧</td><td>BLOCKED</td><td>线长保持、结构净距和本次自接近检查通过；身体侧与 CAM 供电 GND 线相交。</td></tr>
</tbody></table><p class="muted">端子仍是 2.08 × 1.5 × 5.7 mm 名义盒；所选端子的实际压接外形未确认。上述结果不等同于成品线束可安装。</p></section>
<section><h2>端子如何绕过反力连杆</h2><p>端子先在连杆外侧下行，局部向内倾斜，再穿过下方出口。移动轨迹和端子朝向分别处理，没有移动连杆或削薄打印件。</p>
<a href="sections.png"><img src="sections.png" alt="三个高度的实际结构截面，展示名义端子与反力连杆、俯仰支架、固定轴承座的关系"></a>
<p><a href="review.json">连续通路检查</a> · <a href="path.npz">完整端子位置与朝向</a> · <a href="plot_review.json">截面来源</a></p></section>
<section><h2>已确认的相交位置</h2><p>在两个不同的穿入位置，P_J18_1（CAM +5V）和 P_J18_2（CAM GND）的候选线中心分别进入名义端子盒内部。</p>
<p>身体侧完整导线的检查也找到明确交叉：CAM 信号线和供电 GND 的局部中心距约 0.110 mm，而规划外半径之和为 0.9144 mm。加密采样没有消除这个相交。</p>
<p><a href="../contact_with_upper_wires/explicit_witnesses.json">相交坐标与证据</a> · <a href="../contact_with_upper_wires/review.json">连同 7 根候选线的穿入检查</a> · <a href="../wire_body_arrival_refined/review.json">完整导线到达状态</a></p></section>
<section><h2>接下来必须补齐</h2><ol>
<li>安排 CAM 信号线与两根供电线的先后穿入、临时停放和恢复到最终位置的顺序。</li>
<li>检查整根软线在每一步中的过渡形状、线长、弯曲和相互净距，并衔接已有的头内预装步骤。</li>
<li>获得实际端子压接、CAM 供电接口和成品线资料后，替换规划包络复核。</li>
</ol><p>“CAM 信号线先穿、供电线后装”目前只是待检验的顺序方向，尚未作为装配结论。</p></section>
<details><summary>保留的诊断记录</summary><ul>
<li><a href="../contact_vertical/review.json">竖直端子</a></li><li><a href="../contact_profile/review.json">沿路径切向倾斜</a></li>
<li><a href="../contact_radial_orientation/review.json">仅径向倾斜</a></li><li><a href="../contact_collar_follow/review.json">绕过连杆下缘</a></li>
<li><a href="../contact_lower_inward/review.json">下段内移的对照</a></li><li><a href="../wire_body_arrival/review.json">完整导线初次检查</a></li>
</ul><p class="muted">有限路径失败不能证明所有走线方式都不可行。主模型、硬件源文件与已发布动画保持既有版本；没有制造放行。</p><p><a href="main_integrity.json">主模型、硬件及动画保留核验</a></p></details>
</main></html>'''
(OUT/'index.html').write_text(page)
note='''# 颈部端子通路与完整线束：本轮结果

已确认主模型 M1.49 的 C5+K1。本轮只增加独立研究文件，C6、导向件及 CAM 固定候选仍未采用。

1. 调整临时端子轨迹和朝向后，名义 PH 盒从导向位置 Z224 到尾端 Z136.5 的结构通路通过：1,048 个位置、1,047 段连续插值、最小净距下界 0.3056757 mm。反力连杆保留。
2. 加回其余七根上部候选线后，CAM 供电两线 P_J18_1 / P_J18_2 的中心会进入端子盒，明确相交。不能把局部结构通路结论扩展为完整装配通过。
3. 第一根完整 CAM 信号线在身体侧与 P_J18_2 交叉，局部中心距 0.1101197 mm，规划外半径合计 0.9144 mm。加密后仍有相交；无需继续通过加密来追求通过。

下一步应联立 CAM 信号和两根供电线的先后装入、临时停放与最终恢复。先装 CAM 的方向尚未证明可执行，其他五根候选线与未穿 CAM 线仍须保留检查。需要完成整根软线的运动形状和既有下降步骤的衔接，不能只移动裸端子。

PH 的 2.08×1.5×5.7 mm 盒和现有线径均为规划参考，实际成品压接仍 BLOCKED。头部零位、未装件清单及未采用打印件均见各报告。无主模型、硬件或制造状态变更。
'''
(REST/'NECK_CONTACT_PROGRESS.md').write_text(note)
rootpage=BASE/'index.html';content=rootpage.read_text()
content=re.sub(r'<!-- NECK_CONTACT_PROGRESS -->.*?<!-- /NECK_CONTACT_PROGRESS -->','',content,flags=re.S)
section='''<!-- NECK_CONTACT_PROGRESS --><section id="neck-contact-progress"><h2>颈部端子通路找到，完整穿线仍未通过</h2><p>保留反力连杆的名义端子连续通路已通过。加回 CAM 供电两根线后有明确相交；第一根完整信号线的身体侧到达形状也与供电地线交叉，需要继续处理装入顺序和临时停放。</p><p><a href="cam_restraints/contact_continuous/index.html">截面、相交证据与下一步</a> · <a href="cam_restraints/NECK_CONTACT_PROGRESS.md">本轮记录</a></p></section><!-- /NECK_CONTACT_PROGRESS -->'''
assert '</main>' in content;rootpage.write_text(content.replace('</main>',section+'</main>'))
commandfile=BASE/'upper_connection_commands.json';current=read(commandfile)
scriptpaths={r['argv'][-1] for r in commands};current['commands']=[r for r in current['commands'] if r['argv'][-1] not in scriptpaths]+commands
current['utc']=now;write(commandfile,current)
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[])
state['CAM_neck_contact_progress']=dict(status='BLOCKED',structural_rigid_contact='PASS',continuous_intervals=1047,
    gap_lower_bound_mm=rigid['minimum_gap_lower_bound_mm'],with_upper_wires='BLOCKED',conflicting_wires=['P_J18_1','P_J18_2'],
    complete_first_wire_arrival='BLOCKED',arrival_conflicting_wire='P_J18_2',
    evidence='cam_restraints/contact_continuous/index.html',main_applied=False)
state['last_completed_independent_work']='Found a continuous rigid nominal-contact passage with reaction link present; adding seven upper wires exposes definite CAM power-wire intersections. Full first-wire arrival also intersects P_J18_2.'
state['next_work']=[x for x in state['next_work'] if not x.startswith('Restricted final-centreline') and not x.startswith('Do not finalize each CAM return immediately')]
state['next_work'].append('Use the saved contact_continuous path as a conditional structural passage only. Coordinate CAM signal feeding with P_J18_1/2 supply-wire insertion, temporary parking and restoration; prove all stages with full-length wires. Their explicit overlap witnesses rule out clearing the current all-wires-present order by sample refinement alone. The initial descent join is still untested.')
state['review_url']='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT))
write(BASE/'continuation_status.json',state)
assets += [OUT/'index.html',OUT/'main_integrity.json',rootpage,REST/'NECK_CONTACT_PROGRESS.md',commandfile,Path(__file__),HERE/'verify_remaining_publication.py']
pub=read(BASE/'publication.json');pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in assets})
pub.update(utc=now,CAM_neck_contact_progress='Structural passage PASS; upper-wire conflicts BLOCKED',full_harness='BLOCKED',
    contact_progress_publish_command=[sys.executable,*sys.argv],contact_progress_publisher_sha256=sha(Path(__file__)))
write(BASE/'publication.json',pub)
print('CAM_CONTACT_PROGRESS_PUBLISHED',len(commands),'commands',len(set(assets)),'files')
