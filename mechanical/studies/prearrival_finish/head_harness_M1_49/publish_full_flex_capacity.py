"""Publish bounded full-span investigations while retaining all failed cases."""
from pathlib import Path
import datetime,hashlib,json,re,sys
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]; BASE=HERE/'remaining_routes'
FLEX=BASE/'static_flex'; FULL=FLEX/'full_route'; CAM=FLEX/'camera_corridor'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,r:p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
jobs=[
 ('screen_full_static_flex.py','static_flex_full_screen.log',FULL/'screen/review.json','FULL_FFC_SCREEN_DONE'),
 ('screen_full_static_flex_tail.py','static_flex_full_tail.log',FULL/'tail_screen/review.json','FULL_FFC_TAIL_SCREEN_DONE'),
 ('review_full_static_flex_obstructions.py','static_flex_obstruction_review.log',FULL/'obstructions/review.json','FFC_OBSTRUCTION_REVIEW_DONE'),
 ('screen_camera_flex_corridor.py','camera_flex_corridor.log',CAM/'review.json','CAMERA_FPC_CORRIDOR_DONE'),
 ('screen_full_static_flex_mixed.py','static_flex_full_mixed.log',FULL/'mixed_screen/review.json','FULL_FFC_MIXED_SCREEN_DONE'),
 ('check_full_static_flex_motion.py','static_flex_full_motion.log',FULL/'motion/review.json','FULL_FFC_MOTION_DONE'),
 ('review_camera_flex_entry.py','camera_flex_entry.log',CAM/'entry/review.json','CAMERA_FPC_ENTRY_REVIEW_DONE'),
 ('screen_camera_flex_front.py','camera_flex_front.log',CAM/'front_turn/review.json','CAMERA_FRONT_TURN_DONE'),
 ('screen_full_static_flex_lead.py','static_flex_short_lead.log',FULL/'short_lead/review.json','FULL_FFC_SHORT_LEAD_DONE'),
 ('screen_camera_flex_terminal.py','camera_flex_terminal.log',CAM/'terminal/review.json','CAMERA_TERMINAL_DONE'),
 ('check_full_static_flex_short_motion.py','static_flex_short_motion.log',FULL/'short_motion/review.json','FULL_FFC_SHORT_MOTION_DONE'),
 ('review_full_flex_capacity.py','static_flex_full_review.log',FULL/'review/review.json','FULL_FLEX_CAPACITY_REVIEW_DONE'),
]
commands=[]
for script,log,result,token in jobs:
    s=HERE/script; l=BASE/log; r=read(result); txt=l.read_text()
    assert sha(s)==r['script_sha256'],script
    assert token in txt and 'Blender quit' in txt and 'Traceback' not in txt,(script,token)
    assert not r['main_changed']
    for file,h in {**r.get('sources',{}),**r.get('inputs',{})}.items(): assert sha(ROOT/file)==h,file
    commands.append(dict(argv=['/Applications/Blender.app/Contents/MacOS/Blender','--background',
        'mechanical/mori_v1_2.blend','-t','2','--python-exit-code','1','--python',str(s.relative_to(ROOT))],
        cwd=str(ROOT),exit_code=0,log=str(l.relative_to(ROOT)),log_sha256=sha(l),
        script_sha256=sha(s),result=str(result.relative_to(ROOT)),result_sha256=sha(result),check_status=r['status']))
failure=read(FULL/'failures/syntax_failure.json'); failure['log']=str((FULL/'failures'/failure['log']).relative_to(ROOT))
failure['log_sha256']=sha(ROOT/failure['log'])
assert sha(ROOT/failure['script_snapshot'])==failure['script_sha256']
write(FULL/'commands.json',dict(status='PASS',utc=now,commands=commands,failed_executions=[failure],
    scope='Exit-zero executions include FAIL/BLOCKED geometric candidates; the failed import remains separately preserved.',
    script_sha256=sha(Path(__file__))))

