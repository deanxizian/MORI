"""Publish the bounded body-plug/head assembly findings without adoption."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'power_sequence_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
specs=[
 ('power_late_access','check_cam_power_late_access.py','cam_power_late_access.log','CAM_POWER_LATE_ACCESS_DONE'),
 ('power_side_access','check_cam_power_side_access.py','cam_power_side_access.log','CAM_POWER_SIDE_ACCESS_DONE'),
 ('power_plug_search','plan_cam_power_plug_access.py','cam_power_plug_search.log','POWER_PLUG_SEARCH_DONE'),
 ('power_plug_simple','simplify_cam_power_plug_access.py','cam_power_plug_simple.log','POWER_PLUG_SIMPLE_DONE'),
 ('power_cover_dependency','check_cam_power_cover_dependency.py','cam_power_cover_dependency.log','POWER_COVER_DEPENDENCY_DONE'),
 ('power_staging','screen_cam_power_staging.py','cam_power_staging.log','CAM_POWER_STAGING_DONE'),
 ('power_staging_contour','screen_cam_power_staging_contour.py','cam_power_staging_contour.log','POWER_STAGING_CONTOUR_DONE'),
 ('head_module_sequence','check_prewired_head_module_sequence.py','prewired_head_module_sequence.log','PREWIRED_HEAD_MODULE_DONE'),
 ('head_module_sequence_v2','check_prewired_head_module_sequence_v2.py','prewired_head_module_sequence_v2.log','PREWIRED_HEAD_MODULE_DONE'),
 ('head_module_tools','screen_head_module_closed_shell_tools.py','head_module_closed_shell_tools.log','HEAD_MODULE_TOOLS_DONE')]
commands=[];assets=[]
def append_record(directory,script,log,token,result_name='review.json',python=False):
    out=REST/directory;s=HERE/script;l=BASE/log;result=out/result_name;r=read(result)
    assert sha(s)==r['script_sha256'],script
    assert token in l.read_text() and 'Traceback' not in l.read_text(),log
    if not python:
        assert 'Blender quit' in l.read_text() and not r['main_changed']
        assert r['Yaw_Reaction_Link_present']
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
    for f,h in r.get('output_geometry',{}).items():assert sha(out/f)==h,f
    for key,file in [('path_sha256','path.npz'),('curve_sha256','curves.npz'),('section_sha256','sections.json'),('image_sha256','assembly_access.png')]:
        if key in r:assert sha(out/file)==r[key],file
    argv=r['actual_command'] if python else ['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))]
    commands.append(dict(argv=argv,cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
                         script_sha256=sha(s),result=str(result.relative_to(ROOT)),result_sha256=sha(result),check_status=r['status']))
    assets.extend([s,l,*[p for p in out.iterdir() if p.is_file()]])
for args in specs:append_record(*args)
append_record('power_sequence_review','export_head_module_access_sections.py','head_module_access_sections.log','HEAD_MODULE_ACCESS_SECTIONS_DONE','geometry_review.json')
append_record('power_sequence_review','plot_head_module_access.py','head_module_access_plot.log','HEAD_MODULE_ACCESS_PLOT_DONE','plot_review.json',True)
stage=read(REST/'head_module_sequence_v2/review.json');tools=read(REST/'head_module_tools/review.json')
witness=read(OUT/'geometry_review.json')
assert stage['status']=='PASS' and sum(x['checked_samples'] for x in stage['rows'])==383
assert tools['status']=='BLOCKED'
assert all(x['status']=='FAIL' for x in witness['screw_witnesses'] if x['withdrawal_mm']==2)
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
<title>CAM供电线与头身装配顺序复核</title><style>
body{margin:0;background:#f4f6f7;color:#1d3038;font:17px/1.65 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:30px 24px 65px}
h1{font-size:30px;line-height:1.4}h2{font-size:23px}section{background:white;border:1px solid #d6dfe3;border-radius:12px;padding:22px;margin:22px 0}
a{color:#116d85}img{width:100%;height:auto}.status{background:#fff0d9;color:#80510b;padding:5px 13px;border-radius:18px;font-weight:650}
table{border-collapse:collapse;width:100%;font-size:15px}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #dce3e7;padding:12px}th{background:#eef3f5}
.muted{color:#596d78}li{margin:9px 0}code{font-size:13px;overflow-wrap:anywhere}@media(max-width:700px){main{padding:18px 12px}section{padding:15px}h1{font-size:25px}}
</style><main><a href="../../index.html">← 走线工作页</a><h1>供电线与头身装配顺序仍有冲突</h1>
<p><span class="status">完整带线装配 BLOCKED</span></p>
<p>主模型继续使用已批准的 M1.49 C5＋K1，压板嵌件名义侧壁为 1.675 mm。这轮只检查线束装入和工具路径，没有修改主模型、打印件或硬件。</p>
<section><h2>查明了哪些限制</h2><table><thead><tr><th>方向</th><th>结果</th><th>证据范围</th></tr></thead><tbody>
<tr><td>先穿 CAM 信号线，再插身体侧供电插头</td><td>BLOCKED</td><td>上、下壳均未安装时，找到裸胶壳五段连续路径；加入上壳后路径穿壳。附带两根供电线的完整动作未验证。</td></tr>
<tr><td>供电插头先接好，临时移开两根线</td><td>BLOCKED</td><td>7 组临时静态排布均未通过；单纯转动避开下段后，又受头部支架上方实体限制。未采用这些线形。</td></tr>
<tr><td>预穿线的头部与承重桥整体放入</td><td>刚体路径 PASS；锁紧 BLOCKED</td><td>桥与头部抬高 19 mm，上壳独立倾斜 15°并抬高 14 mm，383 个刚体位置未检出相交。但上壳合拢后无法沿现有轴线安装两侧桥螺钉。</td></tr>
</tbody></table><p class="muted">有限候选失败不证明所有顺序都不可行；刚体路径通过也不表示带线、手部支撑或连续净距已通过。</p></section>
<section><h2>为何不能把整体装入直接当成装配完成</h2>
<a href="assembly_access.png"><img src="assembly_access.png" alt="当前实体截面：整体抬升姿态，以及上壳与向外移动2毫米的承重桥螺钉相交"></a>
<p>两侧实际螺钉模型向外移动 2 mm 时，各与上壳相交约 5.50 mm³。这里已用实际螺钉实体复核；不能只看五段插头路径或整体抬升图就放行。</p>
<p>另按 <a href="https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated">Wera 950 PKLS 05022041001 官方尺寸</a>检查了 2 mm 内六角、5.5 mm 短边、100 mm 长边的保守工具包络，闭壳状态没有通过的候选朝向。实际弯头形状和扭矩仍未验证。</p>
<p><a href="../head_module_sequence_v2/review.json">完整刚体阶段和零件清单</a> · <a href="../head_module_tools/review.json">工具与螺钉筛查</a> · <a href="geometry_review.json">实际相交坐标证据</a></p></section>
<section><h2>下一步的边界</h2><ul>
<li>继续联立预穿线、头部子装配和承重桥锁紧顺序。不能先固定一个孤立的最终线形，再假定其他线和工具都能穿过。</li>
<li>完整供电引线、USB 尾部、全部自由端移动、线长保持和弯曲检查尚未闭合。</li>
<li>SCS0009 舵盘和锁紧叠层、实际压接端子及成品线资料仍是独立输入；不以规划包络代替实物配套证据。</li>
</ul><p>C6、线导向和固定候选仍未采用。本页没有提出新增开孔、移动电路板或其他未经确认的结构改动。</p></section>
<details><summary>检查记录与诊断修正</summary><ul>
<li><a href="../power_side_access/review.json">八种侧向退出路径</a></li>
<li><a href="../power_plug_search/review.json">无外壳时的裸胶壳路径搜索</a> · <a href="../power_plug_simple/review.json">五段连续扫掠</a></li>
<li><a href="../power_cover_dependency/review.json">加入外壳后的依赖检查</a></li>
<li><a href="../power_staging/review.json">三组供电线转动</a> · <a href="../power_staging_contour/review.json">四组沿实际孔壁调整</a></li>
<li><a href="../power_late_access/review.json">早期轴向诊断</a>的 Power 名称匹配过宽，排除了板卡固定件；只作历史诊断，不用于宣称固定件净距通过。后续侧向和搜索检查已纠正。</li>
<li><a href="../head_module_sequence/review.json">第一次整体移动诊断</a>没有完整划分装配阶段：下壳和部分连接螺钉仍在，Yaw 输出件未随桥移动。保留记录，但其结果不用于判断完整头部模块路径；使用上方 v2 的明确零件清单。</li>
</ul><p><a href="main_integrity.json">主模型、硬件、STL 和动画保留核验</a> · <a href="plot_review.json">图片来源</a></p></details></main></html>'''
(OUT/'index.html').write_text(page)
note='''# CAM 供电与头身装配顺序

M1.49 C5+K1 已应用，孔壁修正不受本轮研究影响。完整线束仍 BLOCKED。

- 裸供电胶壳在身体两片外壳均未安装时存在五段连续平移路径。已保留其他上部候选线和身体固定线；这不包含它自身两根完整导线。加入上壳后路径相交，不能作为后插供电顺序。
- 先接 J18、临时移动两根供电线：三组转动与四组轮廓调整均受 Pitch_Yoke 实体阻挡。根部固定，但上端未完成、线长改变、恢复动作未验证，均未采用。
- 整体移动头部与桥，同时独立倾斜上壳：抬升19 mm候选的383个位置无相交。包含72件头部/桥模块、22件上壳模块；下壳、外壳及框架连接螺钉在后续安装。只是刚体采样检查。
- 该顺序尚不能实施：上壳闭合后两侧桥螺钉外移2 mm的实际实体分别相交5.5032 mm³。短柄工具包络也未通过。闭壳锁紧不能因整体路径通过而省略。

继续研究的方向是预穿线与分阶段头部装配、桥锁紧同步安排。先完成整段装配顺序，再请求必要的结构确认；不得把失败试验、未知端子和单独的 PASS 拼接成完整线束合格。

保留两个已纠正的初筛：power_late_access 的排除名过宽；head_module_sequence 的装配阶段清单不完整。后续报告给出准确边界。没有修改主模型、硬件、STL 或动画，没有制造放行。
'''
(REST/'POWER_SEQUENCE_PROGRESS.md').write_text(note)
rootpage=BASE/'index.html';content=rootpage.read_text()
content=re.sub(r'<!-- POWER_SEQUENCE_PROGRESS -->.*?<!-- /POWER_SEQUENCE_PROGRESS -->','',content,flags=re.S)
block='''<!-- POWER_SEQUENCE_PROGRESS --><section id="power-sequence-progress"><h2>供电线和头身装配：补查了锁紧依赖</h2><p>整体头部与承重桥的383个刚体位置通过初筛，但上壳闭合后，两侧桥螺钉的实际装入空间受阻。无壳插头通路、供电线临时排布也不能直接组成可执行顺序；完整带线装配仍未通过。</p><p><a href="cam_restraints/power_sequence_review/index.html">实际剖面、阶段清单与限制</a> · <a href="cam_restraints/POWER_SEQUENCE_PROGRESS.md">记录</a></p></section><!-- /POWER_SEQUENCE_PROGRESS -->'''
assert '</main>' in content;rootpage.write_text(content.replace('</main>',block+'</main>'))
commandfile=BASE/'upper_connection_commands.json';c=read(commandfile)
paths={r['argv'][-1] for r in commands};c['commands']=[r for r in c['commands'] if r['argv'][-1] not in paths]+commands
c['utc']=now;write(commandfile,c)
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[])
state['CAM_power_sequence']=dict(status='BLOCKED',open_body_bare_plug='PASS',same_path_with_upper_shell='BLOCKED',
    temporary_supply_pose_families=7,temporary_supply='BLOCKED',preassembled_head_rigid_path='PASS',rigid_samples=383,
    bridge_lift_mm=19,closed_shell_bridge_fastening='BLOCKED',actual_screw_overlap_at_2mm_each_mm3=5.503208749559778,
    evidence='cam_restraints/power_sequence_review/index.html',main_applied=False)
state['last_completed_independent_work']='Body supply plug access and temporary wire staging checked; complete head/bridge has a 383-position rigid path, but actual bridge screw insertion is blocked by closed upper shell.'
state['next_work']=list(dict.fromkeys(state['next_work']))
state['next_work'].append('The open-body late J18 plug path is blocked by the upper shell. Whole-head-plus-bridge rigid insertion at19mm lift passes383 samples, but closed-shell bridge fastening fails on actual screw solids. Rework the prethreaded subassembly/bridge-tightening order; do not adopt the naked-plug or rigid-head paths as a complete assembly sequence. Reaction horn/axial stack and actual crimps remain unresolved.')
state['review_url']='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT))
write(BASE/'continuation_status.json',state)
assets += [OUT/'index.html',OUT/'main_integrity.json',OUT/'assembly_access.png',REST/'POWER_SEQUENCE_PROGRESS.md',rootpage,commandfile,Path(__file__),HERE/'verify_remaining_publication.py']
pub=read(BASE/'publication.json');pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in set(assets)})
pub.update(utc=now,CAM_power_sequence='BLOCKED: nominal rigid module path does not close bridge fastening or complete wires',
           power_sequence_publish_command=[sys.executable,*sys.argv],power_sequence_publisher_sha256=sha(Path(__file__)),full_harness='BLOCKED')
write(BASE/'publication.json',pub)
print('CAM_POWER_SEQUENCE_PUBLISHED',len(commands),'commands',len(set(assets)),'files')
