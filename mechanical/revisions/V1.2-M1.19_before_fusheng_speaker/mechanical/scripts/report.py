"""Current delivery, generated only from executed Blender evidence."""
from pathlib import Path
import json,html,math,hashlib
from module_report import printing_audit
from parts_classification import generate as manufacturing_view
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text());esc=html.escape
p=json.loads((PROJECT/'config/geometry.json').read_text());v=load('validation.json');mass=load('mass_budget.json');ex=load('export_manifest.json');bm=load('build_manifest.json');motion=load('head_motion.json');wm=load('wheel_clearance.json');parts=load('parts_preview_manifest.json');consistency=load('delivery_consistency.json');rebuild=load('rebuild_check.json');bom=load('bom.json');structure=load('structure_changes.json');change=load('layout_cleanup_changes.json');consolidation=load('part_consolidation.json');hardware=json.loads((PROJECT/'contracts/components.json').read_text())
checks={c['id']:c for c in v['checks']};whole=mass['totals']['whole_robot'];hp=mass['totals']['head_pitch'];size=checks['assembled_size']['measurement']['xyz_mm'];imu=checks['imu_underside_rigid_mount']['measurement']
consolidation['status']=checks['physical_part_consolidation']['status'] if consistency['status']=='PASS' and rebuild['status']=='PASS' else 'FAIL'
consolidation['physical_components']=checks['physical_part_consolidation']['measurement']['parts']
consolidation['validation_evidence']='validation.json#/checks/physical_part_consolidation; rebuild_check.json; delivery_consistency.json'
consolidation['source_geometry_sha256']=consistency['render_geometry_sha256']
consolidation['scope']='Connected physical solids and assembly inventory verified. Service, motion and optical checks reported separately; no manufacturing release.'
(ROOT/'reports/part_consolidation.json').write_text(json.dumps(consolidation,ensure_ascii=False,indent=2)+'\n')
# Historical construction stages remain reproducible, but are not a second
# statement of the final assembled inventory after consolidation.
for name in ['belly_relayout_geometry.json','detail_fit_geometry.json']:
 stage=load(name);stage['geometry_scope']='INTERMEDIATE_CONSTRUCTION_PHASE_BEFORE_M1_13_CONSOLIDATION';stage['final_geometry_source']='assembly_instances.json / bom.json / part_consolidation.json';(ROOT/'reports'/name).write_text(json.dumps(stage,ensure_ascii=False,indent=2)+'\n')