motion=read(FULL/'short_motion/review.json'); view=read(FULL/'review/review.json'); camera=read(CAM/'terminal/review.json')
assert motion['status']=='PASS' and view['status']=='PASS' and camera['status']=='BLOCKED'
camrow=next(x for x in camera['rows'] if x['id']=='T2_W6.6')
gap=motion['closest_candidate_wire']['surface_gap_lower_bound_mm']
requirements=dict(status='BLOCKED',scope='Geometric requirements and missing evidence; not a supplier production drawing',
    main_revision='V1.2-M1.49 C5+K1',main_changed=False,procurement_authorized=False,manufacturing_release=False,
    LCD=dict(source_route='L2_W10.5',stock_length_allocation_mm=200,free_span_mm=194,
        connector_zone_budget_total_mm=6,connector_budget_is_actual_insertion=False,
        width_allocation_mm=10.5,thickness_allocation_mm=.2,minimum_radius_allocation_mm=5,
        radii_mm=[5,5,7.5,7.5,7.5,7.5],rear_free_straight_mm=2.,
        assumed_endpoint_outside_package_mm=.6,first_bend_distance_from_package_bound_mm=2.6,
        lead_limit_note='The current candidate uses this lead; larger or smaller allowed lead intervals have not been established.',
        maximum_distributed_roll_deg_per_mm=motion['geometric_parameters']['maximum_twist_deg_per_mm'],
        pose_samples=130,candidate_conductor_checks=1430,minimum_wire_gap_lower_bound_mm=gap,
        missing=['exact selected cable and connector revisions','actual mouth center/height and contact/pin1 view',
            'insertion/stiffener lengths and no-bend zones','supplier-approved bend and roll capability','retention and actual installation sequence']),
    camera=dict(source_route='T2_W6.6',free_corridor_length_mm=camrow['parameters']['length_mm'],
        width_allocation_mm=6.6,thickness_allocation_mm=.15,minimum_radius_allocation_mm=3.,terminal_straight_mm=2.,
        nominal_frame_side_gap_mm=.3,raw_mesh_gap_mm=camrow['failures'][0]['gap_mm'],
        conservative_chord_bound_pass=False,full_factory_FPC_length_mm=None,extension_selected=False,
        missing=['full factory FPC length/profile and true tail exit','contact fanout and any stiffener/no-bend zones',
            'compatible longer-tail module or extension if required','tolerance/retention and camera capture fit']),
    evidence={str(p.relative_to(ROOT)):sha(p) for p in [FULL/'short_motion/review.json',FULL/'review/review.json',CAM/'terminal/review.json',FLEX/'connector_faces/direction_receipt.json']})
