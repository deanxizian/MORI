"""Publish the independent assembly-access candidate and the failed alternatives."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'body_front_rear_split'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat();assets=[];commands=[]
specs=[
 ('inner_head_body_access','screen_inner_head_body_access_pose.py','inner_head_body_access.log','INNER_HEAD_BODY_ACCESS_DONE','review.json'),
 ('reaction_short_tool_deferred_J3','check_reaction_tool_deferred_J3.py','reaction_deferred_J3.log','REACTION_DEFERRED_J3_DONE','review.json'),
 ('reaction_ball_tool','screen_reaction_ball_tool.py','reaction_ball_tool.log','REACTION_BALL_TOOL_DONE','review.json'),
 ('body_front_rear_split','study_body_front_rear_split.py','body_front_rear_split.log','BODY_FRONT_REAR_SPLIT_DONE','review.json'),
 ('body_front_rear_split','render_body_front_rear_split.py','body_front_rear_render.log','BODY_SPLIT_RENDER_DONE','render_review.json'),
 ('body_front_rear_split','check_body_split_core_access.py','body_split_core_access.log','BODY_SPLIT_CORE_ACCESS_DONE','core_access.json')]
for directory,script,log,token,resultname in specs:
    folder=REST/directory;s=HERE/script;l=BASE/log;result=folder/resultname;r=read(result)
    assert sha(s)==r['script_sha256'],script
    assert token in l.read_text() and 'Traceback' not in l.read_text() and 'Blender quit' in l.read_text(),log
    assert not r['main_changed'] and not r['approved'] and r['Yaw_Reaction_Link_present']
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
    for row in r.get('images',[]):assert sha(folder/row['file'])==row['sha256']
    for row in r.get('parts',{}).values():assert sha(ROOT/row['file'])==row['sha256']
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background','mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),script_sha256=sha(s),result=str(result.relative_to(ROOT)),result_sha256=sha(result),check_status=r['status']))
    assets.extend([s,l,*[p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]])
candidate=read(OUT/'review.json');core=read(OUT/'core_access.json')
assert candidate['status']==core['status']=='PASS'
assert all(row['status']=='PASS' for row in candidate['paths']+candidate['frame_tool_access'])
source=read(REST/'reaction_ball_tool/source.json')
assert sha(REST/'reaction_ball_tool'/source['source_file'])==source['source_sha256']
main=read(HERE.parent/'neck_adoption/delivery.json');protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for f,h in {**main['files'],**protected}.items():assert sha(ROOT/f)==h,f
exports=read(ROOT/'mechanical/reports/export_manifest.json');animation=read(ROOT/'mechanical/animation/delivery.json')
for row in exports['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
for f,h in animation['files'].items():assert sha(ROOT/'mechanical'/f)==h,f
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,main_changed=False,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),config_sha256=sha(ROOT/'config/geometry.json'),
    main_files_checked=len(main['files']),protected_hardware_files_checked=len(protected),
    STL_files_checked=len(exports['parts']),animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>身体前后分壳候选 · 待确认</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f6;color:#20313a;font:17px/1.65 system-ui,sans-serif}main{max-width:1120px;margin:auto;padding:28px 24px 70px}
h1{font-size:30px;line-height:1.3}h2{font-size:23px;margin-top:0}section{background:white;border:1px solid #d5dfe3;border-radius:12px;padding:23px;margin:24px 0}
a{color:#126b84}img{display:block;width:100%;height:auto}figure{margin:0}figcaption{font-size:15px;color:#50636e;padding:10px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.badge{display:inline-block;padding:4px 12px;background:#fff0d9;color:#835412;border-radius:14px;font-weight:650}.lead{font-size:19px}.muted{color:#526771}
table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #dbe2e6;padding:11px}th{background:#eef3f5}li{margin:9px 0}
@media(max-width:720px){main{padding:18px 12px}.pair{grid-template-columns:1fr}section{padding:16px}h1{font-size:26px}}
</style><main><a href="../../index.html">← 走线与装配工作页</a><h1>先锁紧内部，再从前后合上身体外壳</h1>
<p><span class="badge">独立候选，尚未应用</span></p>
<p class="lead">前后分壳的刚体拆装、四处螺钉入口和 130 个头部姿态检查通过。它为头部连接提供了可操作空间；完整带线合壳、最终传动接口仍未通过。</p>
<p>主模型仍是 M1.49 C5＋K1。你已确认的压板孔壁修正保持，主 Blender、STL 和 M1.49-A1 动画没有被本候选替换。</p>
<section><h2>改变的是身体分缝，打印件仍为两件</h2><div class="pair">
<figure><a href="current.png"><img src="current.png" alt="当前身体上下分壳，水平分缝"></a><figcaption>当前：上下两片。合上上壳后，工具难以到达反力连杆；先预装连杆又挡住头架落座。</figcaption></figure>
<figure><a href="candidate_closed.png"><img src="candidate_closed.png" alt="候选身体前后分壳，分缝经过两侧和底部"></a><figcaption>候选：前后两片，外形母面保留。蓝色与米色仅用于区分两片；最终仍可统一暖白色。</figcaption></figure></div>
<p class="muted">两图都隐藏了头部与右侧轮胎／轮毂，便于比较身体分缝；这些零件没有被设计删除。</p>
<table><thead><tr><th>项目</th><th>当前</th><th>候选</th></tr></thead><tbody>
<tr><td>身体打印件</td><td>上壳＋下壳，共 2 件</td><td>前壳＋后壳，共 2 件</td></tr>
<tr><td>框架固定</td><td>4 枚螺钉＋4 个嵌件</td><td>沿用这 4 处位置、螺钉及嵌件，每半壳固定在两个点</td></tr>
<tr><td>原水平拼缝固定</td><td>4 枚螺钉＋4 个嵌件及壳内座</td><td>取消</td></tr>
<tr><td>外部变化</td><td>水平分缝，原下壳工具孔</td><td>改为前后分缝；壳体下部需要 4 个 Ø6.6 mm 工具孔，原拼缝孔封闭</td></tr>
<tr><td>硬件位置</td><td>当前主模型位置</td><td>板卡、扬声器、轴承、舵机与安装孔轴保持</td></tr>
</tbody></table></section>
<section><h2>内部连接先完成，外壳最后合拢</h2>
<a href="candidate_open.png"><img src="candidate_open.png" alt="前后壳沿前后方向分开，露出内部承重框架"></a>
<p>候选顺序：先装内部框架与头部连接，在外壳尚未安装时锁紧承重桥和反力连杆；再处理壳上扬声器、接口板的连接，最后从前后合壳，锁紧四枚框架螺钉。</p>
<ul><li>两半壳各沿前后方向平移 220 mm，每 1 mm 检查一次；保留车轮的路径均未检出刚体相交。更远处已与核心组件的 Y 范围分离。</li>
<li>承重桥的两枚横向螺钉仍要在装轮胎／轮毂前操作；这部分工具与螺钉的连续轴向扫掠通过。</li>
<li>反力连杆可从正前方使用直柄工具。检查时壳体组件放在远离工具的台面位置；没有声称连接着短导线时也能移到该位置。</li></ul>
<p class="muted">图中半壳分开 90 mm 是展示姿态，头部与导线隐藏。工具检查使用包络，实际螺钉头型啮合和拧紧扭矩不由几何检查认证。</p>
<p><a href="core_access.json">内部工具与螺钉检查</a> · <a href="review.json">候选来源、拆装路径及姿态检查</a></p></section>
<section><h2>需要接受的代价：下部四个工具孔</h2>
<a href="underside_ports.png"><img src="underside_ports.png" alt="壳体下部四个工具孔，蓝色轴表示从下方操作原有框架螺钉"></a>
<p>蓝色表示工具轴线。四孔直径为 6.6 mm，用来从下方送入原有 M3 螺钉和工具。轴线位于原框架固定点 X＝±48、Y＝±42 mm；没有为了新分缝挪动 PCB 或框架孔。</p>
<p>四处工具及实际螺钉均按 150 mm 连续轴向进入／退出检查。原有螺钉与自身嵌件的名义螺纹接合单独记录；扫掠没有增加接合区域之外的相交，实体螺纹配合仍待实物确认。</p></section>
<section><h2>确认的是结构方向，不是整机打样放行</h2><p>建议接受前后分壳与四个下部工具孔，再按这个方向完成带线装配。以下事项仍保留：</p>
<ul><li>两半壳下缘的定位与变形控制需要继续完善；壳体强度、螺钉预紧及 PA12 装配手感需要试打验证。</li>
<li>扬声器、后接口板的最终线长、接头操作和合壳中的导线避让尚未闭合。</li>
<li>SCS0009 原配舵盘、传动叠层与反力连杆局部接口仍待厂家资料，不因新分缝自动通过。</li>
<li>C6 及此前的导向、绑带座候选仍独立，尚未应用；本分壳检查保留主模型原承重桥与头架。</li></ul>
<p><a href="main_integrity.json">主模型、硬件、STL、动画未变核验</a> · <a href="render_review.json">图片来源与隐藏项</a></p></section>
<details><summary>此前尝试为何没有直接采用</summary><ul>
<li>上壳的 180 个倾斜／平移候选、三个头部偏航位置没有找到可用工具姿态：<a href="../inner_head_body_access/review.json">记录</a>。</li>
<li>延后安装电源板 J3 的线端插头后，138 条短柄退出路径仍受 PCB、壳体或扬声器阻挡：<a href="../reaction_short_tool_deferred_J3/review.json">记录</a>。</li>
<li>依据 <a href="https://hybris-media.wera.de/download/pdfgenerator-datasheets/en/05027101001.pdf">Wera 05027101001 官方尺寸</a> 建立球头工具包络，1,442 个方向仍无可用直线进入通道：<a href="../reaction_ball_tool/review.json">记录</a>。25° 是研究范围，厂家未提供的允许角度没有被当作额定值。</li>
<li>这些有限搜索不证明所有手法都不可能。新候选改为让内部连接在外壳合拢之前完成。</li>
<li>检查脚本曾有一次括号语法错误，失败快照保留。实际螺钉头／杆分离改用原网格顶点，避免共面布尔切分留下极薄的宽头切片而夸大扫掠；原结果保留。没有缩小螺钉或放大安装孔来消除报错。</li>
</ul><p><a href="../inner_head_sequence_review/index.html">上一轮压板与反力连杆检查</a></p></details>
</main></html>'''
(OUT/'index.html').write_text(page)
note='''# 前后分壳独立候选

尚未批准或应用；M1.49 C5+K1 主模型、硬件、STL 和动画保持。

为解除反力连杆/承重桥工具被闭合上壳阻挡的依赖，候选把身体两片改为前后两片。保留母面、四个框架固定轴、所有硬件位姿；取消旧水平拼缝的4枚螺钉/4个嵌件及打印座，新增4个直径6.6的下部工具孔。打印件数量不增加。

两个半壳有轮状态各221个1mm步长刚体位置通过。原四枚框架螺钉和工具的150mm连续轴向扫掠通过；自身名义螺纹接合单列且未增加额外相交。130个头部姿态未检出与新壳相交。核心桥螺钉需先不装轮胎/轮毂；反力横栓的直柄工具入口通过。核心锁紧时外壳放在台面远处，未声称壳上短线已连接。

下一步必须先确认分缝方向/四孔是否可接受，然后完善壳缝定位、短线连接与合壳过程。禁止把本候选替换主模型或写成完整带线装配PASS。SCS0009真实传动接口、强度/公差/工具啮合及物理装配仍待确认。C6/导向/绑带座不在本候选中自动获批。
'''
(OUT/'REVIEW.md').write_text(note)
rootpage=BASE/'index.html';content=rootpage.read_text()
content=re.sub(r'<!-- BODY_SPLIT_REVIEW -->.*?<!-- /BODY_SPLIT_REVIEW -->','',content,flags=re.S)
content=content.replace('最新：压板工具路径已通过，反力连接仍待解决','压板工具路径与反力连接诊断')
block='''<!-- BODY_SPLIT_REVIEW --><section id="body-split-review"><h2>待确认：身体改为前后分壳</h2><p>两半壳刚体拆装和四个框架螺钉入口通过，仍为2件打印件，可取消4枚旧拼缝螺钉和4个嵌件。代价是改变外部分缝、在壳体下部留4个Ø6.6工具孔。候选未应用；完整带线合壳和传动接口仍未通过。</p><p><a href="cam_restraints/body_front_rear_split/index.html">前后对比、打开视图与工具孔</a></p></section><!-- /BODY_SPLIT_REVIEW -->'''
assert '</main>' in content;rootpage.write_text(content.replace('</main>',block+'</main>'))
commandfile=BASE/'upper_connection_commands.json';c=read(commandfile);names={r['argv'][-1] for r in commands}
c['commands']=[r for r in c['commands'] if r['argv'][-1] not in names]+commands;c['utc']=now;write(commandfile,c)
state=read(BASE/'continuation_status.json');state.update(utc=now,active_processes=[])
state['body_front_rear_proposal']=dict(status='BLOCKED',reason='Awaiting user structural-direction confirmation; full wired closure and seam locating design incomplete',
    rigid_paths='PASS',frame_fastener_access='PASS',head_pose_samples=130,head_pose_screen='PASS',
    core_tool_access_with_tyres_deferred='PASS',body_print_count_change=0,retired_screws=4,retired_inserts=4,
    proposed_ports_count=4,proposed_ports_diameter_mm=6.6,approved=False,main_applied=False,
    evidence='cam_restraints/body_front_rear_split/index.html')
state['last_completed_independent_work']='Two-piece front/rear body candidate preserves original frame mount axes, clears sampled rigid shell travel and130 head poses, and permits continuous core/frame fastener access. Structural direction and4 underside ports require user confirmation; connected shell wires and seam location remain unfinished.'
state['next_work'].insert(0,'Await user review of the front/rear body split and4 lower tool ports before adopting or refining that structure. Current main must remain M1.49 C5+K1. Candidate still needs seam location and full flexible speaker/rear-interface closure; no manufacturing release.')
state['review_url']='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT));write(BASE/'continuation_status.json',state)
assets += [OUT/'index.html',OUT/'main_integrity.json',OUT/'REVIEW.md',rootpage,commandfile,BASE/'execution_failures.json',Path(__file__),HERE/'verify_remaining_publication.py']
pub=read(BASE/'publication.json');pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in set(assets)})
pub.update(utc=now,body_split_review='Unapproved candidate: rigid shell/tool paths PASS; full wired assembly BLOCKED',
    body_split_publish_command=[sys.executable,*sys.argv],body_split_publisher_sha256=sha(Path(__file__)),full_harness='BLOCKED')
write(BASE/'publication.json',pub)
print('BODY_SPLIT_REVIEW_PUBLISHED',len(commands),'commands',len(set(assets)),'files')
