"""Publish the bounded continuous-CAM milestone without promoting C6 or full harness."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes';F=OUT/'cam_side_fans';JOIN=F/'c6_join';VIEW=JOIN/'review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
reports=[F/'fan_screen.json',JOIN/'join_review.json',VIEW/'review.json'];fr,jr,vr=[read(p) for p in reports]
for r in [fr,jr,vr]:
    assert r['status']=='PASS' and not r['main_changed']
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert not jr['approved'] and not vr['C6_approved'] and not jr['C6_main_applied']
inventory_file=OUT/'cam_restraints/site_inventory.json';inventory=read(inventory_file);assert inventory['status']=='PASS' and inventory['attachment_design']=='NOT_TESTED'
for f,h in {**inventory['sources'],**inventory['inputs']}.items():assert sha(ROOT/f)==h,f
reports.append(inventory_file)
pub=read(OUT/'publication.json');assert sha(ROOT/'mechanical/mori_v1_2.blend')==pub['source_blend_sha256'] and not pub['C6_approved']
assets=[];pictures='';labels={'continuous_CAM_head.png':'头部连续连接，机械零位','continuous_CAM_body.png':'身体到颈部的连续路径，外壳隐藏','continuous_CAM_motion.png':'偏航60°、俯仰25°的组合姿态'}
for row in vr['images']:
    p=VIEW/row['file'];assert sha(p)==row['sha256'];assets.append(p)
    pictures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="{labels[row["file"]]}" style="width:100%"><figcaption>{labels[row["file"]]}。有色线为四根CAM规划路径；金色线为其他五条下部规划路径，灰线为两条扬声器颈部预留。浅棕色固定座使用未批准的C6候选。</figcaption></figure>'
blend=VIEW/'MORI_M1_49_continuous_CAM_C6_candidate.blend';assert sha(blend)==vr['blend_sha256'];assets.append(blend)
table=''.join(f'<tr><td>{html.escape(r["endpoint"])}</td><td>{r["max_mm"]:.1f}</td><td>&lt;0.01</td></tr>' for r in sorted(jr['lengths'],key=lambda v:v['endpoint']) if r['endpoint'].startswith('CAM_'))
links=''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{html.escape(p.parent.name+"/"+p.name)}：PASS</a></li>' for p in reports)
section=f'''<!-- CONTINUOUS_CAM_PROGRESS --><section id="continuous-cam"><h2>最新：CAM四线连续路径（C6条件候选）</h2>
<p>已接通四段头部固定连接，并接到身体内原有路线。四根CAM参考路径现在从基板J5延伸至CAM板的估算端口。机械零位和偏航±60°、俯仰−20°至25°共130个组合姿态均已检查；没有移动板卡或舵机。</p>
<p>头部连接新增520次导线自身回绕检查、780组完整四线间距检查；身体接续新增5850组交叉检查与585次整条路径回绕检查，均通过。未变化部分以文件哈希核对后复用原检查。采用0.3mm规划净距，CAM新增圆弧半径至少7mm。</p>
<p><strong>主模型仍为已采用C5＋K1的M1.49。</strong>这一连续候选需要C6局部开口，C6仍待你确认；主模型、STL和装配视频没有采用它或本候选线束。完整线束状态仍为BLOCKED。</p>
<table><thead><tr><th>参考路径</th><th>名义中心线长度 / mm</th><th>姿态间长度变化 / mm</th></tr></thead><tbody>{table}</tbody></table>
<p>表内是含弯曲余量的几何中心线路径，端口仍有估算，不是可下单的裁线长度。端子内长度、加工公差与固定位置尚未冻结。</p>
{pictures}<p><a href="{blend.relative_to(OUT).as_posix()}">可编辑连续路径候选</a> · <a href="c6_left_slot_entry/index.html">C6开口对比与待确认范围</a> · <a href="CONTINUOUS_CAM_PROGRESS.md">状态与剩余项</a> · <a href="upper_connection_commands.json">实际执行记录</a></p>
<p>夹持位置复核：偏航端规划夹持点中心距现有偏航托架最近约6.8mm，CAM端距头托最近约5.7mm，均未形成实际夹持结构。这个距离检查不能当作固定验证。</p>
<p>仍需完成：其他上端连接、固定与防拉扯、FFC/FPC以及完整带线装配。厂家端头资料和实物弯折寿命的待验证项继续保留。</p><ul>{links}</ul></section><!-- /CONTINUOUS_CAM_PROGRESS -->'''
page=OUT/'index.html';s=page.read_text();s=re.sub(r'<!-- CONTINUOUS_CAM_PROGRESS -->.*?<!-- /CONTINUOUS_CAM_PROGRESS -->','',s,flags=re.S)
s=s.replace('<h2>最新：CAM侧向引线与颈部联合通过</h2>','<h2>此前：CAM侧向引线与颈部联合通过</h2>');s=s.replace('</main>',section+'</main>');page.write_text(s)
note=OUT/'CONTINUOUS_CAM_PROGRESS.md';note.write_text('# CAM四线连续路径\n\n已通过四条头部连接及C6条件下的身体接续，130个头部姿态。主模型M1.49保持C5＋K1，C6未批准且未应用，完整线束仍BLOCKED。\n\n数据：cam_side_fans/fan_screen.json、cam_side_fans/c6_join/join_review.json。可编辑文件及三个视图位于cam_side_fans/c6_join/review/。\n\n头部新连接的直线起步长度分别为0.5、0、1、0mm；所有新增圆弧半径7mm。通过的上端余量圈补偿偏航导致的颈部名义长度变化。完整CAM路径的姿态间数值长度差小于0.01mm，不构成加工公差或实物可变形路径保证。\n\n身体下部候选原9条保留；当前颈部11条包含2条扬声器预留。固定／应力释放、其余上端点、FFC/FPC和带线装配尚未完成。SCS/USB及端子选型资料待正式交接；不发布供应商裁线图。\n')
readme=OUT/'README.md';readme.write_text('# M1.49 线束候选\n\n主模型C5＋K1已应用。C6开口尚待确认。\n\nCAM四线已形成连续条件候选并通过130姿态的分段、交叉及整条回绕复核。见 index.html#continuous-cam。\n\n完整线束仍BLOCKED：其余上端连接、固定防拉扯、FFC/FPC和带线装配未关闭；模型、STL、装配视频未采用此候选。几何路线不代表线束加工放行。\n')
state=read(OUT/'continuation_status.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat();state['utc']=now;state['active_processes']=[]
state.setdefault('historical_local',state['latest_local']);state['latest_local']=dict(file='neck_side_tail_gentle/join_screen.json',status='PASS',source='11 local neck curves;3upper offsets changed',not_a_main_model_adoption=True)
state['upper_current'].update(upper_fan_connections='PASS',fixed_fans='PASS',fixed_fan_report='cam_side_fans/fan_screen.json',continuous_CAM='PASS',
    continuous_CAM_report='cam_side_fans/c6_join/join_review.json',continuous_curves='cam_side_fans/c6_join/candidate_curves.npz',full_harness='BLOCKED',main_changed=False)
state['upper_current'].update(restraint_site_inventory='cam_restraints/site_inventory.json',restraint_design='NOT_TESTED')
state['C6']['upper']='PASS for four continuous CAM routes only; other upper endpoints and restraint remain open'
state['next_work']=['C6 approval remains PENDING; do not treat K1 approval as C6 approval or apply candidate solids to main.',
    'Use continuous candidate cam_side_fans/c6_join/candidate_curves.npz and its hash-verified report. Four CAM routes pass;5 other body-to-neck routes and2speaker neck reservations remain partial.',
    'Complete fixed/pitch anchor and strain-relief candidates. Read cam_restraints/site_inventory.json: current yaw-side guide centre is6.805mm from Pitch_Yoke; CAM lead centre is5.696mm from Pitch_Cradle. Do not confuse free motion curves with secured cable shape or fatigue qualification. Structural changes require a concrete reviewed candidate.',
    'Resolve other upper endpoints, FFC/FPC and wired assembly. Preserve native hardware and source uncertainty; supplier cut lengths remain unreleased.']
write(OUT/'continuation_status.json',state)
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in reports+assets+[page,note,readme,OUT/'upper_connection_commands.json',OUT/'execution_failures.json']})
pub.update(utc=now,CAM_fixed_fans='PASS',conditional_C6_continuous_CAM='PASS',full_harness='BLOCKED',C6_main_applied=False,
    continuous_publisher_sha256=sha(Path(__file__)),continuous_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub);print('CONTINUOUS_CAM_PUBLISHED',flush=True)
