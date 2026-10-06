"""Publish scoped static-flex evidence; preserve main and previous studies."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';OUT=BASE/'static_flex'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
paths=[OUT/'endpoints.json',OUT/'core_screen/review.json',OUT/'motion/review.json',OUT/'review/review.json']
reports=[read(p) for p in paths]
for r in reports:
    assert r['status']=='PASS' and not r['main_changed']
    for p,h in {**r['sources'],**r.get('inputs',{})}.items():assert sha(ROOT/p)==h,p
motion=reports[2];view=reports[3]
assert motion['poses']==130 and motion['wire_checks']==1430
assert all(r['samples']==273 and r['status']=='PASS' for r in view['shell_paths'])
assert view['parameters']['analytic_length_mm']==170.
assert view['parameters']['unmodeled_end_approach_reserve_mm']==[15,15]

jobs=[('inspect_static_flex.py','static_flex_inspection_v2.log',paths[0]),
      ('screen_static_flex_core.py','static_flex_core.log',paths[1]),
      ('check_static_flex_motion.py','static_flex_motion.log',paths[2]),
      ('review_static_flex.py','static_flex_review.log',paths[3])]
commands=[]
for script,log,p in jobs:
    s=HERE/script;l=BASE/log;r=read(p)
    assert sha(s)==r['script_sha256']
    assert 'Blender quit' in l.read_text() and 'Traceback' not in l.read_text()
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background',
        'mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
        script_sha256=sha(s),result=str(p.relative_to(ROOT)),result_sha256=sha(p),check_status=r['status']))
failed=BASE/'static_flex_inspection.log'
assert "KeyError: 'Head_Lower_Guard'" in failed.read_text()
write(OUT/'commands.json',dict(status='PASS',utc=now,commands=commands,
    tools=dict(Blender='5.2.2 LTS d13f752e3b9c',Python='3.13 bundled with Blender',manifold3d='3.5.3'),
    failed_executions=[dict(log=str(failed.relative_to(ROOT)),log_sha256=sha(failed),exit_code=1,
        command=commands[0]['argv'],cause="Absent historical object Head_Lower_Guard",
        fix='Record absent historical names and enumerate only current existing parts.',
        original_script_snapshot=None,limitation='Original pre-fix source was not separately saved; no original source hash is claimed.')],
    script_sha256=sha(Path(__file__))))

main=read(HERE.parent/'neck_adoption/delivery.json')
protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for p,h in {**main['files'],**protected}.items():assert sha(ROOT/p)==h,p
ex=read(ROOT/'mechanical/reports/export_manifest.json')
for row in ex['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
animation=read(ROOT/'mechanical/animation/delivery.json')
for p,h in animation['files'].items():assert sha(ROOT/'mechanical'/p)==h,p
write(OUT/'main_integrity.json',dict(status='PASS',utc=now,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),main_changed=False,
    config_sha256=sha(ROOT/'config/geometry.json'),main_delivery_files_checked=len(main['files']),
    protected_hardware_files_checked=len(protected),STL_files_checked=len(ex['parts']),
    animation_revision=animation['animation_revision'],animation_files_checked=len(animation['files']),
    script_sha256=sha(Path(__file__))))

sources=[
    dict(url='https://docs.waveshare.com/1.85inch_Touch_LCD_Module',retrieved='2026-10-06',
        status='PASS',supports='SKU35079, 18-pin external FPC interface; not cable bend or insertion specification'),
    dict(url='https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx',retrieved='2026-10-06',
        status='PASS',supports='SKU33700 and 18-pin display interface; actual purchased revision remains unknown'),
    dict(url='https://www.waveshare.com/catalog/product/view/id/8439/s/1.85inch-touch-lcd-module/category/346/',
        retrieved='2026-10-06',status='PASS',method='Official-domain search result content',
        supports='Included cable 18 contacts, 0.5 mm pitch, 200 mm length, same-side contacts',
        limitation='Direct short product URL returned403. No cable width, thickness, stiffener, insertion or radius drawing retrieved.')]
write(OUT/'documentation_sources.json',dict(status='PASS',utc=now,sources=sources,
    local_reference_images={str(p.relative_to(ROOT)):sha(p) for p in [
        HERE.parent/'head_harness/sources/lcd_connector_photo.webp',
        ROOT/'mechanical/sources/waveshare_detail/ESP32-S3-CAM-OVxxxx-details-inter.jpg']},
    no_supplier_contact=True,no_BOM_change=True))

note='''# 头内屏幕排线：静态收纳容量预检

当前主模型为 **M1.49 C5＋K1**。本页是未应用的独立空间研究，不是新的打印件、完整排线或制造图。

## 已查清的范围

屏幕、CAM 板和相机都在同一俯仰运动组。当前主模型的 130 个偏航／俯仰组合姿态，两个接口对的中心间距变化小于 0.000006 mm（变换浮点误差）。这说明端点之间无需由头部运动引起的相对伸缩；前提是未来固定点也在同一运动组。不能把端点关系当作完整布线或疲劳证明。

LCD 的外部主控接口为官方 CAD 的 **Connector_108 / L1**；Connector_107 是屏本体内部连接。接口包络只用来定位，没有当成插入深度、接触面或线尾出口。板上引脚文字与电气功能仍以硬件交接为准。

官方随屏线为 **18P、0.5 mm 间距、200 mm、同面触点**。来源为[微雪产品页](https://www.waveshare.com/catalog/product/view/id/8439/s/1.85inch-touch-lcd-module/category/346/)；[屏幕文档](https://docs.waveshare.com/1.85inch_Touch_LCD_Module)和[CAM 文档](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)用于接口识别。此次没有取得原线宽厚、补强、插入深度、弯曲半径或两端触点面配对图。

## 收纳容量

- 中间 **170 mm** 做成平面内连续圆弧；没有扭转、锐折或沿排线宽度方向硬弯。总长剩余 **30 mm** 暂分配为两端各 15 mm，端部没有建模，绝不代表已接上两个插座。
- 采用 **10.5 mm 宽、0.2 mm 厚、R7.5 mm、中心 Z238 mm** 作为容量假设，全部标为 ASSUMED。R7.5 不是厂家允许弯曲半径；模型也没有仿真回弹或松垂。
- 比较 R5/R7.5、宽9.5/10.5、Z236/Z238 的8种有限组合，中央段的零位容量均通过名义几何检查；未搜索全部可能路径。
- 所示组合在130姿态下，对当前刚体及11条已有候选导线逐项筛查通过。刚体间距查询上限1 mm，结果表示至少1 mm，不是精确最小值。1430次导线组合均在相关距离扩张包围盒外；不是完成全部导线的实体装配。
- 前壳沿 +Y、后壳沿 -Y 各0～68 mm、0.25 mm步长的273个位置，与中央收纳段没有新增干涉。这里只验证此排线段不会挡住指定壳体路径，不能替代整机装配顺序。

没有增加打印件、开孔、胶粘件或固定夹；图中红点是未连接的端部。当前仅证明有地方容纳这段平直带材，**尚未证明它可以无固定地保持该形状**。

## 仍需完成

1. 确定实际两端插接方向、触点面和插入长度，画完预留的30 mm端部，重新核对完整200 mm线长。
2. 取得真实宽厚、补强区和厂家允许弯曲数据；用真实数据替换容量假设，设计应力释放并验证插入／关闭过程。
3. 相机原配完整FPC长度及出口未知；照片中的10.5 mm只是可见段，不能据此选任意延长线。
4. CAM线束临时穿入、身体端固定、其他头部接口和反力连接仍是独立未完成项。此中央段通过不关闭这些问题。

完整屏幕排线 **BLOCKED**；完整线束 **BLOCKED**；实物装配、固定可靠性和弯曲寿命 **NOT_TESTED**。C6、导向和夹持座仍待批准；本研究没有采用它们或改动主模型、STL、视频、硬件源文件。
'''
(OUT/'README.md').write_text(note)
blend=OUT/'review/MORI_M1_49_static_FFC_capacity.blend';assert sha(blend)==view['blend_sha256']
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M1.49 屏幕排线收纳预检</title><style>body{font:16px/1.75 system-ui;margin:0;background:#f4f6f7;color:#20303b}main{max-width:1050px;margin:auto;padding:32px 24px}h1{font-size:30px}h2{margin-top:34px}a{color:#1e658c}img{max-width:100%;border-radius:12px}figure{margin:24px 0}figcaption{color:#4c6070}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:12px;border-bottom:1px solid #d9e1e6}.note{border-left:5px solid #d79726;background:#fff7e8;padding:15px 20px}.small{font-size:14px}</style><main>
<p><a href="../index.html#static-flex">返回线束总进展</a></p><h1>头内排线有收纳空间；两端尚未连接</h1>
<p class="note">主模型 M1.49 C5＋K1 未改动。橙色是未应用的170 mm中央段容量模型；红点是未连接端部。两端共30 mm只作长度预算，图中未建模。</p>
<figure><img src="review/central_span.png" alt="橙色静态收纳段，红点标示未连接的两端"><figcaption>连续圆弧收纳，不增加打印件。宽厚和允许弯曲半径仍需确认，排线的固定与端部插入尚未完成。</figcaption></figure>
<table><tr><th>这次完成</th><th>检查范围</th></tr>
<tr><td>屏幕／相机端点的运动关系</td><td>同属俯仰组，130姿态保持相对位置；不需要因头部运动而在端点间反复弯折。</td></tr>
<tr><td>中央段收纳容量</td><td>170 mm，假定宽10.5、厚0.2、R7.5 mm；8种参数组合预检通过。</td></tr>
<tr><td>运动中的中央段空间</td><td>130姿态，对当前刚体及已有11条候选线的1430个组合通过有限检查。</td></tr>
<tr><td>前后壳指定平移路径</td><td>各273个位置与该中央段无新增干涉；不是完整带线装配通过。</td></tr></table>
<h2>尚未完成</h2><p>两端触点面、插入深度和过渡形状；实际线宽、厚度、补强和允许弯曲半径；固定、应力释放和插拔过程。完整屏幕排线及完整线束仍为 BLOCKED。</p>
<p>200 mm随屏线的规格来自<a href="https://www.waveshare.com/catalog/product/view/id/8439/s/1.85inch-touch-lcd-module/category/346/">微雪产品资料</a>。没有用容量假设代替厂家尺寸，也未将该模型加入主模型或装配视频。</p>
<figure><img src="review/top.png" alt="静态收纳段俯视图"><figcaption>从上方看中央段形状。它避开了相机支架和舵机，但暂时没有用于保持形状的固定设计。</figcaption></figure>
<p><a href="README.md">范围、假设与剩余工作</a> · <a href="review/MORI_M1_49_static_FFC_capacity.blend">可编辑 Blender 候选</a> · <a href="sections.png">当前头部剖面</a></p>
<p class="small"><a href="endpoints.json">接口与运动组</a> · <a href="core_screen/review.json">容量组合</a> · <a href="motion/review.json">姿态检查</a> · <a href="review/review.json">壳体路径</a> · <a href="main_integrity.json">主文件保留检查</a> · <a href="commands.json">命令记录</a> · <a href="documentation_sources.json">资料来源</a></p>
</main></html>'''
(OUT/'index.html').write_text(page)

mainpage=BASE/'index.html';text=mainpage.read_text()
section='''<!-- STATIC_FLEX_PROGRESS --><section id="static-flex"><h2>新增：屏幕排线中央段的收纳容量已检查</h2>
<p>屏幕、CAM和相机同属俯仰组。独立候选的170 mm中央段已通过130姿态及指定前后壳平移路径检查，暂按两端各15 mm预留原配200 mm排线的剩余长度。</p>
<p><strong>两端未连接，宽厚和允许弯曲半径仍是假设。</strong>固定、应力释放、相机FPC和完整带线装配尚未完成；主模型、STL和视频不变。</p>
<a href="static_flex/index.html"><img src="static_flex/review/central_span.png" style="width:100%" alt="屏幕排线中央段容量候选"></a>
<p><a href="static_flex/index.html">查看收纳候选与明确边界</a> · <a href="static_flex/README.md">剩余要求</a></p></section><!-- /STATIC_FLEX_PROGRESS -->'''
text=re.sub(r'<!-- STATIC_FLEX_PROGRESS -->.*?<!-- /STATIC_FLEX_PROGRESS -->','',text,flags=re.S)
text=text.replace('</main>',section+'</main>');mainpage.write_text(text)
(BASE/'README.md').write_text('''# M1.49 线束候选

主模型C5＋K1已应用。最新新增[屏幕静态收纳容量](static_flex/index.html)：170 mm中央段通过有限检查，但两端未接、固定和真实线材数据未闭合，不能视为整根排线完成。

[此前CAM穿线进展](index.html#cam-threading)保留：离机固定、带自由线尾落座、临时弯回和第一根名义端子下穿分别通过；后续端子及颈部完整穿入仍受限。

完整线束BLOCKED。C6、导向和夹持座未批准／未应用；主模型、STL、视频与硬件源文件未变。没有制造放行。
''')
state=read(BASE/'continuation_status.json')
state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str((OUT/'index.html').relative_to(ROOT)))
state['static_flex']=dict(status='PASS',scope='Untwisted 170mm central packing capacity only',
    two_end_approaches='NOT_TESTED',selected_material_dimensions=False,full_LCD_flex='BLOCKED',
    report='static_flex/index.html',main_applied=False,poses=130)
state['next_work']=[x for x in state['next_work'] if not x.startswith('Complete body strain relief')]
state['next_work'] += [
    'Static LCD central-span capacity is documented, not the full cable. Resolve both mating directions/contact faces and actual FFC data before completing 30mm of reserved ends, anchoring and insertion.',
    'Complete body strain relief, other upper endpoints, actual camera FPC and the full wired assembly. Preserve unresolved reaction-link and crimp dependencies.',
    'No structural candidate or stock FFC material has been adopted by the capacity study. C6 approval is still pending.']
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json')
assert not pub['C6_approved'] and pub['source_blend_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assets=list(OUT.rglob('*'));assets=[p for p in assets if p.is_file()]
assets += [HERE/s for s in ['inspect_static_flex.py','static_flex_geometry.py','screen_static_flex_core.py',
    'check_static_flex_motion.py','review_static_flex.py','plot_static_flex_sections.py',Path(__file__).name]]
assets += [mainpage,BASE/'README.md']
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in assets})
pub.update(utc=now,static_LCD_core_capacity='PASS',full_LCD_FFC='BLOCKED',full_harness='BLOCKED',
    static_flex_publisher_sha256=sha(Path(__file__)),static_flex_publish_command=[sys.executable,*sys.argv])
write(BASE/'publication.json',pub)
print('STATIC_FLEX_PUBLISHED',len(commands),'commands',len(assets),'files',flush=True)