structure['geometry_status']='FAIL' if v['counts']['FAIL'] else 'BLOCKED';structure['validation_summary']=v['counts']
structure['remaining_service_parts']=['Display_Frame','Battery_Tray','Motor_Retainer','Yaw_Reaction_Link','Speaker_Mount']
structure['integrated_accessories']=[f'{a} -> {b}' for a,b in consolidation['integrations'].items()]
baseline_datums=json.loads((PROJECT/p['structure']['comparison_baseline']['derived']).read_text());current_datums=load('derived.json')
structure['head_joint_axes_unchanged']=all(abs(baseline_datums[k]-current_datums[k])<.001 for k in ['head_z','yaw_bearing_z','wheel_z'])
structure['limits']='M1.19 removes both microphone tubes and retains open shell/frame passages; recording performance remains untested. M1.18 widens tray between flat cheeks and provides actual bottom bearing; no extra parts/fasteners. M1.17 replaces long power rails with four low seats and two diagonal screws using P4 holes; populated P5 fit pending. M1.16 moves paired battery retention holes inward and checks closed edges; M1.15 mounting cleanup, M1.13 consolidation and M1.14 wheel interfaces retained. No hardware resizing. Populated PCB fit, camera/CAM dimensions, real connectors, print strength and dynamic balance remain unqualified.'
(ROOT/'reports/structure_changes.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2))
assembly_plan=load('module_assembly.json');assembly_plan['limits']='Trial M2 fastening and straight-shank access only, not actual threads or hands. P3 power populated fit and rear-interface components/final retention still pending.';(ROOT/'reports/module_assembly.json').write_text(json.dumps(assembly_plan,ensure_ascii=False,indent=2)+'\n')
hz=load('derived.json')['head_z'];c=hp['center_mm_rounded'];torque=[{'pitch_deg':a,'gravity_Nm':round(abs((c[1]*math.cos(math.radians(a))-(c[2]-hz)*math.sin(math.radians(a)))/1000*hp['mass_g_rounded']/1000*9.81),4)} for a in range(-20,26,5)]
(ROOT/'reports/head_load_estimate.json').write_text(json.dumps({'status':'ASSUMED','gravity_samples':torque,'sampled_max_Nm':round(max(x['gravity_Nm'] for x in torque),3),'inertia_kg_m2':hp['inertia_at_head_joint_kg_m2'][0][0],'dynamic_equation':'gravity+Ixx*alpha+cable/friction; continuous torque not qualified','mass_uncertainty_percent':35},indent=2))
selection=f'''# 当前部件尺寸依据 · {p['revision']}

没有执行采购，没有将原厂CAD、原生PCB设计或图纸名义尺寸标记为实物测量。硬件文件和 components.json 保持只读。

M1.16已只读核对硬件P4交接。下表中的P2/P3模型是当前模型采用的历史参考；P4完整装件并未替换入总装。P4后接口板已为24×25，和当前24×14占位不一致；PH接插件插合高度与线弯、开关/USB轴线也需重新适配。M1.17电源短座只采用P4板孔；P5正在改版，完整装件适配仍未通过，详见[P4接收记录](P4_receipt_review.json)。

| 部件 | 模型依据 | 尚待确认 |
|---|---|---|
| Waveshare LCD35079 | 原厂113实体STEP，1:1；有效显示Ø45.68 | 两个缺陷连接器使用保守代理，线缆及购买版本待核 |
| Waveshare CAM33700 | 板框37×37；两颗板载麦克风示意 | 完整装件CAD未取得，镜头/FPC/麦克风坐标仍是部分尺寸或照片估计 |
| WeAct V1.1 | 原厂224实体CAD，按P2基板插接方向刚性放置 | 6mm排母堆叠为假设；真实插座和P3版本需复核 |
| Motion基板 | 原生P2 70×35×1.6及49项库几何，四个原生孔位 | P3布线和板框交接已收到，装件/对插适配尚未完成；图中仍为P2参考 |
| IMU | 原生P2 20×16×1.6及8项库几何，原生两孔；器件朝下 | P3器件位置、配对插头和传感器到PCB轴向需复核 |
| 电源板 | 最大PCB80×55×1.6，正面装件+16/背面−3的容量 | 容量包络，孔位取P4原生交接；四个矮座、两个对角M2×6。P5改版中，局部元件禁布区和完整对插未验证 |
| 后接口小板 | 新24×14×1.6提案；顶面开关、底面USB-C、都朝后 | 精确器件与电路在另一任务设计；模型中的器件都是选型要求包络 |
| 扬声器 | Same Sky CMS-4017-34SP，厂图Ø40×17.5，±0.3，25g | 接在上壳，独立后盖；焊片/密封/音腔需实测 |
| 电池 | Tenergy31013 成品3S，名义71×55×20、150g | 导线出口、公差、NTC、均衡、充电方案和本地采购待核 |
| 轮驱 | S288尺寸图六孔；整体金属法兰轴与双扁轮毂设计；686ZZ图纸6×13×5 | 自攻螺钉具体型号、加工配合、中心螺钉凹位、线口与负载待样件验证；见S288轮驱连接与加工要求.md |
| 头部舵机 | SCS0009×2尺寸图 | 舵盘、轴承保持、线口和负载需实物验证 |

原厂来源文件/哈希在 contracts/mechanical_interfaces.json。原生P2来源和STEP哈希在 mechanical/studies/pcb_P2_fit/native_inventory.json。原模型三维尺寸没有为了适配而缩放。橙色表示资料未完整或待选型，不能据此下单或制造。

新增[电源P3独立装件参考与CAM资料核对](../studies/power_P3_detail/README.md)：85个三维库器件加PCB已实际导出Blender，14个器件缺CAD并明确列出。这份未替换总装电源容量包络，也未宣称P3完整装配通过。
'''
assembly=f'''# MORI {p['revision']} 组装与打印

头壳默认pitch=0°，底部切面水平，主承重支架沿水平/垂直方向布置。只有圆屏和相机的固定安装角上仰10°；圆脸外缘按头球半径推导，整套光学件绕球心上转10°，中心随球面自然上移约8.8mm；外缘接齐球面，不再有上沿深凹台。LCD保持原厂平面尺寸，未弯曲或缩放。相机仍有独立额头窗口。

M1.13合并将本体打印件26→20；M1.14删去两只打印转接毛坯，用两根一体金属法兰轴替代，M1.19再取消两根麦克风导管，当前本体候选打印件{consolidation['robot_print_after']}件。已保留的合并成果：取消两只独立轮盖，轮毂自身外侧改为白色面；相机遮光座与前壳连接；开口线导、Yaw转台和U托成为一件；固定遮缝环接入Yaw承重桥。转台原来的两组M2螺钉/螺母取消，补齐轮输出、共用底盖及端部保持后，当前已示意紧固件{consolidation['fasteners_after']}个，包含两枚平垫圈；M1.15取消外伸螺丝耳/工具槽，承重桥两枚螺母换成嵌件，该次五金总数不变。M1.17取消两条长电源托边，四个矮座并入原托板，新补两枚M2×6与两枚试配嵌件。电池托盘、轮驱底盖、屏幕叉架和扬声器后盖保留独立，便于安装和维修。麦克风采用无导管方案：保留两颗板载MIC、外壳声孔与头托开放孔，声音经头部空隙进入。没有增加胶圈或支架；实际声孔坐标、拾音、双麦串音及电机/扬声器噪声仍待样机确认。

保留M1.12主托板两侧整体收窄至104mm的轮廓，轮窝附近保留完整4mm平板；去掉上一版底面被轮窝削出的弧形缺口。左右对称，使用连续直边和倒角；前部圆弧让位扬声器，后部圆角开口让位USB/接口板。这两处是有明确用途的开口，不是轮胎随意裁切。四个原有壳体连接点保留。合并件也没有恢复包裹电池的大筒壁。

1. 台面上先从Load_Frame底面安装IMU，两枚M2试配螺钉；器件朝下，固定在刚性托板上。不要增加松软胶垫。PCB轴向变换见imu_mount_transform.json，传感器芯片坐标仍须由硬件/固件按P3方向核对。
2. 台面上用每侧六枚厂家匹配M2自攻螺钉连接整体金属法兰轴；再从轴尾套入内轴承、5mm隔套、外轴承，两套组件由下装入上座，四枚M3×25固定共用底盖。之后连接主托板；完整轮驱顺序见S288轮驱连接与加工要求.md。装载板和WeAct前，检查6mm排母候选是否真能配对。P2运动基板四孔原位固定，电源80×55仍是容量包络，按P4原生孔位落在四个一体矮座上，先预装两枚短嵌件，再由顶部拧两枚对角M2×6，之后才装Yaw承重桥。P5改版与完整装件/接插件仍待复核。
3. 在电池托盘装入前，先把承重桥放到主托板上，从主托板底面用两枚M2×8锁入桥脚盲孔嵌件；螺丝头收进板厚。再装电池托盘、软垫和束带。M1.18托盘外宽90→94.2mm，内通道保持81mm；与平侧板每侧留0.3mm试配间隙，删除局部过渡凸块。侧板统一3.6mm，侧向M2沉孔1.8mm深，孔后1.8mm材料；底部原台阶接到托盘，侧向螺钉只限制抽出。IMU实际三角实体到电池名义包络间距约{imu['battery_actual_solid_gap_mm']:.1f}mm；插头向下10mm的预留位于电池后侧。电池仍按报告的拆壳/卸轮、断线、沿+Y抽出顺序维护。
4. 台面上先将反力轴、舵盘和夹紧件穿入一体Yaw转台/U托，再把这组组件放入固定桥/轴承，安装反力轴横向保持螺钉，然后装倒置Yaw舵机和输出/中心锁紧，最后装pitch头组件。拆卸反向进行：移除pitch头和Yaw舵机后，松开反力轴横向保持，再把转台/U托与反力轴一起向上取出。运行时反力轴仍固定在身体，绝不随Yaw旋转。头前组件先在台面装LCD三后柱和相机，再通过四个可从侧面操作的螺钉接到直立头托。
5. 后接口小板安装在拆下的身体上壳内，位于两个一体短耳下方，从底面拧两枚螺钉。开关在上、Type-C在下，均朝后。小板的详细要求见../INTERFACE_PCB_REQUIREMENTS.md。没有独立打印接口架、Function_Button或外置RESET。
6. 麦克风无需安装打印导管，保持后壳声孔和头托开孔畅通。CAM板上双麦的位置及进声面需实板核对，先做安静环境、舵机动作和扬声器播放的录音对比，再确认拾音方案。喇叭保持固定在上壳，连续轮廓的独立后盖由两枚M2×20从背面沉孔压紧，无外伸耳；接好可断开的音频线和接口板线束，再合壳。不要悬挂着线束拆壳。

打印：外壳仍可用PLA/PETG做外观试样；承重材料/层向需载荷试验。一体托板可比较侧面落床与倒置打印，两个方向都有局部安装柱/短脚支撑需求，未运行切片器，不承诺免支撑。直立屏叉和轮驱底盖保留简单结构。一体Yaw/U托比较轴向竖放与侧放；一体遮缝环、相机座和线导需要局部支撑评估。轮毂改为双扁孔，12.2mm啮合，M3端螺钉与垫圈保持；先验证配合、回差、防松及塑料蠕变。轴承座试样12.9/13.0/13.1mm，双扁孔试样另列；金属轴与隔套不是打印件。相机座内部需要哑黑遮光涂层，独立窗口仍可维护。Yaw限位凸耳及固定挡块一起移到轴承上方，避免限位凸耳卡住轴承阻止拆装；准确触点角度、强度和冲击载荷仍待核。先试打嵌件、接口局部后壳、轴承及平缝小样，再决定整件。不会把0.3mm当作所有机器通用公差。

几何检查不包含螺纹真实啮合、打印强度、疲劳、手柄/手指、实际线束寿命、音频和热验证。托架使用必须禁轮驱；几何通过不代表断电自立或实机平衡通过。
'''
for n,t in [('采购件选型.md',selection),('purchased_dimensions.md',selection),('组装与打印.md',assembly),('结构简化说明.md',assembly),('设计与选型分工.md',selection),('外购与自制.md',selection+'\n打印件见bom.json和候选STL清单；轮胎、光学片、紧固件另列。\n'),('打印件审查.md',printing_audit(bom))]:(ROOT/'reports'/n).write_text(t)
rows='\n'.join(f"| {c['id']} | {c['status']} | {c['summary']} |" for c in v['checks'])
report=f'''# MORI {p['revision']} 机械交付

已实际运行build、validate、render、export及重复生成检查。本轮逐件巡检{consolidation['robot_print_after']}个本体打印件，去掉承重桥、喇叭后盖、轮驱底盖和反力轴夹口的外伸螺丝耳/长工具槽，采用底面或背面沉入式固定。无新增打印件，轮/板/光学位置不变。保留M1.14的S288输出至轮毂连接：整体金属法兰轴、双686ZZ轴承、双扁位轮毂、M3端部保持，以及共用可拆电机/轴承底盖。下壳轴孔向壳缝开放，壳缝安装位移至Y±54，轮窝局部壁厚改用双精度实体射线并交叉验证，拆卸不必先抽轮轴。M1.13的26→20件合并和M1.14的20→18件调整继续保留；M1.19取消两根麦克风导管，本体18→16件，五金数量不变。累计本体打印件26→{consolidation['robot_print_after']}，已示意紧固件78→{consolidation['fasteners_after']}（新增必要的六孔输出连接、四点底盖固定及端部保持，未减少五金）。轮盖由轮毂自身外观面替代；相机遮光座并入前壳；开口线导和Yaw转台并入U托；固定遮缝环并入Yaw承重桥。未以悬空网格拼组冒充连通实体。

维修分界保留：电池托盘、轮驱底盖、屏幕叉架、扬声器后盖及前后/上下外壳。新的头部维护顺序要求释放反力轴横向保持后，将反力轴随一体Yaw/U托取出；不是继续沿用旧版先拆U托底部螺钉的方式。CAD采购件保持1:1，轮心、轮径、光学安装及板卡位置保持原方案；M1.14轮轴和壳体维修接口保留，M1.15调整的是安装固定方式。圆脸接齐球面、104mm整边主托板和接口板一体壳耳延续M1.12。[接口板设计要求](../mechanical/INTERFACE_PCB_REQUIREMENTS.md)。

正常装配宽×深×高约{'×'.join(f'{x:.1f}' for x in size)}mm；头部零位0°，切面Z={hz+p['head_lower_opening_z_from_center_mm']:.1f}mm水平。轮径105、轮宽18、球腹离地20mm，轮壳最小采样间隙{wm['minimum']['distance_mm']:.2f}mm。全头动作包围尺寸{[round(x,1) for x in motion['size_xyz_mm']]}mm，yaw±60°/10°步长、pitch−20…+25°/5°步长，共{motion['poses']}姿态；有限采样不是连续证明。±15°机身倾斜仍仅作几何测试。

IMU采用原生P2库CAD，器件向下。电池最小名义实体间距约{imu['battery_actual_solid_gap_mm']:.1f}mm。P2运动载板和WeAct已1:1摆入，排母6mm仍是假设；电源板80×55只是容量。P3已另行生成85个库器件加PCB的详细参考，14器件仍缺CAD；该独立参考尚未替换总装电源容量包络，完整装件与对插空间未适配。当前P2参考没有改名冒充P3。接口板24×14是机械提案，两孔Ø2.2，顶面开关、底面USB-C都向后；真实器件未选择，不能按橙色包络下单或冻结外壳加工。

估重约{whole['mass_g_rounded']/1000:.2f}kg，估计质心{whole['center_mm_rounded']}mm，pitch运动件约{hp['mass_g_rounded']}g。详见mass_budget.json的材料/填充和附件质量，至少±35%不确定，未测平衡、扭矩或惯量。新增PCB库几何不等于整板实测质量。

实际检查{v['counts']}。Blender{bm['blender']} / Python{bm['python']} / Manifold{bm['manifold3d']}。重复生成{rebuild['status']}；最终输入、渲染与STL一致性{consistency['status']}。{ex['exported_count']}候选STL已回读检查毫米尺寸。

新增[一体Yaw限位复查](../mechanical/reports/integrated_stop_check.json)：沿两方向每1°检查，64°样本尚无正体积交集，65°样本在限位凸耳高度出现接触穿入；这只是离散几何挡止区间，正常工作角仍为±60°。不代表可运行到65°，也不验证公差、冲击和打印强度。

新增[S288轮驱连接设计](../mechanical/studies/s288_interface_review/README.md)：已经实际生成六孔输出连接、一体金属轴、双扁轮毂、轴承保持和可拆底盖。新增检查包含每5°整套转动件、每1mm下壳/底盖/电机组件拆出，以及螺钉装入路径。金属加工STEP与尺寸图位于mechanical/metal_design，属于设计参考；自攻牙型、配合、强度、预算与实物验证仍未放行。

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
for i,(n,label) in enumerate([('consolidated_yaw',p['revision']+' / ONE YAW U + JOURNAL + GUIDE'),('consolidated_camera','CAMERA COLLAR IN FRONT SHELL / CROP'),('consolidated_base','FIXED BRIDGE + SHADOW RIM'),('consolidated_wheel','WHITE HUB / NO SEPARATE CAP')]):
 x=i%2*800;y=i//2*840
 with Image.open(ROOT/f'renders/{n}.png') as im:grid.paste(im.convert('RGB').resize((800,800)),(x,y+40))
 draw.text((x+20,y+7),label,font=font,fill='#f3f7f8')
grid.save(ROOT/'renders/consolidated_overview.jpg',quality=94);sheets.append('renders/consolidated_overview.jpg')
(ROOT/'reports/presentation_manifest.json').write_text(json.dumps({'revision':p['revision'],'files':{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in sheets}},indent=2))
view_names={'consolidated_yaw':'转台、U托、开口线导一体 · 少2件+4紧固件','consolidated_camera':'前壳一体相机遮光座 · 实体局部剖切','consolidated_base':'固定承重桥与遮缝环一体','consolidated_wheel':'轮毂直接提供白色外观面 · 取消独立盖','rear_interface_section':'接口固定剖面 · 两枚螺钉从下往上锁入嵌件','frame_underside':'托板底面 · 完整4mm平板，无轮窝削切','face_surface_side':'圆脸接齐球面 · 实体侧视','45_assembled':'水平头壳 · 光学安装上仰10°','front':'前视','side':'侧视','rear':'后视 · 开关/USB上下排列','top':'顶视','bottom':'底视','level_head_side':'头部水平切面与倾斜光学安装','imu_underside':'IMU在一体托板底面','deck_plan':'对称托板轮廓 · 明确的功能开口','rear_interface_detail':'后接口板与壳体一体短安装耳','face_detail':'圆屏与相机独立开口','screen_outline_review':'直立屏幕叉架','internal':'内部布局','structure_only':'主要打印支撑','structure_exploded':'结构分界','head_section':'双轴剖面','speaker_shell_detail':'扬声器固定上壳','mic_detail':'CAM板载双麦 · 无打印导管','mic_open_path':'开放进声路径 · 实际模型透视','weact_detail':'原厂WeAct CAD','belly_detail':'PCB/电池区','yaw_drive_detail':'头内Yaw','exploded':'装配爆炸图','clearance':'离地与轮隙','pose_up':'联合仰头姿态','pose_down':'联合低头姿态','docked':'维护托架'}
def card(n):return f'<figure><a href="renders/{n}.png"><img loading="lazy" src="renders/{n}.png" alt="{esc(view_names.get(n,n))}"></a><figcaption>{esc(view_names.get(n,n))}</figcaption></figure>'
appearance=''.join(card(n) for n in ['45_assembled','face_surface_side','level_head_side','front','side','rear','top','bottom','face_detail'])
structure_cards=''.join(card(n) for n in ['consolidated_yaw','consolidated_camera','consolidated_base','consolidated_wheel','frame_underside','deck_plan','rear_interface_detail','rear_interface_section','imu_underside','internal','structure_only','structure_exploded','screen_outline_review','speaker_shell_detail','mic_detail','belly_detail','head_section','yaw_drive_detail','exploded','clearance','pose_up','pose_down','docked'])
parts_section=manufacturing_view(ROOT,p['revision'],bom,parts,ex)
from fastener_cleanup_report import generate as publish_fastener_cleanup
mounting_section=publish_fastener_cleanup(ROOT)
from animation_page import generate as publish_animation
animation_section=publish_animation(ROOT)
animation_nav='<a href="#animation">装配动画</a>' if animation_section else ''
presentation=load('presentation_manifest.json');presentation['files']['renders/fastener_cleanup_overview.jpg']=hashlib.sha256((ROOT/'renders/fastener_cleanup_overview.jpg').read_bytes()).hexdigest();(ROOT/'reports/presentation_manifest.json').write_text(json.dumps(presentation,indent=2))
statusrows=''.join(f'<tr><td>{esc(a["id"])}</td><td class="{a["status"]}">{a["status"]}</td><td>{esc(a["summary"])}</td></tr>' for a in v['checks'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {p['revision']}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#11151a;color:#e3e8ed;font:16px/1.7 system-ui,sans-serif}}main{{max-width:1300px;margin:auto;padding:32px}}h1{{font-size:36px;margin:0}}h2{{margin-top:48px}}p{{max-width:1050px;color:#bfcbd4}}a{{color:#85dce8}}nav{{position:sticky;top:0;padding:12px;background:#11151af2;display:flex;gap:22px;flex-wrap:wrap;border-bottom:1px solid #33404c}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}}.parts{{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}}figure{{margin:0;background:#242b33;border-radius:12px;overflow:hidden}}img{{width:100%;display:block}}figcaption{{padding:12px}}small{{color:#a6b4bf}}.note{{padding:20px;background:#25333d;border-radius:12px}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #33404c}}.PASS{{color:#8de0ae}}.FAIL{{color:#ff7777}}.BLOCKED,.NOT_TESTED{{color:#efbf7c}}.links{{display:flex;flex-wrap:wrap;gap:20px;margin:20px 0}}@media(max-width:600px){{main{{padding:18px}}}}
details{{padding:16px 0;border-bottom:1px solid #33404c}}summary{{cursor:pointer;color:#85dce8;font-weight:600}}details[open] summary{{margin-bottom:16px}}h4{{margin:28px 0 12px;font-size:18px}}
</style><main><h1>MORI <small>{p['revision']}</small></h1><p>取消麦克风导管 · 本体打印件 {consolidation['robot_print_after']} 件 · 当前五金 {consolidation['fasteners_after']} 件</p><nav>{animation_nav}<a href="#microphones">麦克风</a><a href="#mounting">安装优化</a><a href="#wheel-interface">轮驱连接</a><a href="#appearance">外观</a><a href="#structure">结构</a><a href="#interface">接口板要求</a><a href="#parts">打印件/紧固件</a><a href="#checks">检查</a></nav><div class="links"><a href="mori_v1_2.blend">Blender模型</a><a href="INTERFACE_PCB_REQUIREMENTS.md">交给PCB任务的设计要求</a><a href="../reports/mechanical_v1_2.md">完整报告</a><a href="reports/组装与打印.md">组装/打印</a><a href="reports/采购件选型.md">真实尺寸依据</a></div>
<div class="note">已实际重建、检查、渲染与导出。<b>{v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL</b>。其余未测/阻塞见下表。P2库几何是原生设计参考，P3完整装件与插头适配尚未完成；橙色接口板/开关/USB是要求包络，没有把它们当成已选实物。</div>
{animation_section}
<section id="microphones"><h2>取消麦克风导管</h2><p>M1.19删除两根独立打印导管，本体打印件18→16，五金仍为98件。保留微雪CAM板载双麦、后壳声孔和头托的开放孔，不增加支架或胶圈。模型中的开放路径已做实体检查；实际MIC进声面与坐标仍是照片估计，头腔并无双麦声学隔离，拾音、串音和扬声器/舵机噪声需要样机录音。<a href="reports/microphone_open_path.json">查看几何依据与未测项</a>。</p><div class="grid">{card('mic_open_path')}{card('mic_detail')}</div></section>
{mounting_section}
<section id="appearance"><h2>水平默认头部</h2><p>头部零位0°、底部切面水平，主内部支架保持水平/垂直。圆脸外缘沿径向接齐头球面，光学安装倾角+10°，屏幕中心由几何推导自然上移约8.8mm。原厂平面LCD保持1:1，头壳底面及主结构仍水平。功能按钮及其孔已移除，保留物理电源/禁驱接口。</p><div class="grid">{appearance}</div></section>
<section id="structure"><h2>简单分件与安装空间</h2><p>IMU移到刚性托板底面；与电池名义实体间距约{imu['battery_actual_solid_gap_mm']:.1f}mm。主托板左右整边由110mm收窄至104mm，轮窝附近底面保留完整4mm厚度，实际轮胎间隙8mm。前面喇叭圆弧和后面接口缺口保留。本体打印件26→{consolidation['robot_print_after']}，紧固件78→{consolidation['fasteners_after']}。下图展示当前连通的合并件；相对运动、光学保护片以及电池/喇叭维修分界保留。转台/U托改为与释放后的反力轴一起取出，详见组装说明。</p><div class="grid">{structure_cards}</div></section>
<section id="interface"><h2>给接口板设计任务</h2><p><a href="INTERFACE_PCB_REQUIREMENTS.md">完整要求文件</a>：板框24×14×1.6，两孔Ø2.2。开关在PCB顶面，USB-C在底面，两者均侧向朝后。外壳两短耳一体成型，从拆下的上壳底面拧螺钉。开关/插口中心距11mm，型号选定后复核其轴高与开口；目前不是最终加工尺寸。</p><p>Motion基板70×35、IMU20×16尺寸未要求电气修改。电源80×55容量已放入本次模型，装件与最终固定方式仍待复核。<a href="reports/采购件选型.md">查看已有实物资料与未确认项</a>。</p><p><a href="studies/power_P3_detail/index.html">新增：电源P3详细Blender参考与CAM资料核对</a>。85个器件库模型已导出；14个器件CAD缺失。独立参考尚未替换总装包络。</p></section>
<section id="wheel-interface"><h2>S288 到轮毂：完整候选连接</h2><p>六孔原厂兼容自攻螺钉连接整体金属法兰轴，两只686ZZ支撑，双扁位轮毂用M3端部螺钉保持。上轴承座并入Drive_Bridge，下轴承座并入共用底盖；没有新增单独轴承小盖。下壳有隐藏的开放轴槽，可在卸轮毂后向下取出。</p><p><a href="studies/s288_interface_review/index.html?revision={p['revision']}">查看轴向剖面、拆装与详细数据</a> · <a href="reports/S288轮驱连接与加工要求.md">连接与加工要求</a> · <a href="metal_design/Wheel_Axle_Common_DESIGN_REFERENCE.step">整体金属轴STEP参考</a></p><div class="grid"><figure><a href="studies/s288_interface_review/axial_section.png"><img src="studies/s288_interface_review/axial_section.png"></a><figcaption>实际总装剖切：输出盘→金属轴→轴承→双扁轮毂→端螺钉</figcaption></figure><figure><a href="studies/s288_interface_review/split_seat.png"><img src="studies/s288_interface_review/split_seat.png"></a><figcaption>上座与共用底盖；展示偏移不进入STL</figcaption></figure></div><p>已运行几何与拆装检查。金属轴需要按图加工，螺钉须匹配厂家牙型；未实物试配、打印、载荷验证或核准≤1000元预算。</p></section>
{parts_section}
<section id="checks"><h2>验证记录</h2><p>Blender {bm['blender']}；重建{rebuild['status']}，输入/图片/STL一致性{consistency['status']}。130组头部离散姿态，未证明连续空间。估重约{whole['mass_g_rounded']/1000:.2f}kg，质量至少±35%不确定。尚未打印、装实物或验证平衡。</p><table>{statusrows}</table></section></main></html>'''
(ROOT/'index.html').write_text(page)
from wheel_interface_report import generate as publish_wheel_design
publish_wheel_design(ROOT)
print('REPORT_COMPLETE',p['revision'])
