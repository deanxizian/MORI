"""Record two rejected temporary parking families without adopting structures."""
from pathlib import Path
import json,hashlib,datetime,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat();assets=[];commands=[]
for name,script,log,token in [('temporary_parking','screen_cam_temporary_parking.py','cam_temporary_parking.log','TEMP_PARK_DONE'),
                              ('temporary_parking_fan','screen_cam_temporary_parking_fan.py','cam_temporary_parking_fan.log','TEMP_FAN_DONE')]:
    out=REST/name;r=read(out/'review.json');s=HERE/script;l=BASE/log
    assert r['status']=='BLOCKED' and not r['main_changed'] and r['Yaw_Reaction_Link_present']
    assert token in l.read_text() and 'Blender quit' in l.read_text() and 'Traceback' not in l.read_text()
    assert sha(s)==r['script_sha256'] and sha(out/'states.npz')==r['states_sha256']
    for file,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/file)==h,file
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),
        result=str((out/'review.json').relative_to(ROOT)),result_sha256=sha(out/'review.json'),check_status=r['status']))
    assets.extend([s,l,*[p for p in out.iterdir() if p.is_file()]])
commandfile=BASE/'upper_connection_commands.json';current=read(commandfile)
scripts={r['argv'][-1] for r in commands};current['commands']=[r for r in current['commands'] if r['argv'][-1] not in scripts]+commands
current['utc']=now;write(commandfile,current)
witness=read(REST/'temporary_parking/contact_overlap_witness.json');assert sha(ROOT/witness['source'])==witness['source_sha256']
assert witness['strictly_inside_sample_count']>0 and witness['minimum_inset_mm']>.025
note='''# 临时停放顺序检查：两种局部布局均不采用

主模型 C5＋K1、打印文件、动画和硬件源文件保持。以下仅是未采用的 C6／导向结构候选中的穿线研究；没有新增开孔或削薄支架。

**靠边分层停放：** 第一根的完整临时形状通过了本次局部静态检查，但第 2、3 根未通过。第 3 根的一段中心线位于第 1 根的名义 PH 端子盒内部，已有明确交叉点；不能靠放宽数值采样误差来消除。仅在导向孔平面把导线排成两排并不足以证明整根线能停放。

**反序并在孔下散开：** 比较 4→3→2→1 顺序，把三个裸端子向外分散。三个静态中间状态均未通过，其中第 3、2 根的端子与现有 Pitch_Yoke 模型的相交体积分别约 17.784 和 9.854 mm³。这个摆法同样不能采用。

因为中间状态已经不成立，没有继续跑它们的连接运动，也没有把相同失败改名为装配通过。反力连杆保留在障碍物中；前壳、屏幕和舵盘等未装零件的清单在报告内。实际成品压接外形和触点选型仍未确认，PH 通用外形与现有 0.6604 mm 线材样本不能视为已采购组合。

下一步需要把端子通过颈部直至身体侧的临时路径与停放连在一起处理，避免在导向孔正下方堆放端子；还需结合反力连接的预装顺序。已有直线工具与连杆抬升失败、SCS0009 配套舵盘/短轴资料缺口仍保持。不能据本次有限布局失败宣称所有走线方案都不可能。
'''
(REST/'TEMPORARY_PARKING_REVIEW.md').write_text(note)
page=BASE/'index.html';text=page.read_text();text=re.sub(r'<!-- CAM_TEMP_PARKING -->.*?<!-- /CAM_TEMP_PARKING -->','',text,flags=re.S)
section='''<!-- CAM_TEMP_PARKING --><section id="temporary-parking"><h2>临时停放：两种局部摆法未通过</h2><p>靠边分层会让后续导线穿入先前的裸端子空间；改为反序并在孔下散开，又与俯仰支架相交。两种摆法均未采用，完整穿线仍待解决。</p><p><a href="cam_restraints/TEMPORARY_PARKING_REVIEW.md">具体范围与下一步</a> · <a href="cam_restraints/temporary_parking/review.json">靠边分层记录</a> · <a href="cam_restraints/temporary_parking/contact_overlap_witness.json">中心线穿入端子的明确交叉点</a> · <a href="cam_restraints/temporary_parking_fan/review.json">孔下散开记录</a></p></section><!-- /CAM_TEMP_PARKING -->'''
assert '</main>' in text;page.write_text(text.replace('</main>',section+'</main>'))
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[])
state['CAM_temporary_parking']=dict(status='BLOCKED',family_count=2,conditional_static_states_checked=6,accepted_complete_layouts=0,
    evidence='cam_restraints/TEMPORARY_PARKING_REVIEW.md',main_applied=False,connecting_motions='NOT_TESTED')
state['last_completed_independent_work']='CAM entry direction correction prepared and reviewed. Two temporary parking layouts screened: stacked contacts interfere with later wire; outward lower fan intersects Pitch_Yoke. Neither is adopted.'
state['next_work']=[x for x in state['next_work'] if not x.startswith('Do not finalize each CAM return immediately')]
state['next_work'] += ['Do not finalize each CAM return immediately after feeding: it obstructs the next contact. Two guide-local parking families now also fail. Integrate a complete neck-to-body contact feed and remote parking with reaction-link preassembly instead of treating a two-row guide cross-section as a full sequence.']
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json')
assets += [commandfile,page,REST/'TEMPORARY_PARKING_REVIEW.md',HERE/'cam_temporary_staging_geometry.py',HERE/'cam_temporary_fan_geometry.py',Path(__file__)]
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in assets});pub.update(utc=now,CAM_temporary_parking='BLOCKED; two rejected families retained',
    temporary_parking_publish_command=[sys.executable,*sys.argv],temporary_parking_publisher_sha256=sha(Path(__file__)),full_harness='BLOCKED')
write(BASE/'publication.json',pub)
print('CAM_PARKING_REVIEW_PUBLISHED',len(commands),'commands',len(assets),'files')
