"""Publish the unapproved, fully reviewable CAM screw/tool candidate."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,re,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_socket_tool'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=read(OUT/'screen.json');v=read(OUT/'verification.json');r=read(OUT/'render_manifest.json')
ws_path=A8/'cam_board_last/continuous_wire_solids.json';ws=read(ws_path)
assert ws['status']=='PASS' and not ws['unproved_intervals']
assert ws['script_sha256']==sha(A8/'check_CAM_board_wire_sweeps.py')
assert ws['helper_sha256']==sha(A8/'check_CAM_board_last.py')
assert ws['screen_sha256']==sha(A8/'cam_board_last/screen.json')
assert ws['continuous_wire_to_wire_packing']=='NOT_TESTED' and not ws['main_applied']
packing=read(A8/'cam_board_last/continuous_packing.json')
forming=read(A8/'cam_wire_forming/raised/screen.json')
fc=read(A8/'cam_wire_forming/continuous/screen.json');fct=read(A8/'cam_wire_forming/terminals/screen.json')
assert fc['status']=='BLOCKED' and fct['status']=='PASS' and not fc['complete_coverage'] and fc['unproved_intervals']
assert fc['source_terminal_screen_sha256']==sha(A8/'cam_wire_forming/terminals/screen.json')
assert packing['status']==forming['status']=='PASS'
assert packing['script_sha256']==sha(A8/'check_CAM_board_continuous_packing.py')
assert not packing['unproved_intervals'] and forming['continuous_motion']=='NOT_TESTED'
assert s['status']==v['status']==r['status']=='PASS'
assert r['verification_sha256']==sha(OUT/'verification.json')
assert len(v['head_motion'])==130 and all(x['status']=='PASS' for x in v['head_motion'])
assert r['physical_parts_preserved_unchanged']==209
main_hash=sha(ROOT/'mechanical/mori_v1_2.blend');assert main_hash==s['source_main_sha256']
critical=read(A8/'cam_wire_forming/lifted_end2/contact_refined_forming/critical_return_continuous/screen.json')
current_forming_file=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/negative_complete/screen.json'
current_forming=read(current_forming_file)
assert current_forming['status']=='PASS' and current_forming['complete_four_wire_forming_coverage']
assert current_forming['source_main_sha256']==main_hash
rootdir=current_forming_file.parent.parent/'root_tie_access'
roottool=read(rootdir/'screen.json');rootfeed=read(rootdir/'contact_feed.json')
assert roottool['status']=='PASS' and rootfeed['status']=='BLOCKED'
assert roottool['source_main_sha256']==rootfeed['source_main_sha256']==main_hash
seatingdir=current_forming_file.parent.parent/'root_seating/aligned_tails'
seating=read(seatingdir/'verification.json')
assert seating['status']=='PASS' and seating['source_main_sha256']==main_hash
detail=f'CAM四线成形动作已通过{current_forming["continuous_interval_count"]}个连续区间，8个步骤边界一致；空胶壳外部接近和板卡8→2mm下降也已通过。已补查完整线尾在场时的根部剪尾工具和朝外扎带尾空间：名义通过，但工具对扎带的0.25mm间隔未满足通用0.3mm余量。收紧后沿所查竖直轴穿端子会碰到打印座和带身；初次穿线、扎带收紧、端子入壳及其他线路仍需完成。四枚CAM内六角螺钉仍待确认；主模型未改，尚无正式裁线图。'
detail+=f' 另已完成未装根部扎带时的四线侧向入座：{seating["continuous_intervals"]}个连续区间通过，线长和下方端点保持。初次端子绕行到此起点与扎带穿绕仍未完成。新增官方端子图显示底部锁止弹片未包含在原1.35mm尺寸内，旧方盒检查不代表真实端子全外形已通过。'
md='''# CAM固定工具候选：四枚M2×5改内六角

本页是独立候选，尚未采用。供应商按图制作线束已经确定，公开资料由项目继续搜集；本次新取得的工具与标准螺钉尺寸，解决了前一版CAM后装工序的一个工具障碍。

## 推荐改动

只将四枚CAM固定螺钉从GB823十字盘头换成 **DIN912/ISO4762 M2×5内六角头**。孔位、5mm杆长、四个嵌件、板卡、舵机及所有打印件都不变。螺钉头由直径3.5×高1.4mm变为直径3.8×高2mm；零件数量不增加。

工具采用 **Wera 950 PKLS / 05022040001，1.5mm内六角，长边90mm、短边4.5mm**。用短端锁紧，长端向上伸出头框供握持。头部原有舵机耳螺钉也使用1.5mm内六角，不增加新的驱动规格。

![扳手从上方进入](key_access.png)

![短端进入螺钉，保留舵机与后板](socket_closeup.png)

绿色是扳手检查包络，不是新增的机器人杆件；方形转角包络有意覆盖未知弯曲轮廓。彩色线仅区分四条候选几何线，不代表最终针序或线色。两处已有线束固定座仍属于未采用的线束候选。

## 厂家资料

| 项目 | 来源与已知尺寸 | 证据边界 |
|---|---|---|
| Wera 950 PKLS 05022040001 | [官方产品页](https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated)，[保存的官方PDF](sources/Wera_05022040001.pdf)：1.5mm、90mm、4.5mm | 尺寸已公开；圆弧弯头不是厂家CAD，检查体按偏大的圆杆和转角包络构造 |
| Bossard BN610 1420569 | [厂家CAD目录](https://bossard.partcommunity.com/3d-cad-models/?info=bossard%2F01%2F01_100%2F01_100_100%2F01_100_100_10%2Fbn_610_612_31101%2Fbn_610.prj&languageIso=de)：A2、M2×5、头径3.8、头高2、内六角1.5、槽深至少1、螺距0.4mm | 按公开参数重建名义包络；没有冒充厂家STEP，没有拟合或验证真实螺纹 |
| VESSEL TD-74、ENGINEER DR-55 | [VESSEL](https://www.vessel.co.jp/english/product/screwdriver/250074)为18mm头；[ENGINEER](https://www.nejisaurus.engineer.jp/product-page/dr-55-%E3%82%AA%E3%83%95%E3%82%BB%E3%83%83%E3%83%88%E3%83%A9%E3%83%81%E3%82%A7%E3%83%83%E3%83%88%E3%82%BB%E3%83%83%E3%83%88-%E8%96%84%E5%9E%8B)为22mm头 | 不适用于原十字螺钉附近约14.71mm的轴向名义空间；不能因产品叫“薄型”就认定放得下 |

[来源文件与哈希](sources/receipt.json)。这里只提出机械选型，没有核价、下单或证明预算达标。

## 装配顺序与检查

1. 保留俯仰及水平舵机，暂不装显示支架和头壳。沿[前一版板卡后装研究](../cam_board_last/index.html)将CAM临时抬6mm完成插头插合，再落座。四条线总长不增加。
2. 三枚螺钉从上方送入，先在孔前8mm处对齐，再沿孔轴进入。右下CAM_Mount_Screw_2上方有板上器件，改从正前方沿轴送入；没有删除这个器件或更改PCB。
3. 短扳手从上方进入，用短边驱动。已检查从−30°到+30°的连续60°摆动，以及0–8mm连续轴向空间，覆盖拧入过程和退出1mm重新插入。完整工具、螺钉、所有现有舵机和四线都参与检查。
4. 线束固定及后续合壳仍按线束总工序继续完成；本页不将整机装配标记为完成。

| 检查 | 结果 |
|---|---|
| 四枚新螺钉在名义最终位置及装入路径 | PASS；保留每枚螺钉与其自身嵌件的螺纹配对排除，不排除PCB或打印件 |
| 扳手连续60°摆动＋轴向行程 | PASS；使用包围整个角度范围的外切扇形实体，不只比较几个角度 |
| 扳手从上方进入90mm | PASS；四处都检查完整长边与短边 |
| 入口握持区 | PASS；在工具上端额外检查直径18×长25mm的假设空间，不是手部动作或扭矩验证 |
| 新螺钉随头部转动 | PASS；yaw −60…60°、pitch −20…25°共130个姿态，与当前全部209个物理对象逐件比较 |
| 头部四线的板卡后装变形 | 两段6mm插合/落座过程中，连续线形对当时已安装实体、线与线及非相邻自接近检查通过；初始穿线成形及真实插合仍未完成 |
| 完整线束与制造放行 | BLOCKED |

按连续扳手工作体计算，最小名义间隙约0.43mm（到候选扎带）；到打印支架约0.58mm，到CAM板器件约1.29mm。不能把1.29mm当成整体最小间隙。这些是当前尺寸模型的计算值，CAM照片估算部件、真实工具弯头、打印偏差及手部操作仍需实物复核。

新增[连续线对实体检查](../cam_board_last/continuous_wire_solids.json)：把连接器插合与CAM板下落分成两个6mm行程，用曲线位移上界、真实结构件的距离及弦误差覆盖全部中间位置。共128个自适应区间全部通过，保留原0.3mm名义间隙要求和原有固定/出线接触区域；没有缩小线径或改变线路。初始姿态为头部机械零位，显示支架及头壳等尚未安装，具体零件清单见报告。

之后另补[连续线间检查](../cam_board_last/continuous_packing.json)，用14组固定/包围路线、解析分离界限和8个自适应区间覆盖四线及非相邻自接近，最小已证表面间隙下界约0.306mm。初次成形发现中途碰撞；[先抬高回环的候选与对比图](../cam_wire_forming/index.html)已有41个位置通过，连续过程和末端压接件仍未查完。因此这些检查不是线束力学、初次穿线成形或整机装配完成的证明。

## 保留的失败路线

原直柄PH1刀杆会撞到俯仰舵机。另检查了[舵机后装的8条路径](../cam_servo_last/screen.json)：水平舵机保留时阻挡横移；两舵机后装的几条既定路径会触及已摆好的线形。这些失败只针对所测路径，不声称其他工序不可能。此次采用更换标准螺钉头型作为推荐候选。

CAM_Mount_Screw_2的垂直送入试验也保留在verification.json，候选选择已通过的前方轴向送入，不覆盖或隐去失败。

主模型M1.47、config、STL、动画及hardware均未更改。本候选采用与否按用户“有疑问先确认”的要求待确认。PA12强度、实物插合、紧固扭矩和线束动态寿命不由这些几何检查保证。

[独立Blender](review.blend) · [初步检查](screen.json) · [连续工作体/装入/运动](verification.json) · [实际命令](commands.json) · [交付清单](review_manifest.json)
'''
md=md.replace('已有41个位置通过，连续过程和末端压接件仍未查完。',f'原41位置筛查之后，[加入散端子并检查连续过程](../cam_wire_forming/terminals/index.html)发现末段对头托间隙不足。{len(fc["passed_intervals"])}个区间已证，原整段仍为BLOCKED；新的2mm临时抬高方案仅有限位置通过，连续、线间和装壳工序仍待完成。')
md=md.replace('新的2mm临时抬高方案仅有限位置通过，连续、线间和装壳工序仍待完成。','[最新逐根路线](../cam_wire_forming/lifted_end2/index.html)已从负侧绕开原相交位置，四线规定成形动作的连续检查和步骤衔接通过；板卡8→2mm连续下降也已通过。初始穿线、真实端子入壳、扎带及完整装配仍未完成。')
(OUT/'README.md').write_text(md)
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM螺钉与工具候选</title><style>
body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f4f6f5;color:#253b3d;max-width:1040px;margin:28px auto;padding:0 24px 60px}a{color:#096a74}h1{font-size:30px}.note{background:#fff0d9;padding:18px;border-radius:10px}img{width:100%;border-radius:8px}figure{margin:24px 0}figcaption{font-size:14px}td,th{padding:12px;border-bottom:1px solid #cad7d2;text-align:left}table{border-collapse:collapse;width:100%}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:700px){.pair{display:block}}</style>
<p><a href="../../index.html">← 当前未完成项</a> · <a href="../index.html">A8研究</a> · <a href="../cam_board_last/index.html">前一版工具阻挡</a></p>
<h1>CAM螺钉改内六角，支架保持原样</h1>
<p class="note">待确认候选：四枚M2×5只换头型，孔位、嵌件、板卡、舵机和打印件不变。工具转动、进入、螺钉装入及130个头部姿态检查通过。主模型尚未修改，完整线束仍未完成。</p>
<div class="pair"><figure><img src="../cam_board_last/screw_tool_obstruction.png" alt="原直柄十字刀杆穿过舵机"><figcaption>之前：直柄PH1刀杆被舵机挡住。</figcaption></figure><figure><img src="socket_closeup.png" alt="内六角短端进入螺钉，长端向上"><figcaption>候选：短边4.5mm的内六角扳手从上方操作。</figcaption></figure></div>
<h2>改动很局部</h2><p>四枚CAM固定螺钉保持M2×5，改DIN912/ISO4762内六角头：头径3.5→3.8mm，头高1.4→2mm。数量不变，没有新增孔、避让槽或支架。1.5mm内六角也已用于头部舵机耳螺钉。</p>
<figure><img src="key_access.png" alt="完整90毫米长扳手向上伸出头框"><figcaption>绿色为工具的保守检查包络，不是新机器人零件。显示支架和头壳留到之后安装；现有两只舵机保留。</figcaption></figure>
<h2>公开尺寸已找到</h2><p><a href="https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated">Wera 950 PKLS 05022040001</a>：1.5mm内六角，90mm长边、4.5mm短边，<a href="sources/Wera_05022040001.pdf">官方PDF</a>已保存。螺钉采用<a href="https://bossard.partcommunity.com/3d-cad-models/?info=bossard%2F01%2F01_100%2F01_100_100%2F01_100_100_10%2Fbn_610_612_31101%2Fbn_610.prj&languageIso=de">Bossard BN610 1420569</a>公开参数重建名义包络；尚未采购，没有把重建模型标成官方STEP。</p>
<table><tr><th>验证</th><th>结果与边界</th></tr><tr><td>四枚螺钉装入</td><td>通过。三处上方送入；右下角从前方沿孔轴进入，避开板上器件。</td></tr><tr><td>扳手动作</td><td>连续60°摆动、0–8mm轴向工作空间、90mm上方进入均通过；最小名义间隙约0.43mm（候选扎带）；到打印支架约0.58mm、到板上器件约1.29mm。</td></tr><tr><td>头部运动</td><td>四枚新螺钉在130个头部姿态中未检出新增刚性干涉。</td></tr><tr><td>四线插合与落座</td><td><a href="../cam_board_last/continuous_wire_solids.json">连续线对实体检查</a>通过：两段6mm行程，128个带位移上界的区间覆盖全过程，保持0.3mm名义间隙。连续线间检查也已通过，间隙下界约0.306mm；<a href="../cam_wire_forming/index.html">初次成形仍待完善</a>。</td></tr><tr><td>实物与完整线束</td><td>实际工具、紧固扭矩、手部操作及动态寿命待验证。穿线、其他线路、最终裁线图仍未完成。</td></tr></table>
<p>供应商按图制作线束已确定。JST连接器、端子与压接资料见<a href="../TOOLING_DETAILS.md">完整料号查询记录</a>；CAM实际插座厂牌、物理针腔视图及SCS0009原配舵盘资料仍需进一步确认。本次没有把标准工具资料当作这些缺项已经解决的证据。</p>
<p><a href="README.md">完整说明</a> · <a href="review.blend">独立Blender</a> · <a href="verification.json">检查结果</a> · <a href="sources/receipt.json">来源和哈希</a> · <a href="commands.json">命令</a> · <a href="review_manifest.json">交付清单</a></p></html>'''
(OUT/'index.html').write_text(html)
for suffix,dest in [('', 'screen.log'),('_verify','verification.log'),('_render','render.log')]:
    log=Path('/tmp/mori_CAM_socket_tool'+suffix+'.log')
    if log.is_file():shutil.copyfile(log,OUT/dest)
    else:assert (OUT/dest).is_file(),f'Missing preserved execution log: {OUT/dest}'
if Path('/tmp/mori_CAM_servo_last.log').is_file():shutil.copyfile('/tmp/mori_CAM_servo_last.log',A8/'cam_servo_last/screen.log')
else:assert (A8/'cam_servo_last/screen.log').is_file(), 'Missing preserved servo-last log'
commands=[f'/Applications/Blender.app/Contents/MacOS/Blender --background {blend} -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/{script}' for blend,script in [
 ('mechanical/mori_v1_2.blend','check_CAM_servo_last.py'),('mechanical/mori_v1_2.blend','check_CAM_socket_tool.py'),('mechanical/mori_v1_2.blend','verify_CAM_socket_tool.py'),('mechanical/studies/prearrival_finish/harness_A8/cam_wired_cradle/review.blend','render_CAM_socket_tool.py')]]
commands.append('/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/check_CAM_board_wire_sweeps.py')
if Path('/tmp/mori_CAM_board_wire_sweeps.log').is_file():shutil.copyfile('/tmp/mori_CAM_board_wire_sweeps.log',A8/'cam_board_last/continuous_wire_solids.log')
else:assert (A8/'cam_board_last/continuous_wire_solids.log').is_file(), 'Missing preserved wire sweep log'
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},indent=2)+'\n')
p=PARENT/'work_status.json';state=read(p);row=next(r for r in state['remaining'] if r['id']=='harness');old=row['detail']
detail+=' 新增JST APSH同料号细节图和工装信息已存档。初次穿线补查16组端子路线、21个同步整理位置及3种抬高路线，均未通过当前筛查；这是仍可继续处理的装配设计，不能归为仅等实物。'
source_update=read(A8/'supplier_source_update/verification.json')
assert source_update['vertical_free_feed']=='PASS' and source_update['vertical_feed_allocations']==8
assert source_update['progressive_staging']=='BLOCKED'
detail+=' 后续8组竖直端子行程的局部扫掠通过，但从下向上整理的41个位置仍未通过；两步未连成完整装配。M5Stack官方摇臂STL已归档为连接参考，未替代SCS0009配套确认。'
assert source_update['ordered_feed_finite']==source_update['ordered_recovery_finite']=='PASS'
assert source_update['ordered_continuous']=='PASS'
detail='同样1×1.8×4.1mm假设端子预留尺寸下，CAM上部逐根穿入1228、回位256、入座256、四段弯线1735个连续区间通过；已核对步骤衔接，弯线调整两处临时动作。身体侧完整供线尚未建模：当前步骤每根约有140–162mm原有材料需要暂存，下一步评估头部在机身外先穿线、身体端最后接入。扎带穿绕收紧、真实端子插装、其余跨关节线和FPC仍未完成。四枚CAM内六角螺钉仍待确认；研究候选未应用主模型，正式裁线图未放行。'
if not (OUT/'previous_work_status.json').exists():shutil.copyfile(p,OUT/'previous_work_status.json')
row.update(detail=detail,evidence='harness_A8/cam_wire_forming/lifted_end2/index.html');state['updated_utc']=datetime.now(timezone.utc).isoformat()
state['A8_harness_research'].update(latest_review='harness_A8/cam_wire_forming/lifted_end2/index.html',CAM_socket_screw_candidate='PASS',CAM_socket_screw_candidate_main_applied=False,
    CAM_socket_screw_candidate_approval=state['A8_harness_research'].get('CAM_socket_screw_candidate_approval','NOT_REQUESTED'),CAM_socket_key_continuous_angle_deg=60,CAM_socket_head_motion_poses=130,
    CAM_socket_candidate_review='harness_A8/cam_socket_tool/index.html',CAM_whole_connected_installation='BLOCKED')
state['A8_harness_research'].update(CAM_board_last_continuous_wire_to_solids='PASS',
    CAM_board_last_continuous_wire_to_wire='PASS',CAM_board_last_continuous_intervals=len(ws['passed_intervals']),
    CAM_board_last_continuous_review='harness_A8/cam_board_last/continuous_wire_solids.json')
state['A8_harness_research'].update(CAM_board_last_continuous_packing_intervals=len(packing['adaptive_intervals']),
    CAM_initial_forming_direct='BLOCKED',CAM_initial_forming_raised_positions='PASS',
    CAM_initial_forming_raised_amplitude_mm=forming['selected_amplitude_mm'],CAM_initial_forming_continuous='BLOCKED',
    CAM_initial_forming_terminal_shapes='PASS',CAM_initial_forming_terminal_evidence='ASSUMED catalogue span envelope; exact post-crimp profile unknown',
    CAM_initial_forming_continuous_scope='Wire and nominal bare contacts to forming-stage solids only',
    CAM_initial_forming_continuous_intervals=len(fc['passed_intervals']),CAM_initial_forming_continuous_complete_coverage=False,
    CAM_initial_forming_wire_packing='BLOCKED',CAM_initial_forming_lift2_positions='PASS',CAM_initial_forming_lift2_continuous='NOT_TESTED',
    CAM_lift2_board_descent_continuous='PASS',CAM_lift2_board_descent_intervals=1057,
    CAM_lift2_nominal_wire_collision='FAIL',CAM_lift2_revised_forming_trials='PASS',
    CAM_lift2_revised_forming_trial_scope='Finite sequential order3/2/1/0 at644 positions; continuous and real terminal handling remain open',
    CAM_sequential_forming_positions='PASS',CAM_sequential_forming_position_count=644,
    CAM_sequential_forming_contact_nonpenetration='PASS',CAM_sequential_forming_contact_margin='BLOCKED',
    CAM_sequential_forming_continuous='BLOCKED',CAM_sequential_forming_wire_intersection='FAIL',
    CAM_sequential_forming_finite_evidence_superseded=True,
    CAM_critical_return_continuous=critical['status'],CAM_critical_return_complete_local_coverage=critical['complete_local_coverage'],
    CAM_critical_return_full_sequence_coverage=False,CAM_sequential_forming_main_applied=False,
    CAM_initial_forming_housed_trials='BLOCKED',CAM_initial_forming_review='harness_A8/cam_wire_forming/lifted_end2/index.html')
state['A8_harness_research'].update(
    CAM_current_forming_continuous='PASS',CAM_current_forming_complete_coverage=True,
    CAM_current_forming_interval_count=current_forming['continuous_interval_count'],
    CAM_current_forming_boundary_identity='PASS',
    CAM_current_forming_receipt='harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/negative_complete/screen.json',
    CAM_current_forming_receipt_sha256=sha(current_forming_file),
    CAM_current_forming_scope=current_forming['scope'],CAM_current_forming_main_applied=False,
    CAM_housing_external_approach='PASS',CAM_housing_terminal_insertion='NOT_TESTED',
    CAM_root_tie_cutter_nominal='PASS',CAM_root_tie_general_rigid_margin='BLOCKED',
    CAM_root_tie_outward_tail_space='PASS',CAM_root_tie_tight_contact_feed='BLOCKED',
    CAM_root_tie_full_installation='NOT_TESTED',
    CAM_root_tie_tool_receipt_sha256=sha(rootdir/'screen.json'),
    CAM_root_tie_feed_receipt_sha256=sha(rootdir/'contact_feed.json'),
    CAM_root_wire_seating_finite='PASS',CAM_root_wire_seating_continuous='PASS',
    CAM_root_wire_seating_intervals=256,CAM_root_wire_seating_receipt_sha256=sha(seatingdir/'verification.json'),
    CAM_initial_terminal_bypass='BLOCKED',CAM_tie_threading_and_tightening='NOT_TESTED',
    CAM_initial_terminal_bypass_scope='Upper feed, recovery, seating and forming pass continuous geometry bounds using the same larger ASSUMED contact allocation; complete body supply, ties and real terminals remain unclosed',
    CAM_initial_terminal_bypass_review='harness_A8/supplier_source_update/index.html',
    CAM_APSH_source_receipt='harness_A8/ssh_catalogue_addendum/apsh/retrieval.json',
    CAM_vertical_free_feed=source_update['vertical_free_feed'],
    CAM_vertical_free_feed_scope=source_update['vertical_feed_scope'],
    CAM_vertical_free_feed_receipt_sha256=source_update['vertical_feed_receipt_sha256'],
    CAM_progressive_staging='BLOCKED',CAM_progressive_staging_positions=41,
    CAM_ordered_terminal_feed_finite=source_update['ordered_feed_finite'],
    CAM_ordered_terminal_feed_positions=source_update['ordered_feed_positions'],
    CAM_ordered_recovery_finite=source_update['ordered_recovery_finite'],
    CAM_ordered_recovery_positions=source_update['ordered_recovery_positions'],
    CAM_ordered_retraction_sweep=source_update['ordered_retraction_sweep'],
    CAM_ordered_boundary_match=source_update['ordered_boundary_match'],
    CAM_ordered_continuous='PASS',CAM_ordered_main_applied=False,
    CAM_ordered_feed_continuous_intervals=source_update['ordered_feed_continuous_intervals'],
    CAM_ordered_recovery_continuous_intervals=source_update['ordered_recovery_continuous_intervals'],
    CAM_body_supply='BLOCKED',
    CAM_body_supply_review='harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/README.md',
    CAM_large_contact_seating='PASS',CAM_large_contact_seating_intervals=256,
    CAM_large_contact_forming='PASS',CAM_large_contact_forming_intervals=1735,
    CAM_large_contact_review='harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/large_contact_downstream/index.html',
    CAM_large_contact_publication_sha256=source_update['larger_contact_publication_sha256'],
    CAM_ordered_review='harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/ordered_feed_recovery/index.html',
    CAM_ordered_publication_sha256=source_update['ordered_publication_sha256'],
    M5_servo_arm_reference='PASS',M5_servo_arm_MORI_interface='BLOCKED',
    CAM_terminal_catalogue_span_is_complete_envelope=False,
    CAM_terminal_extra_catalogue='harness_A8/ssh_catalogue_addendum/README.md')
p.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';t=p.read_text();assert old in t;t=t.replace(old,detail).replace('harness_A8/cam_board_last/index.html','harness_A8/cam_socket_tool/index.html').replace('最新：CAM板后装与剩余工具阻挡','最新：CAM螺钉与短扳手候选')
t=t.replace('最新：CAM螺钉与短扳手候选','最新：CAM四线连续成形').replace('最新：CAM板卡下降与弯线冲突','最新：CAM四线连续成形').replace('href="harness_A8/cam_socket_tool/index.html">查看原厂尺寸、两种出线与未完成项','href="harness_A8/cam_wire_forming/lifted_end2/index.html">查看连续成形与未完成项').replace('查看板卡下降、线间冲突与未完成项','查看连续成形与未完成项');p.write_text(t)
for p,link in [(A8/'index.html','cam_wire_forming/lifted_end2/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_wire_forming/lifted_end2/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_wire_forming/lifted_end2/index.html')]:
    t=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM螺钉与短扳手候选</h2><p>{detail}</p><p><a href="{link}">查看局部改动与检查</a></p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM螺钉与工具候选</h2><p>{detail}</p><p><a href="{link}">查看局部改动与检查</a></p></section>{b}'
    block=block.replace('CAM螺钉与短扳手候选','CAM四线连续成形').replace('CAM螺钉与工具候选','CAM四线连续成形').replace('查看局部改动与检查','查看新路线与未完成项')
    t,n=re.subn(pat,block,t,flags=re.S);assert n==1;p.write_text(t)
p=A8/'README.md';t=p.read_text();t,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM内六角螺钉与短扳手候选](cam_socket_tool/index.html)：四处螺钉装入、60°连续工具动作及130个头部姿态通过；只换同长度螺钉头型，主模型未改，采用与否待确认。完整线束尚未完成。\n<!-- /A8_PITCH_FLEX_LATEST -->',t,flags=re.S);assert n==1;p.write_text(t)
t=t.replace('最新见[CAM内六角螺钉与短扳手候选](cam_socket_tool/index.html)：四处螺钉装入、60°连续工具动作及130个头部姿态通过；只换同长度螺钉头型，主模型未改，采用与否待确认。完整线束尚未完成。','最新见[CAM四线连续成形](cam_wire_forming/lifted_end2/index.html)：四线规定成形动作及8个步骤边界通过；板卡8→2mm连续下降保持通过。初始穿线、端子入壳、扎带和完整工序仍未完成。四枚内六角螺钉仍待确认，主模型未改。');p.write_text(t)
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
(OUT/'review_manifest.json').write_text(json.dumps({'status':'PASS','scope':'Review candidate and source consistency; whole harness incomplete','script_sha256':sha(SCRIPT),
 'source_main_sha256':main_hash,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
 'main_applied':False,'approval':state['A8_harness_research']['CAM_socket_screw_candidate_approval'],'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==main_hash
print('CAM_SOCKET_PUBLISHED',len(files),flush=True)