write(FULL/'interface_requirements.json',requirements)
text=f'''# 完整排线空间候选复核

主模型仍为 M1.49 C5＋K1，打印件、板卡和装配视频均未改动。本次输出是独立可编辑的空间候选，不是已选型或已插接的真实排线。

## 屏幕排线

此前 170＋15＋15 mm 分配与官方出口方向不符。本次按 CAM 向 −X 出线、LCD 从 −X 插入重建，194 mm 自由段、6 mm 两端预算，合计200 mm。两端中心仍取模拟包络，6 mm不代表已确认插深或补强长度。

L2_W10.5 候选采用10.5×0.2 mm截面、后侧两弯R5、其余四弯R7.5。它在130个离散头部姿态下通过3408组邻近刚性对象检查和1430组候选导线检查，导线净距下界最小约{gap:.3f} mm；66组非相邻排线分段、自身避让和前后壳各273个拆装位置也通过。壳路径这里只增加“壳与新排线”的检查，不重定义完整带线装配顺序。

**限制：** CAM出座端模型基准之外只有2 mm直线，按当前假定基准相当于距插座包络边2.6 mm处开始弯曲。实际补强片若延伸超过这里，候选便不成立。宽、厚、半径和分布扭转均未获得材料/供应商确认，端部插接、固定和整根线装入未完成。不能以空间PASS代替真实FFC选型。

第一次全长度布局与俯仰舵机相交；将第一个回弯后移后消除了刚性碰撞，但仍与四根CAM导线交叉。将该回弯收进导线内侧后才通过上述有限样本。失败模型和日志均保留。

## 相机排线

官方照片支持CAM端向+Z出线。按原有相机下缘的假定出口，建立上方通道、末端直线2 mm的容量模型，自由通道长约{camrow['parameters']['length_mm']:.2f} mm。这不是原配FPC实测长度，也不能据此选任意24P延长线。

6.6 mm宽的末段在当前座内名义侧隙仅0.3 mm；网格值约0.2999999 mm，加入圆弯离散误差的保守检查未通过，结论保持BLOCKED。更宽12.5 mm的整段假设与卡座相交。真实FPC的宽窄变化、完整长度和补强区未知，因此未缩窄假件来宣称合格，也未更改卡座。

## 未关闭事项

仍需确认排线/连接器实际型号、接触面、补强和允许弯曲；补齐固定及完整带线装入。C6颈部局部方案和导线约束结构未获采用；CAM穿线及反力连杆装配、其他线束端点等仍在总清单中。不是只剩实物验证，也没有发布生产图。

彩图中金色、紫色和蓝色分别区分屏幕通道、相机通道和已有CAM导线候选；这些颜色用于路径诊断，均不是采购确认。隐藏外壳后留下的壳螺钉不是新增悬空零件。
'''
(FULL/'README.md').write_text(text)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M1.49 完整排线空间复核</title><style>body{{font:16px/1.7 system-ui;margin:0;background:#f3f6f7;color:#243743}}main{{max-width:1100px;margin:auto;padding:28px 24px}}h1{{font-size:30px}}h2{{margin-top:36px}}a{{color:#126894}}.note{{padding:14px 18px;background:#fff1d5;border-left:5px solid #cc8720}}figure{{margin:18px 0;background:white;padding:14px;border-radius:10px}}img{{width:100%;height:auto}}figcaption{{font-size:14px}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:11px;border-bottom:1px solid #d8e1e5}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}</style><main>
<p><a href="../../index.html">线束总进展</a> · <a href="../connector_faces/index.html">官方入口方向证据</a></p>
<h1>屏幕完整自由段已通过空间检查，实际排线仍待定型</h1>
<p class="note">主模型 M1.49 C5＋K1 保持。这里是通道容量研究，未采用新打印结构、未选定排线、未发生产图；完整线束仍为 BLOCKED。</p>
<figure><a href="review/overview.png"><img src="review/overview.png" alt="头部完整排线路径空间候选"></a><figcaption>金色：194 mm屏幕自由段；紫色：相机通道假设；蓝色：四根CAM导线候选。路径颜色用于诊断，均不表示已采购或已验证实物。外壳隐藏，部分原壳螺钉因此单独可见。</figcaption></figure>
<h2>屏幕：避开舵机，也避开左侧导线</h2>
<p>后侧回弯采用R5容量假设，收在CAM四根线的内侧；剩余弯为R7.5。原厂200 mm长度按194 mm自由段＋6 mm两端预算研究，端部实际插深和补强长度仍未知。</p>
<table><tr><th>检查</th><th>结果与范围</th></tr><tr><td>头部130个姿态</td><td>PASS：3408组邻近刚性对象，1430组候选导线；导线净距下界约{gap:.3f} mm。</td></tr><tr><td>排线自身与头壳</td><td>PASS：66组非相邻分段；前后壳各273个平移位置。</td></tr><tr><td>真实端部与材料</td><td>BLOCKED：插座/线材型号、补强区、触点面、允许弯曲及固定、装入尚未确认。</td></tr></table>
<figure><a href="review/rear_return.png"><img src="review/rear_return.png" alt="后侧屏幕回弯与CAM导线之间的空间"></a><figcaption>这是收在导线内侧的独立候选。先前较外侧回弯虽避开舵机，却会穿过四根CAM导线，失败记录保留。</figcaption></figure>
<p class="note">最关键的选型条件：当前基准后只有2 mm直线，约在插座包络边外2.6 mm处开始弯曲。补强片如果延伸到这里，候选就不成立。R5不是厂家的允许弯曲半径，空间检查不证明材料可承受。</p>
<h2>相机：通道约{camrow['parameters']['length_mm']:.2f} mm，末段侧隙仍很紧</h2>
<p>末端增加2 mm直线，可避免早期圆弯直接碰座边。但按6.6 mm宽的假定细尾，名义侧隙仅0.3 mm，加入离散误差后的保守检查未通过。原配FPC完整长度、宽窄变化和出尾细节尚不完整；没有改卡座或选任意延长线。</p>
<div class="grid"><figure><a href="../camera_corridor/entry/side.png"><img src="../camera_corridor/entry/side.png" alt="相机上方通道的早期定位图"></a><figcaption>早期定位图：利用CAM板上方的既有空间；镜头端圆弯贴近卡座，不能直接作为最终线。</figcaption></figure><figure><a href="review/top.png"><img src="review/top.png" alt="两类排线空间候选的俯视图"></a><figcaption>最新整体俯视。两类排线的空间候选之间未检出相交，具体线材及约束仍未确定。</figcaption></figure></div>
<h2>完整线束尚未完成</h2><p>除了真实排线接口，还需完成固定和带线装入；C6及导线约束结构未采用，CAM穿线和反力连杆装配仍有未解决项。这些没有被改称为“只等实物”。</p>
<p><a href="review/MORI_M1_49_full_FFC_capacity.blend">可编辑 Blender 候选</a> · <a href="interface_requirements.json">给选型/供应商核对的尺寸条件（非生产图）</a> · <a href="README.md">详细结论</a></p>
<p><a href="short_motion/review.json">130姿态与导线检查</a> · <a href="review/review.json">壳路径与自身检查</a> · <a href="../camera_corridor/terminal/review.json">相机边界检查</a> · <a href="commands.json">12次执行与保留失败</a> · <a href="main_integrity.json">主文件保留检查</a></p>
<p><a href="obstructions/review.json">最初刚性碰撞定位</a> · <a href="motion/review.json">较外侧回弯的导线碰撞</a> · <a href="short_lead/review.json">回弯内收的有限比较</a></p>
</main></html>'''
(FULL/'index.html').write_text(page)

main_delivery=read(HERE.parent/'neck_adoption/delivery.json'); protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for f,h in {**main_delivery['files'],**protected}.items(): assert sha(ROOT/f)==h,f
exports=read(ROOT/'mechanical/reports/export_manifest.json')
for row in exports['parts']: assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
animation=read(ROOT/'mechanical/animation/delivery.json')
for f,h in animation['files'].items(): assert sha(ROOT/'mechanical'/f)==h,f
write(FULL/'main_integrity.json',dict(status='PASS',utc=now,main_changed=False,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),config_sha256=sha(ROOT/'config/geometry.json'),
    main_files_checked=len(main_delivery['files']),protected_hardware_files_checked=len(protected),
    STL_files_checked=len(exports['parts']),animation_files_checked=len(animation['files']),animation_revision=animation['animation_revision']))
for page,relative in [(BASE/'index.html','static_flex/full_route/index.html'),(FLEX/'index.html','full_route/index.html')]:
    old=page.read_text(); old=re.sub(r'<!-- FULL_FLEX_UPDATE -->.*?<!-- /FULL_FLEX_UPDATE -->','',old,flags=re.S)
    section=f'''<!-- FULL_FLEX_UPDATE --><section id="full-flex"><h2>后续：完整排线空间候选</h2><p>194 mm屏幕自由段已通过130个姿态、候选导线与头壳拆装空间检查。CAM端补强长度和允许弯曲仍未知；相机通道末段仅约0.3 mm名义侧隙，完整排线及线束均未完成。</p><p><a href="{relative}">查看最新空间候选、失败记录和选型条件</a></p></section><!-- /FULL_FLEX_UPDATE -->'''
    page.write_text(old.replace('</main>',section+'</main>'))
state=read(BASE/'continuation_status.json'); state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str((FULL/'index.html').relative_to(ROOT)))
state['full_flex_capacity']=dict(status='PASS',scope='Short-lead LCD free-span capacity only',candidate='L2_W10.5',pose_samples=130,
    wire_gap_lower_bound_mm=gap,actual_LCD_FFC='BLOCKED',camera_FPC='BLOCKED',main_applied=False,
    evidence='static_flex/full_route/index.html')
state['last_completed_independent_work']='194 mm LCD free-span with correct endpoint directions; 130 poses, 1430 candidate-wire checks, 66 nonadjacent self pairs, 546 shell samples. Camera corridor requirements and marginal capture gap recorded.'
state['next_work']=[x for x in state['next_work'] if not x.startswith('CAM-FPC-EXIT-R1 received:')]
state['next_work'] += ['LCD short-lead capacity now passes; actual slot/stiffener/no-bend/radius data must close the 2 mm free-lead constraint before adoption. Do not call 6 mm connector budget actual insertion.',
    f"Camera upper corridor is approximately {camrow['parameters']['length_mm']:.2f} mm for T2_W6.6, with only 0.3 mm nominal capture-side gap. Full factory FPC profile/length is unknown; actual compatibility and tolerance remain BLOCKED. Do not scale the tail or cut the capture without a reviewed option.",
    'Correct the independently evidenced CAM camera visual entrance (+Z) and display mouth (-X) separately; do not rotate both complete connector bodies. Main visual source remains unchanged.']
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json'); assert not pub['C6_approved']
assets=[p for folder in [FULL,CAM] for p in folder.rglob('*') if p.is_file() and p.suffix not in ['.blend1','.pyc']]
assets += [HERE/script for script,_,_,_ in jobs]
assets += [HERE/n for n in ['full_static_flex_geometry.py','full_static_flex_tail_geometry.py','full_static_flex_mixed_geometry.py','camera_flex_corridor_geometry.py','camera_flex_terminal_geometry.py',Path(__file__).name]]
assets += [BASE/'index.html',FLEX/'index.html',HERE/'verify_remaining_publication.py',*[BASE/log for _,log,_,_ in jobs]]
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in assets})
pub.update(utc=now,full_LCD_free_span_capacity='PASS with assumptions',full_LCD_FFC='BLOCKED',camera_FPC='BLOCKED',full_harness='BLOCKED',
    full_flex_publisher_sha256=sha(Path(__file__)),full_flex_publish_command=[sys.executable,*sys.argv])
write(BASE/'publication.json',pub)
print('FULL_FLEX_CAPACITY_PUBLISHED',len(commands),'commands',len(assets),'files')
