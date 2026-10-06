"""Publish bounded keeper access and the remaining reaction-link dependency."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'inner_head_sequence_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat();assets=[];commands=[]
specs=[
 ('keeper_after_head','screen_keeper_after_head_preassembly.py','keeper_after_head.log','KEEPER_AFTER_HEAD_DONE','review.json'),
 ('keeper_after_head_long_leg','screen_keeper_after_head_long_leg.py','keeper_after_head_long_leg.log','KEEPER_LONG_LEG_DONE','review.json'),
 ('keeper_alternating_yaw','verify_keeper_alternating_yaw_access.py','keeper_alternating_yaw.log','KEEPER_ALTERNATING_DONE','review.json'),
 ('inner_head_lowering','check_inner_head_lowering_order.py','inner_head_lowering.log','INNER_HEAD_LOWERING_DONE','review.json'),
 ('reaction_link_order','check_reaction_link_order.py','reaction_link_order.log','REACTION_LINK_ORDER_DONE','review.json'),
 ('reaction_short_tool','screen_reaction_retainer_short_tool.py','reaction_short_tool.log','REACTION_SHORT_TOOL_DONE','review.json'),
 ('reaction_short_tool_exit','check_reaction_short_tool_exit.py','reaction_short_tool_exit.log','REACTION_SHORT_TOOL_EXIT_DONE','review.json'),
 ('inner_head_sequence_review','render_inner_head_keeper_order.py','inner_head_keeper_render.log','INNER_HEAD_KEEPER_RENDER_DONE','render_review.json'),
 ('inner_head_sequence_review','plot_reaction_link_order.py','reaction_link_plot.log','REACTION_LINK_PLOT_DONE','plot_review.json')]
for directory,script,log,token,resultname in specs:
    folder=REST/directory;s=HERE/script;l=BASE/log;result=folder/resultname;r=read(result)
    assert sha(s)==r['script_sha256'],script
    assert token in l.read_text() and 'Traceback' not in l.read_text(),log
    python='actual_command' in r
    if not python:assert 'Blender quit' in l.read_text() and not r['main_changed'] and r['Yaw_Reaction_Link_present']
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
    for image in r.get('images',[]):assert sha(folder/image['file'])==image['sha256']
    for key,name in [('tool_geometry_sha256','tools.npz'),('sections_sha256','sections.json'),('image_sha256','reaction_order.png')]:
        if key in r:assert sha(folder/name)==r[key],name
    argv=r['actual_command'] if python else ['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))]
    commands.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),result=str(result.relative_to(ROOT)),result_sha256=sha(result),check_status=r['status']))
    assets.extend([s,l,*[p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]])
keeper=read(REST/'keeper_alternating_yaw/review.json');lower=read(REST/'inner_head_lowering/review.json')
link=read(REST/'reaction_link_order/review.json');exitcheck=read(REST/'reaction_short_tool_exit/review.json')
assert keeper['status']=='PASS'
assert [r['status'] for r in lower['rows']]==['BLOCKED','PASS']
assert exitcheck['clear_routes']==0 and exitcheck['route_count']==138
main_delivery=read(HERE.parent/'neck_adoption/delivery.json')
protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for f,h in {**main_delivery['files'],**protected}.items():assert sha(ROOT/f)==h,f
exports=read(ROOT/'mechanical/reports/export_manifest.json');animation=read(ROOT/'mechanical/animation/delivery.json')
for row in exports['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
for f,h in animation['files'].items():assert sha(ROOT/'mechanical'/f)==h,f
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,main_changed=False,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),config_sha256=sha(ROOT/'config/geometry.json'),
    main_files_checked=len(main_delivery['files']),protected_hardware_files_checked=len(protected),
    STL_files_checked=len(exports['parts']),animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>头部子装配与压板工具路径</title><style>
body{margin:0;background:#f4f6f7;color:#1d3038;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:30px 24px 65px}
h1{font-size:30px;line-height:1.4}h2{font-size:23px}section{background:white;border:1px solid #d6dfe3;border-radius:12px;padding:22px;margin:22px 0}
a{color:#116d85}img{width:100%;height:auto}.status{background:#fff0d9;color:#80510b;padding:5px 13px;border-radius:18px;font-weight:650}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0}figcaption{padding:10px 0;font-size:15px}.muted{color:#596d78}
table{border-collapse:collapse;width:100%;font-size:15px}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #dce3e7;padding:12px}th{background:#eef3f5}li{margin:9px 0}
@media(max-width:700px){main{padding:18px 12px}section{padding:15px}.pair{grid-template-columns:1fr}h1{font-size:25px}}
</style><main><a href="../../index.html">← 走线工作页</a><h1>压板工具路径已通过，整套装配仍待闭合</h1>
<p><span class="status">完整带线装配 BLOCKED</span></p>
<p>已批准的 K1 孔位与孔壁修正继续保留在主模型 M1.49。本轮补查安装顺序，没有改动主模型、STL、硬件或动画。</p>
<section><h2>压板的两枚螺钉可以分开操作</h2>
<p>头壳、屏幕和相机支架暂不安装。内侧头架分别转到 +60° 与 −60°，用长边朝下的工具逐枚操作，工具取出后再转头。</p>
<div class="pair"><figure><a href="left_keeper.png"><img src="left_keeper.png" alt="内侧头架在正60度偏航时，从上方操作左侧压板螺钉"></a><figcaption>左侧螺钉：偏航 +60°。蓝色为工具包络，黄色为压板。</figcaption></figure>
<figure><a href="right_keeper.png"><img src="right_keeper.png" alt="内侧头架在负60度偏航时，从上方操作右侧压板螺钉"></a><figcaption>右侧螺钉：偏航 −60°。头壳与光学组件最后安装。</figcaption></figure></div>
<p>两次操作均检查了 150 mm 直线伸入／退出、完整一圈转动和实际螺钉的连续装入扫掠；避开了这两个姿态下的 11 条候选导线。工具按 <a href="https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated">Wera 950 PKLS 05022041001</a> 的 2 mm 内六角、100／5.5 mm 边长建立保守包络。</p>
<p class="muted">图片使用独立 C6、导向和绑带座候选，尚未应用到主模型；省略导线显示以说明工具位置。导线目前仍是规划路径。实际球头啮合、拧紧扭矩、两次操作间的完整带线运动没有通过此检查。</p>
<p><a href="../keeper_alternating_yaw/review.json">逐步检查与明确缺件清单</a> · <a href="render_review.json">渲染来源</a></p></section>
<section><h2>反力连杆仍限制头部落座与锁紧</h2>
<a href="reaction_order.png"><img src="reaction_order.png" alt="反力连杆预装时被头部支架孔挡住，随头部安装后直柄工具受上壳阻挡的实际剖面"></a>
<table><thead><tr><th>装配方向</th><th>结果</th><th>范围</th></tr></thead><tbody>
<tr><td>先固定连杆，再竖直放入内侧头架</td><td>BLOCKED</td><td>−60° 到 +60°、每 10° 一组均在落座路径中相交。零偏航时，抬高 24 mm 的相交体积约 411 mm³；不是首个接触点的微小数值造成的误判。</td></tr>
<tr><td>连杆随内侧头架一起落座</td><td>刚体采样 PASS；锁紧未闭合</td><td>0～90 mm 的 181 个竖直位置通过。连杆横向固定螺钉要随后安装；直柄工具受扬声器和上壳阻挡。</td></tr>
<tr><td>改用短柄工具，从未封闭的下部退出</td><td>局部姿态有空间，所测退出路径 BLOCKED</td><td>20／25／30 mm 短边存在局部可放置姿态；23 个姿态、共 138 条简单退让路径均受阻。其他带转动的路径及实际工具选型仍未验证。</td></tr>
<tr><td>先留上壳抬起，之后再落下</td><td>所测路径 BLOCKED</td><td>内侧头架已就位时，上壳原有 15°／14 mm 倾斜抬升路径在 −60°、0°、+60° 三个头部位置均碰到支架。</td></tr>
</tbody></table>
<p>因此还不能把这套顺序交给装配执行，也没有据此增加开孔。SCS0009 原配舵盘及传动锁紧叠层仍待厂家资料，连杆附近的安装判断也须随真实接口复核。</p>
<p><a href="../inner_head_lowering/review.json">头部落座清单</a> · <a href="../reaction_link_order/review.json">实际相交与直柄工具检查</a> · <a href="../reaction_short_tool/review.json">短柄局部筛查</a> · <a href="../reaction_short_tool_exit/review.json">138 条退出路径</a></p></section>
<section><h2>本轮解决的范围</h2><p>压板螺钉可以按两个偏航位置分别操作，这一局部工具路径已闭合。完整线束装入、连杆固定、线长保持及最终接头仍未闭合；不能把各处单独的 PASS 合并成“整机已能装配”。</p>
<p><a href="../power_sequence_review/index.html">上一轮：供电插头与承重桥锁紧依赖</a> · <a href="main_integrity.json">主模型、硬件、STL 和动画保留核验</a></p></section>
<details><summary>检查边界与修正记录</summary><ul>
<li>早期长边工具筛查要求同一偏航角能操作左右两枚螺钉，结果为 BLOCKED。本轮改为逐枚操作，保留早期报告，未覆盖其证据。</li>
<li>连续工具检查曾因凸包零面积三角形产生无效法向而中止；失败记录保留。修正仅影响检验算法，不改变零件实体。</li>
<li>螺钉扫掠按保存网格的实际头／杆边界分拆，并验证包络包含全部原始实体；避免把宽螺钉头的微小切片扩展到整根细杆产生假碰撞。旧结果保留在 history_screw_split。</li>
<li>更严格的本轮诊断还记录了候选承重桥与名义反力连杆螺母约 0.00847 mm³ 的相交，原因未定。没有以此修改孔位或豁免配合，待实际紧固件与传动接口一起复核。</li>
<li>C6、导向和固定座均是未批准的独立候选；力学、材料与实物装配仍为 NOT_TESTED。</li>
</ul><p><a href="../keeper_after_head/review.json">短边压板工具初筛</a> · <a href="../keeper_after_head_long_leg/review.json">长边单姿态初筛</a> · <a href="plot_review.json">剖面图片来源</a></p></details>
</main></html>'''
(OUT/'index.html').write_text(page)
note='''# 内侧头架与压板工具操作

主模型 M1.49 C5+K1 保持；无结构或硬件修改。完整线束 BLOCKED。

1. 头壳和光学组件后装，左右压板螺钉分别在 yaw+60/-60 操作。150mm 连续工具入/退出、360deg 分段带误差界扫掠、实际螺钉连续装入通过；保留两姿态的11条最终规划曲线。真实工具啮合、拧紧扭矩和完整带线过渡未验证。
2. 反力连杆预装时，13个偏航角的竖直支架落座路径均被夹口挡住。零偏航抬升24mm相交约411mm3，不能忽略首接触小体积后宣称通过。
3. 连杆随内侧头架落座，181个刚体位置通过；后续反力横栓的直柄工具受上壳/扬声器阻挡。短柄工具有23个局部可放置姿态，但138条简单平移退出路径都失败，完整操作仍未闭合。没有证明其他带转动路径不可能。
4. 抬上壳给工具让位也不能直接沿用旧动作：已有内侧头架的三个偏航角均在所测上壳抬升动作中相交。

独立 C6/v4/v3 候选未批准，真实SCS0009舵盘/锁紧叠层未定，不以这些规划几何放行采购或制造。后续须联合解决供电与信号穿线顺序、反力连接锁紧及全线长度；避免重新展开已经失败的同一路径。
'''
(REST/'INNER_HEAD_SEQUENCE_PROGRESS.md').write_text(note)
rootpage=BASE/'index.html';content=rootpage.read_text()
content=re.sub(r'<!-- INNER_HEAD_SEQUENCE_PROGRESS -->.*?<!-- /INNER_HEAD_SEQUENCE_PROGRESS -->','',content,flags=re.S)
block='''<!-- INNER_HEAD_SEQUENCE_PROGRESS --><section id="inner-head-sequence-progress"><h2>最新：压板工具路径已通过，反力连接仍待解决</h2><p>头壳和光学组件后装，左右压板螺钉在 +60°／−60° 分别操作，连续工具伸入、转动和退出检查通过。反力连杆预装会挡住头架落座，随头架落座又存在后续锁紧工具入口问题；完整线束与装配仍未通过。</p><p><a href="cam_restraints/inner_head_sequence_review/index.html">操作图、实际剖面与完整限制</a> · <a href="cam_restraints/INNER_HEAD_SEQUENCE_PROGRESS.md">记录</a></p></section><!-- /INNER_HEAD_SEQUENCE_PROGRESS -->'''
assert '</main>' in content;rootpage.write_text(content.replace('</main>',block+'</main>'))
commandfile=BASE/'upper_connection_commands.json';c=read(commandfile);paths={r['argv'][-1] for r in commands}
c['commands']=[r for r in c['commands'] if r['argv'][-1] not in paths]+commands;c['utc']=now;write(commandfile,c)
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[])
state['inner_head_sequence']=dict(status='BLOCKED',keeper_sequential_tool_access='PASS',keeper_yaw_deg=[60,-60],
    preinstalled_reaction_link_vertical_path='BLOCKED',link_with_head_rigid_samples=181,link_with_head_rigid_path='PASS',
    reaction_straight_tool='BLOCKED',nominal_short_tool_local_poses=23,nominal_short_tool_exit_routes=138,nominal_short_tool_exit='BLOCKED',
    evidence='cam_restraints/inner_head_sequence_review/index.html',main_applied=False)
state['last_completed_independent_work']='Sequential keeper tool entry/rotation/screw sweeps passed with inner head before optics; reaction-link preinstallation blocks the throat, while installing it with the head leaves a tool-access dependency. Nominal short tools have local poses but 138 simple exits fail.'
state['next_work']=list(dict.fromkeys(state['next_work']))
state['next_work'].append('Keep the proven keeper operations at opposite yaw angles, with shells/optics absent. Resolve reaction-link locking jointly with inner-head placement and body wiring: preinstalled collar blocks all13 tested vertical yaw paths; link-with-head passes181 rigid samples but straight tool is blocked and138 simple short-tool exits failed. These finite failures do not prove all manipulation impossible. Do not redesign the throat/retainer or add shell holes without a concrete reviewed option; actual SCS0009 horn and locking stack remain a separate dependency.')
state['review_url']='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT));write(BASE/'continuation_status.json',state)
assets += [OUT/'index.html',OUT/'main_integrity.json',REST/'INNER_HEAD_SEQUENCE_PROGRESS.md',rootpage,commandfile,BASE/'execution_failures.json',Path(__file__),HERE/'verify_remaining_publication.py']
pub=read(BASE/'publication.json');pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in set(assets)})
pub.update(utc=now,inner_head_sequence='Keeper tool operations PASS; reaction-link installation and full wiring BLOCKED',
    inner_head_sequence_publish_command=[sys.executable,*sys.argv],inner_head_sequence_publisher_sha256=sha(Path(__file__)),full_harness='BLOCKED')
write(BASE/'publication.json',pub)
print('INNER_HEAD_SEQUENCE_PUBLISHED',len(commands),'commands',len(set(assets)),'files')
