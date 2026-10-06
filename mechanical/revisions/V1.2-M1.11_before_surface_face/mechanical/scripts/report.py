"""M1.11 current delivery, generated only from executed Blender evidence."""
from pathlib import Path
import json,html,math,hashlib
from module_report import printing_audit
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text());esc=html.escape
p=json.loads((PROJECT/'config/geometry.json').read_text());v=load('validation.json');mass=load('mass_budget.json');ex=load('export_manifest.json');bm=load('build_manifest.json');motion=load('head_motion.json');wm=load('wheel_clearance.json');parts=load('parts_preview_manifest.json');consistency=load('delivery_consistency.json');rebuild=load('rebuild_check.json');bom=load('bom.json');structure=load('structure_changes.json');change=load('layout_cleanup_changes.json');hardware=json.loads((PROJECT/'contracts/components.json').read_text())
checks={c['id']:c for c in v['checks']};whole=mass['totals']['whole_robot'];hp=mass['totals']['head_pitch'];size=checks['assembled_size']['measurement']['xyz_mm'];imu=checks['imu_underside_rigid_mount']['measurement']
structure['geometry_status']='FAIL' if v['counts']['FAIL'] else 'BLOCKED';structure['validation_summary']=v['counts'];(ROOT/'reports/structure_changes.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2))
hz=load('derived.json')['head_z'];c=hp['center_mm_rounded'];torque=[{'pitch_deg':a,'gravity_Nm':round(abs((c[1]*math.cos(math.radians(a))-(c[2]-hz)*math.sin(math.radians(a)))/1000*hp['mass_g_rounded']/1000*9.81),4)} for a in range(-20,26,5)]
(ROOT/'reports/head_load_estimate.json').write_text(json.dumps({'status':'ASSUMED','gravity_samples':torque,'sampled_max_Nm':round(max(x['gravity_Nm'] for x in torque),3),'inertia_kg_m2':hp['inertia_at_head_joint_kg_m2'][0][0],'dynamic_equation':'gravity+Ixx*alpha+cable/friction; continuous torque not qualified','mass_uncertainty_percent':35},indent=2))
selection='''# 当前部件尺寸依据 · M1.11

没有执行采购，没有将原厂CAD、原生PCB设计或图纸名义尺寸标记为实物测量。硬件文件和 components.json 保持只读。

| 部件 | 模型依据 | 尚待确认 |
|---|---|---|
| Waveshare LCD35079 | 原厂113实体STEP，1:1；有效显示Ø45.68 | 两个缺陷连接器使用保守代理，线缆及购买版本待核 |
| Waveshare CAM33700 | 板框37×37；两颗板载麦克风示意 | 完整装件CAD未取得，镜头/FPC/麦克风坐标仍是部分尺寸或照片估计 |
| WeAct V1.1 | 原厂224实体CAD，按P2基板插接方向刚性放置 | 6mm排母堆叠为假设；真实插座和P3版本需复核 |
| Motion基板 | 原生P2 70×35×1.6及49项库几何，四个原生孔位 | P3文件正在更新，未冒充P3最终装件 |
| IMU | 原生P2 20×16×1.6及8项库几何，原生两孔；器件朝下 | P3器件位置、配对插头和传感器到PCB轴向需复核 |
| 电源板 | 最大PCB80×55×1.6，正面装件+16/背面−3的容量 | 限制包络，不是P3装件模型；长边各1mm背面支承边带禁装件，最终固定孔和连接器待交接 |
| 后接口小板 | 新24×14×1.6提案；顶面开关、底面USB-C、都朝后 | 精确器件与电路在另一任务设计；模型中的器件都是选型要求包络 |
| 扬声器 | Same Sky CMS-4017-34SP，厂图Ø40×17.5，±0.3，25g | 接在上壳，独立后盖；焊片/密封/音腔需实测 |
| 电池 | Tenergy31013 成品3S，名义71×55×20、150g | 导线出口、公差、NTC、均衡、充电方案和本地采购待核 |
| 轮驱与头部舵机 | S288×2、SCS0009×2尺寸图 | 舵盘、轮轴、轴承保持、线口和负载需实物验证 |

原厂来源文件/哈希在 contracts/mechanical_interfaces.json。原生P2来源和STEP哈希在 mechanical/studies/pcb_P2_fit/native_inventory.json。原模型三维尺寸没有为了适配而缩放。橙色表示资料未完整或待选型，不能据此下单或制造。
'''
assembly=f'''# MORI {p['revision']} 组装与打印

头壳默认pitch=0°，底部切面水平，主承重支架沿水平/垂直方向布置。只有圆屏和相机的固定安装角上仰10°；圆屏有效区中心仍在头球正前中心。LCD总成刚性后移4mm以适应安装倾斜，尺寸不变。相机仍有独立额头窗口。

本轮合并主托板、左右短侧板，并用托板上的支承边带代替独立电源托板。机器人本体打印件从{change['printed_parts_before']}件变为{change['printed_parts_after']}件（托架和试打小样另计）；主结构取消8组螺钉/螺母连接。新增原生PCB固定又需要6枚试配螺钉和嵌件，后接口小板需要2枚，因此不把整机螺钉净数量宣传成少8枚。保留轮驱座、Yaw轴承座、屏幕叉架和扬声器后盖这些安装/维修分界。

主托板左右对称，使用连续直边和倒角；前部圆弧让位扬声器，后部圆角开口让位USB/接口板。这两处是有明确用途的开口，不是轮胎随意裁切。四个原有壳体连接点保留。合并件也没有恢复包裹电池的大筒壁。

1. 台面上先从Load_Frame底面安装IMU，两枚M2试配螺钉；器件朝下，固定在刚性托板上。不要增加松软胶垫。PCB轴向变换见imu_mount_transform.json，传感器芯片坐标仍须由硬件/固件按P3方向核对。
2. 安装轮驱和底盖，再将整块主托板组件与轮驱座连接。装载板和WeAct前，检查6mm排母候选是否真能配对。P2运动基板四孔原位固定，电源80×55只是容量与边缘支承；P3最终孔位/压片不在本次伪造。
3. 装电池托盘、软垫和束带。IMU实际三角实体到电池名义包络间距约{imu['battery_actual_solid_gap_mm']:.1f}mm；插头向下10mm的预留位于电池后侧。电池仍按报告的拆壳/卸轮、断线、沿+Y抽出顺序维护。
4. 安装Yaw桥/轴承、转台与反力轴，再装头内倒置Yaw及pitch支撑。头前组件先在台面装LCD三后柱和相机，再通过四个可从侧面操作的螺钉接到直立头托。
5. 后接口小板安装在拆下的身体上壳内，位于两个一体短耳下方，从底面拧两枚螺钉。开关在上、Type-C在下，均朝后。小板的详细要求见../INTERFACE_PCB_REQUIREMENTS.md。没有独立打印接口架、Function_Button或外置RESET。
6. 喇叭保持固定在上壳，独立后盖压紧；接好可断开的音频线和接口板线束，再合壳。不要悬挂着线束拆壳。

打印：外壳仍可用PLA/PETG做外观试样；承重材料/层向需载荷试验。一体托板可比较侧面落床与倒置打印，两个方向都有局部安装柱/短脚支撑需求，未运行切片器，不承诺免支撑。直立屏叉、YawU托和轮驱底盖分别保留简单结构。先试打嵌件、接口局部后壳、轴承及平缝小样，再决定整件。不会把0.3mm当作所有机器通用公差。

几何检查不包含螺纹真实啮合、打印强度、疲劳、手柄/手指、实际线束寿命、音频和热验证。托架使用必须禁轮驱；几何通过不代表断电自立或实机平衡通过。
'''
for n,t in [('采购件选型.md',selection),('purchased_dimensions.md',selection),('组装与打印.md',assembly),('结构简化说明.md',assembly),('设计与选型分工.md',selection),('外购与自制.md',selection+'\n打印件见bom.json和候选STL清单；轮胎、光学片、紧固件另列。\n'),('打印件审查.md',printing_audit(bom))]:(ROOT/'reports'/n).write_text(t)
rows='\n'.join(f"| {c['id']} | {c['status']} | {c['summary']} |" for c in v['checks'])
report=f'''# MORI {p['revision']} 机械交付

已实际运行build、validate、render、export及重复生成检查。头壳默认水平，屏幕和相机单独固定上仰10°；IMU移到刚性托板底面；移除功能按钮与孔；主托板合并短侧板，整理对称轮廓；后壳加入接口小板一体安装耳。接口板电路由另一任务完成。[设计要求](../mechanical/INTERFACE_PCB_REQUIREMENTS.md)。

本轮机器人本体打印件{change['printed_parts_before']}→{change['printed_parts_after']}，主结构取消8组螺钉/螺母连接；新增原生板和接口板固定使用8枚试配螺钉及嵌件，整机数量变化见BOM。没有为了少分件取消必需的运动与维修分界。

正常装配宽×深×高约{'×'.join(f'{x:.1f}' for x in size)}mm；头部零位0°，切面Z={hz+p['head_lower_opening_z_from_center_mm']:.1f}mm水平。轮径105、轮宽18、球腹离地20mm，轮壳最小采样间隙{wm['minimum']['distance_mm']:.2f}mm。全头动作包围尺寸{[round(x,1) for x in motion['size_xyz_mm']]}mm，yaw±60°/10°步长、pitch−20…+25°/5°步长，共{motion['poses']}姿态；有限采样不是连续证明。±15°机身倾斜仍仅作几何测试。

IMU采用原生P2库CAD，器件向下。电池最小名义实体间距约{imu['battery_actual_solid_gap_mm']:.1f}mm。P2运动载板和WeAct已1:1摆入，排母6mm仍是假设；电源板80×55只是容量。P3正在另任务改动，未拿旧板冒充最终实物。接口板24×14是机械提案，两孔Ø2.2，顶面开关、底面USB-C都向后；真实器件未选择，不能按橙色包络下单或冻结外壳加工。

估重约{whole['mass_g_rounded']/1000:.2f}kg，估计质心{whole['center_mm_rounded']}mm，pitch运动件约{hp['mass_g_rounded']}g。详见mass_budget.json的材料/填充和附件质量，至少±35%不确定，未测平衡、扭矩或惯量。新增PCB库几何不等于整板实测质量。

实际检查{v['counts']}。Blender{bm['blender']} / Python{bm['python']} / Manifold{bm['manifold3d']}。重复生成{rebuild['status']}；最终输入、渲染与STL一致性{consistency['status']}。{ex['exported_count']}候选STL已回读检查毫米尺寸。

| 检查 | 状态 | 说明 |
|---|---|---|
{rows}

[装配与打印](../mechanical/reports/组装与打印.md)。已生成模型与候选件；完成的几何检查见表。采购选型/P3交接、局部试打、强度/热/音频/续航和实机自平衡仍未完成。完整精确实物干涉仍BLOCKED：LCD两个接插件使用保守代理，CAM镜头/FPC等未取得完整尺寸。没有掩盖这些边界。
'''
(PROJECT/'reports/mechanical_v1_2.md').write_text(report)
fontpath='/System/Library/Fonts/Helvetica.ttc';font=ImageFont.truetype(fontpath,24);smallfont=ImageFont.truetype(fontpath,14);sheets=[]
for target,folder,row_names,col_names,w in [('structure_comparison.jpg','structure',['whole','belly'],['before','after'],800),('appearance_comparison.jpg','appearance',['before','after'],['front','side','oblique'],600),('v1_2_shape_comparison.jpg','variants',['A','B'],['front','side','45'],480)]:
 sheet=Image.new('RGB',(len(col_names)*w,len(row_names)*(w+35)),'#edf0ed');draw=ImageDraw.Draw(sheet)
 for ri,r in enumerate(row_names):
  for ci,col in enumerate(col_names):
   filename=f'{col}_{r}.png' if folder=='structure' else f'{r}_{col}.png'
   with Image.open(ROOT/'renders'/folder/filename) as im:sheet.paste(im.convert('RGB').resize((w,w)),(ci*w,ri*(w+35)+35))
   label=f'{r} / {col}'
   if folder=='structure':label=(p['structure']['comparison_baseline']['revision'] if col=='before' else p['revision'])+' / '+r
   if folder=='appearance':label=(p['structure']['comparison_baseline']['revision'] if r=='before' else p['revision'])+' / '+col
   draw.text((ci*w+12,ri*(w+35)+4),label,fill='#24343d',font=font)
 sheet.save(ROOT/'renders'/target,quality=94);sheets.append('renders/'+target)
for page_no in range(math.ceil(len(parts)/20)):
 group=parts[page_no*20:(page_no+1)*20];sheet=Image.new('RGB',(1250,50+math.ceil(len(group)/5)*300),'#eeeeea');draw=ImageDraw.Draw(sheet);draw.text((20,10),p['revision']+f' | PARTS {page_no+1}',fill='#24343d',font=font)
 for i,part in enumerate(group):
  x=i%5*250;y=i//5*300+50
  with Image.open(ROOT/part['file']) as im:sheet.paste(im.convert('RGB').resize((245,245)),(x,y))
  draw.text((x+5,y+248),part['id'][:24],fill='#24343d',font=smallfont)
 path=f'renders/parts_sheet_{page_no+1:02}.jpg';sheet.save(ROOT/path,quality=92);sheets.append(path)
# Overview uses the exact same rendered geometry; no generated concept imagery.
grid=Image.new('RGB',(1600,1680),'#434950');draw=ImageDraw.Draw(grid)
for i,(n,label) in enumerate([('45_assembled','M1.11 / LEVEL HEAD'),('level_head_side','ONLY OPTICS TILT +10 DEG'),('imu_underside','IMU / UNDERSIDE OF FRAME'),('rear_interface_detail','REAR I/O / ONE SMALL PCB')]):
 x=i%2*800;y=i//2*840
 with Image.open(ROOT/f'renders/{n}.png') as im:grid.paste(im.convert('RGB').resize((800,800)),(x,y+40))
 draw.text((x+20,y+7),label,font=font,fill='#f3f7f8')
grid.save(ROOT/'renders/M1_11_overview.jpg',quality=94);sheets.append('renders/M1_11_overview.jpg')
(ROOT/'reports/presentation_manifest.json').write_text(json.dumps({'revision':p['revision'],'files':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sheets}},indent=2))
view_names={'45_assembled':'水平头壳 · 光学安装上仰10°','front':'前视','side':'侧视','rear':'后视 · 开关/USB上下排列','top':'顶视','bottom':'底视','level_head_side':'头部水平切面与倾斜光学安装','imu_underside':'IMU在一体托板底面','deck_plan':'对称托板轮廓 · 明确的功能开口','rear_interface_detail':'后接口板与壳体一体短安装耳','face_detail':'圆屏与相机独立开口','screen_outline_review':'直立屏幕叉架','internal':'内部布局','structure_only':'主要打印支撑','structure_exploded':'结构分界','head_section':'双轴剖面','speaker_shell_detail':'扬声器固定上壳','mic_detail':'板载麦克风示意','weact_detail':'原厂WeAct CAD','belly_detail':'PCB/电池区','yaw_drive_detail':'头内Yaw','exploded':'装配爆炸图','clearance':'离地与轮隙','pose_up':'联合仰头姿态','pose_down':'联合低头姿态','docked':'维护托架'}
def card(n):return f'<figure><a href="renders/{n}.png"><img loading="lazy" src="renders/{n}.png" alt="{esc(view_names.get(n,n))}"></a><figcaption>{esc(view_names.get(n,n))}</figcaption></figure>'
appearance=''.join(card(n) for n in ['45_assembled','level_head_side','front','side','rear','top','bottom','face_detail'])
structure_cards=''.join(card(n) for n in ['imu_underside','deck_plan','rear_interface_detail','internal','structure_only','structure_exploded','screen_outline_review','speaker_shell_detail','mic_detail','belly_detail','head_section','yaw_drive_detail','exploded','clearance','pose_up','pose_down','docked'])
partcards=''.join(f'<figure><a href="{esc(a["file"])}"><img loading="lazy" src="{esc(a["file"])}"></a><figcaption>{esc(a.get("label",a.get("name",a["id"])))}<br><small>{esc(a["id"])}</small></figcaption></figure>' for a in parts)
statusrows=''.join(f'<tr><td>{esc(a["id"])}</td><td class="{a["status"]}">{a["status"]}</td><td>{esc(a["summary"])}</td></tr>' for a in v['checks'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {p['revision']}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#11151a;color:#e3e8ed;font:16px/1.7 system-ui,sans-serif}}main{{max-width:1300px;margin:auto;padding:32px}}h1{{font-size:36px;margin:0}}h2{{margin-top:48px}}p{{max-width:1050px;color:#bfcbd4}}a{{color:#85dce8}}nav{{position:sticky;top:0;padding:12px;background:#11151af2;display:flex;gap:22px;flex-wrap:wrap;border-bottom:1px solid #33404c}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}}.parts{{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}}figure{{margin:0;background:#242b33;border-radius:12px;overflow:hidden}}img{{width:100%;display:block}}figcaption{{padding:12px}}small{{color:#a6b4bf}}.note{{padding:20px;background:#25333d;border-radius:12px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #33404c}}.PASS{{color:#8de0ae}}.FAIL{{color:#ff7777}}.BLOCKED,.NOT_TESTED{{color:#efbf7c}}.links{{display:flex;flex-wrap:wrap;gap:20px;margin:20px 0}}@media(max-width:600px){{main{{padding:18px}}}}
</style><main><h1>MORI <small>{p['revision']}</small></h1><p>水平头壳 · 单独倾斜屏幕/相机 · 底面IMU · 一体短侧板 · 共板双面后接口</p><nav><a href="#appearance">外观</a><a href="#structure">结构</a><a href="#interface">接口板要求</a><a href="#parts">全部零件</a><a href="#checks">检查</a></nav><div class="links"><a href="mori_v1_2.blend">Blender模型</a><a href="INTERFACE_PCB_REQUIREMENTS.md">交给PCB任务的设计要求</a><a href="../reports/mechanical_v1_2.md">完整报告</a><a href="reports/组装与打印.md">组装/打印</a><a href="reports/采购件选型.md">真实尺寸依据</a></div>
<div class="note">已实际重建、检查、渲染与导出。<b>{v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL</b>。其余未测/阻塞见下表。P2库几何是原生设计参考，P3仍待交接；橙色接口板/开关/USB是要求包络，没有把它们当成已选实物。</div>
<section id="appearance"><h2>水平默认头部</h2><p>头部零位0°、底部切面水平，主内部支架保持水平/垂直。圆屏有效区居头球正前中心，仅光学安装倾角+10°。LCD全总成刚性后移4mm，硬件尺寸不变。功能按钮及其孔已移除，保留物理电源/禁驱接口。</p><div class="grid">{appearance}</div></section>
<section id="structure"><h2>简单分件与安装空间</h2><p>IMU移到刚性托板底面；与电池名义实体间距约{imu['battery_actual_solid_gap_mm']:.1f}mm。主托板合并左右短板，删除独立电源托板；本体打印件{change['printed_parts_before']}→{change['printed_parts_after']}。取消8组主结构螺钉/螺母连接，新增PCB固定另需8枚试配螺钉及嵌件。相对运动与维修分界保留。</p><div class="grid">{structure_cards}</div></section>
<section id="interface"><h2>给接口板设计任务</h2><p><a href="INTERFACE_PCB_REQUIREMENTS.md">完整要求文件</a>：板框24×14×1.6，两孔Ø2.2。开关在PCB顶面，USB-C在底面，两者均侧向朝后。外壳两短耳一体成型，从拆下的上壳底面拧螺钉。开关/插口中心距11mm，型号选定后复核其轴高与开口；目前不是最终加工尺寸。</p><p>Motion基板70×35、IMU20×16尺寸未要求电气修改。电源80×55容量已放入本次模型，装件与最终固定方式待P3交接。<a href="reports/采购件选型.md">查看已有实物资料与未确认项</a>。</p></section>
<section id="parts"><h2>全部零件 · {len(parts)}项</h2><p><a href="reports/bom.csv">BOM</a> · <a href="reports/打印件审查.md">打印审查</a> · <a href="reports/export_manifest.json">{ex['exported_count']}件候选STL</a></p><div class="grid parts">{partcards}</div></section>
<section id="checks"><h2>验证记录</h2><p>Blender {bm['blender']}；重建{rebuild['status']}，输入/图片/STL一致性{consistency['status']}。130组头部离散姿态，未证明连续空间。估重约{whole['mass_g_rounded']/1000:.2f}kg，质量至少±35%不确定。尚未打印、装实物或验证平衡。</p><table>{statusrows}</table></section></main></html>'''
(ROOT/'index.html').write_text(page)
print('REPORT_COMPLETE',p['revision'])
