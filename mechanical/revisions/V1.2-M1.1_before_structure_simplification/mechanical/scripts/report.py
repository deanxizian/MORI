"""V1.2 report/gallery from executed Blender evidence. No synthetic render or guessed PASS."""
from pathlib import Path
import json,html,math,datetime
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text())
esc=html.escape
p=json.loads((PROJECT/'config/geometry.json').read_text());v=load('validation.json');mass=load('mass_budget.json');ex=load('export_manifest.json');bm=load('build_manifest.json');motion=load('head_motion.json');wm=load('wheel_clearance.json');pose=load('body_head_envelope.json');comparison=load('parameter_comparison.json');parts=load('parts_preview_manifest.json');consistency=load('delivery_consistency.json');rebuild=load('rebuild_check.json');instances=load('assembly_instances.json')
checks={x['id']:x for x in v['checks']};size=checks['assembled_size']['measurement']['xyz_mm'];bbox=checks['assembled_size']['measurement']['bounds_xyz_mm'];hp=mass['totals']['head_pitch'];whole=mass['totals']['whole_robot'];c=hp['center_mm_rounded'];hz=json.loads((ROOT/'reports/derived.json').read_text())['head_z']
torque=[{'pitch_deg':a,'gravity_Nm':round(abs((c[1]*math.cos(math.radians(a))-(c[2]-hz)*math.sin(math.radians(a)))/1000*hp['mass_g_rounded']/1000*9.81),4)} for a in range(-20,26,5)]
(ROOT/'reports/head_load_estimate.json').write_text(json.dumps({'status':'ASSUMED','gravity_samples':torque,'sampled_max_Nm':round(max(x['gravity_Nm'] for x in torque),3),'inertia_kg_m2':hp['inertia_at_head_joint_kg_m2'][0][0],'dynamic_equation':'tau = gravity + Ixx*alpha + cable/friction; alpha and cable/friction must be measured, not inferred from stall torque','mass_uncertainty_percent':35},indent=2))
links={'S288':'https://www.unitree.com/download/DigitalServo/','SCS0009':'https://www.feetech.cn/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf','CAM33700':'https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx','LCD35079':'https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm'}
limits='LCD35079已按原厂113实体STEP以1:1导入；CAM33700板框已改为原厂37×37mm，12mm厚度仍仅为预留。电池80×65×30mm、STM32载板70×35×12mm、电源44×16×10mm及其他未选型件均为占位。橙色代表缺尺寸或待选型；原厂资料核对不等于已拿到实物测量。'
assembly='''# V1.2 装配、维护和候选打印

这些是M1/M2预研装配顺序；舵盘、实际板孔和完整工具手柄路径尚未冻结。先用限制包络/纸板/试样确认，再做整套打印。

1. 同材料、喷嘴、层高打印嵌件阶梯孔、平面间隙和配合片。记录实际插入力、尺寸和方向，不通用套用0.3mm间隙。
2. 检查独立4mm轮轴和两侧双轴承的真实规格、配合、挡圈/锁紧；轴承载荷经框架传递。装S288鞍座，确认原厂输出连接和自攻螺钉深度后才能制作转接盘。S288图中的Ø10.5孔圈和6个Ø1.7自攻底孔有资料，但孔位相位、螺钉啮合和买到的版本仍待核；当前Wheel_Coupler仅是待开孔毛坯，不能套用J288的4螺纹孔+2销孔。
3. 在框架上组电池托架、身体IMU、STM32后侧板架、电源板架和USB模块。线束分开动力/信号，避开轮胎，留插头拔出与束带空间。电池不压迫软包，±4mm调位需要实际托架槽方案复核。
4. 组独立扬声器后腔，检查孔阵列与分件线、密封垫和出音通道；头上板载麦克风走单独短声道。声道端点必须等待CAM板实际麦克风位置确认。
5. 装yaw承重轴承、SCS0009、空心转盘与双侧pitch支架；再装pitch轴承/短轴、舵盘及限位。不要把头重量交给单根舵机细轴。
6. 头内先试配CAM板框，再装LCD原厂总成与按三根M2柱位置重做的后支架；支架Ø2.4是试打间隙，螺钉长度/啮合深度未冻结。装相机和短FPC、平面黑面罩及两个独立透光区。QSPI与DVP同属pitch组；跨关节只走电源、通信与扬声器线。两轴服务环、应力释放和8mm最小弯曲半径均为待实测起点。
7. 接合头前后壳及身体上下壳，在无动力/外部支撑下手动检查全行程、每个插头和线束。紧固件/热熔工具全部可达性仍NOT_TESTED，不能仅凭这一步说明宣称装配合格。
8. 电池维护：在托架/可靠外部支撑下DISARM并断电，取轮盖/车轮，按最终锁紧设计释放并抽出轮轴，再拆上下壳，断开电池插头并释放四吊杆。电池+托架沿+Y取出120mm。此路径已按41个刚体采样检查；前序轮轴/壳体拆卸和插头操作仍需真实硬件验证。它不是无需拆轮的快换设计。
9. 充电、刷机、关机和维护用外置托架，车轮离地8mm且禁驱。没有托架传感器，必须人工确认支撑；不能用托架稳定推断双轮断电自立。

## 打印与材料

- 外壳建议PLA外观样件或PETG候选；2.4mm是当前建模起点，局部孔壁与全部最小壁厚仍需切片、卡尺和破坏样件验证。
- 框架、轴承座、舵机座可用PETG/PA候选；方向、蠕变、冲击和温升未验证。不能把PLA示意支架当成载荷认证。
- 轮胎独立外购橡胶或经试验的软TPU。当前95×18是要求，不是已选现货规格；硬PLA不作为抓地轮胎。
- 面罩优先1mm平面黑片，显示与镜头透光片是独立平片。exports/templates/face_mask_1to1.svg为同尺寸切片参考，检查20mm校准线；光学反射/透过率需实测。
- STL只包含候选打印件/试样，保留装配坐标，逐件落到切片平台后选方向。禁止用爆炸坐标生产。不含PCB、电池、轴承、整电机和轮胎。
- 全局壁厚、精确全三角自交、打印机误差、热熔孔和紧固强度未通过实际试打。候选STL通过拓扑和单位回读也不等于可直接整机生产。
'''
(ROOT/'reports/组装与打印.md').write_text(assembly)
procurement='''# V1.2 外购与自制划分

| 类型 | 零件 | 当前边界 |
|---|---|---|
| 指定型号外购 | S288×2、SCS0009×2、CAM33700、LCD35079 | LCD导入原厂完整CAD；CAM板框核实、装件厚度待核；两种舵机是尺寸图简化模型。未下单、未实测 |
| 通用外购待选 | 4Ω3W扬声器、成品3S电池、轴承/短轴/紧固件/嵌件、线束、按钮和开关、USB-C3S充电与保护稳压模块 | 所列包络不证明存在适配现货；型号、尺寸、价格、完整电气方案均需硬件任务 |
| 独立软材料 | 95×18软轮胎、托架垫、声学密封垫 | 采购橡胶或试验TPU；不混入硬壳STL |
| 自己打印候选 | 头身分壳、框架、轮毂/轮盖、板架、电池架、yaw/pitch支撑、相机/屏幕框、声腔、接口帽、停放托架 | 模型和候选STL已生成；未知孔位不冻结，需试样/承载验证 |
| 平片加工 | 黑面罩、屏幕保护片、相机透光窗 | 优先手工/激光切片；不要求曲面玻璃 |

CAM板载双麦/ES7210/ES8311/NS4150B复用，不重复买独立麦克风、Codec和功放。S288内部集成驱动，不额外加入FOC电调。CAN板也不是默认新增项。

预算仍≤1000元。当前没有完整国内到手报价及所需配件清单，采购/PCB冻结BLOCKED；机械建模进度不代表预算或续航已满足。CAM板3.7V充电输入不能接3S电池。
'''
(ROOT/'reports/外购与自制.md').write_text(procurement)
# Evidence table is derived from the interface source, not another editable BOM.
interfaces=json.loads((PROJECT/'contracts/mechanical_interfaces.json').read_text())
audit=load('purchased_geometry_audit.json'); lcd=interfaces['components']['display']['vendor_dimensions']; cam=interfaces['components']['cam_board']['vendor_dimensions']
dimension_report=f'''# 采购件尺寸依据与缺项 — {p['revision']}

按用户授权核对V1.2指定型号，尚无订单/实物测量。此表由机械接口与本次审计生成，改尺寸请编辑共享输入；不要另行把这张表当成采购BOM真值。

| 零件 | 已有尺寸依据 | 尚未验证 |
|---|---|---|
| LCD35079 | 原厂113实体STEP、1:1；玻璃Ø{lcd['glass_outer_diameter_mm']}、有效区Ø{lcd['active_diameter_mm']}、视窗Ø{lcd['view_diameter_mm']}mm；CAD深{lcd['cad_total_depth_mm']:.2f}mm | PDF参考{lcd['drawing_reference_total_depth_mm']}mm与CAD不同；两连接器转网格缺陷；买到版本、对插线束、最终M2安装 |
| CAM33700 | 板框{cam['board_width_mm']}×{cam['board_height_mm']}mm；孔中心距{cam['mount_center_pitch_mm'][0]}×{cam['mount_center_pitch_mm'][1]}mm；外角R{cam['corner_radius_mm']} | 孔径、板厚、装件总高、精确接口/双麦/天线、镜头与FPC；模型Y12mm只是橙色预留 |
| S288×2 | 原厂图本体20×34×20mm、两端输出总外廓26mm、输出Ø14；简化实体 | 完整连接器/线缆、转接盘与自攻螺钉、买到版本、承载 |
| SCS0009×2 | 图纸本体23.3×12.1×25.25mm、耳外廓32.5mm、含输出深28.45mm；简化实体 | 图纸/表格23.3/23.2差异、线缆和完整舵盘/螺钉 |
| STM32运动板、IMU模块 | 只确定芯片/系列；当前实体是可用空间 | 具体板型、含排针/插头全尺寸、安装孔、天线与热空间 |
| 电池、充电/保护/稳压、喇叭、接口、线束、轴承、轮胎等 | 仅预研包络/需求 | 具体商品及版本；不能按占位尺寸下单或加工 |

来源文件、哈希和版本见contracts/mechanical_interfaces.json的vendor_geometry_sources。原厂尺寸图与完整CAD均附在本项目sources下。源文件与比例核验：**{audit['integrity_status']}**；所有采购件完整真实建模：**{audit['all_purchased_parts_complete']}**。所有采购件measured_unit=false。

原厂CAD源实体有效，不意味着三角转换没有缺陷。两个连接器在检查中用保守包络，其余111件用实体网格；完整原厂网格保留用于编辑与渲染。静态/联合检查的具体结果见validation.json，不能从没有干涉推导实际线束、所有螺钉和公差均合格。

橙色零件属于占位或仅部分尺寸已知。CAD有来源的器件保持原比例；修改打印件或安装位置适配器件。下一步需确定未选商品并补齐原厂尺寸/实测，再冻结孔位、打印试样、实机验证。交接见reports/decisions/ADR-MECH-013-purchased-dimensions.md。
'''
(ROOT/'reports/purchased_dimensions.md').write_text(dimension_report)
ct='\n'.join(f"| {x['id']} | {x['status']} | {x['summary']} |" for x in v['checks'])
report=f'''# MORI V1.2 机械交付与证据

生成日期：{datetime.date.today()}。依据用户提供的MORI_SPEC_V1_2.md和01_CODEX_MECHANICAL.md。未提供/未找到模板、REFERENCES、交接清单和种子文件；没有声称读过或合并这些缺失文件。AGENTS保留不冲突规则并更新V1.2优先级。

## 完成范围

- M1已完成：实际Blender参数化双方案、同相机前/侧/45°对比，选择B主线、初步内部包络与缺失清单。
- M2部分完成：4执行器链、独立承重轴承/短轴、CAM在头内、分运动组、相机外参、联合姿态、质量/惯量预估。LCD原厂CAD和CAM板框已回写，剩余器件/高度/线缆/最终孔位与完整装拆仍BLOCKED；不能称为已适配生产结构。
- M3候选文件已生成：{ex['exported_count']}件STL、平片模板、逐件预览、装配/试打说明。待打印和实机平衡验证；未进行采购、PCB放行或上电测试。

## 实际尺寸与造型

正常宽×深×高 **{size[0]:.1f}×{size[1]:.1f}×{size[2]:.1f}mm**，头名义120、身160、胎95×18、腹部25mm。身体底部由声明曲面的实际局部最低点−80mm推得球心Z105mm；轮轴Z47.5mm。身体顶部Z177，头中心Z227，正常高287，均由共享参数推导。

B仅作4.5%随高度变化的肩腹修形、Y深度减1.5%；保留母球和原始基准，没有把真实硬件缩放进壳。A接近双球；B保留圆肩、略收腹。两套内部器件、相机、屏幕、轮比和渲染相机相同。容积比较见mechanical/reports/parameter_comparison.json；容积不是可装入矩形板的证明。分件、COM和内部干涉按最终B另检。

轮壳实际最小采样间隙 **{wm['minimum']['distance_mm']:.2f}mm**（两轮各37姿态、10°步进，轮胎/毂/盖对实际壳网格）。腹部保留曲面，轮胎最低Z0。两轮轴线同轴。身体±15°检查仅几何意义。

130组头部联合姿态（yaw−60…60每10°，pitch−20…25每5°），包络宽深高 **{'×'.join(f'{n:.1f}' for n in motion['size_xyz_mm'])}mm**；全姿态最高点 {motion['bounds_xyz_mm'][2][1]:.1f}mm。叠加身体±15°的4030组包络 **{'×'.join(f'{n:.1f}' for n in pose['size_xyz_mm'])}mm**，最高点 {pose['bbox_xyz_mm'][2][1]:.1f}mm。离散采样不是连续空间、回差或变形保证。

## 原厂资料、假设和接口

- [S288原厂手册]({links['S288']})第2页已下载并检查：20×34投影、本体轴向20、两端输出总外廓26、输出中心距端9.5、孔间距30×16、Ø1.7深度最多3的自攻孔。模型保留本体、两端输出、待定转接盘与独立双轴承；没有假定舵机轴径向承载合格。
- [SCS0009规格书]({links['SCS0009']})2020 A/0第4/6页：表格23.2、图纸23.3存在差异；模型按23.3、12.1、25.25和安装耳/20T输出预研。13.2±1g是该文件数据。购买版本、耳孔、舵盘和锁紧仍需确认。
- [CAM33700原厂产品与尺寸图](https://www.waveshare.com/esp32-s3-cam-ov5640.htm?sku=33700)：板框37×37mm、孔中心距32.6×32.6mm、边距2.2mm、外角R2.25。R2.25不是孔半径；孔径、PCB厚度与含元件总高未标。当前37×12×37mm中的12仅为橙色预留厚度。照片确认USB在板底边，已移除旧版假定的后向实体插头；精确插口坐标、麦克风、天线和原装FPC仍缺尺寸。H/V57°/44°仅用于光学预研，真实镜头待标定。
- [LCD35079原厂CAD与图纸](https://github.com/waveshareteam/1.85inch-Touch-LCD-Module/tree/main/dimensions)：113实体STEP REV1、2026-07-02、毫米、刚性1:1转换，包含圆形玻璃、背板、已装连接器和三根固定柱。玻璃外径55、有效区45.68、视窗46.08、玻璃厚0.7、PCB厚1.6mm。STEP整套深度9.35mm，PDF标9.1参考值；固定柱坐标也有约0.06mm差异，保留两份证据而不擅自统一。M2最终孔/螺钉待购买版本确认。完整原厂轮廓替代旧55×55假设矩形，因此旧版“必须增大头径才能装入”条件推论已撤销。
- 屏幕整件上移0.8mm，相机及独立透光孔上移3mm，按三柱位置重做打印后支架；未缩放采购件。黑面罩直径68mm不等于屏幕有效区，双眼只在45.68mm有效圆内。
- STEP的113实体在源CAD中均通过BRep检查；其中两个连接器子实体转三角网格后仍非流形。渲染保留所有原厂三角面，碰撞检查对这两件采用源CAD保守外接框，其他111件采用实体网格。即使零碰撞，完整精确装配检查也为BLOCKED；未以替代框伪造全实体PASS。详见vendor_lcd_import.json、mesh_topology.json。原始STEP、DXF、PDF、尺寸图与哈希保存在mechanical/sources/v1_2_verified_dimensions/。

{limits}

contracts/components.json由硬件拥有，V1.2-H0.1已只读核对且哈希未变。新尺寸事实和待回写字段在ADR-MECH-013-purchased-dimensions.md交接，未擅改硬件契约。机械接口仅记录原厂字段、设计限制和待确认项；旧H0.3、A4屏幕/电机数据已保存在mechanical/revisions/V1-A4_before_V1_2，不再作为当前装机真值。当前没有重复独立音频板或额外FOC占位。

完整固定/旋转对象与坐标在assembly_instances.json；相机变换在camera_kinematics.json：T_body_axle_camera=T(head_center) Rz(yaw) Rx(pitch) T(pupil) R_CV。CV光轴+Y，图像右+X，下−Z；角度需带时间，反馈/标定尚未实测。

## 质量、负载与维护

整机约 **{whole['mass_g_rounded']/1000:.2f}kg**，pitch活动件约 **{hp['mass_g_rounded']}g**，yaw连同头部约 **{mass['totals']['head_yaw_total']['mass_g_rounded']}g**。pitch COM在装配坐标约 {hp['center_mm_rounded']}mm，Ixx约 {hp['inertia_at_head_joint_kg_m2'][0][0]:.2g}kg·m²。按当前COM的pitch采样重力矩最大约 {max(t['gravity_Nm'] for t in torque):.3f}N·m；另需Iα、线缆阻力和摩擦，不能拿堵转扭矩当连续可用能力。

质量按网格体积、PLA1.24g/cm³、外壳有效98%/支架65%与独立附件假设计算；电池190g、CAM板18g等未测，至少±35%不确定度。估算表与完整惯量矩阵见mass_budget.json，不是空壳重量或实测。

电池向下取出会被轮驱挡住；最终路径为释放外壳/吊杆后+Y120mm、41姿态验证。前序需卸车轮/抽轮轴以释放下壳，完整工具和插头步骤未认证。此版维护代价明确保留，不宣称快换。IMU固定框架，主板后置，电池中部；未用“越低越好”代替平衡控制评估。

外置托架把车轮抬离地8mm，驱动必须DISARM。实际垫/身体接触和假设COM投影已检查；摩擦、线拉力、真实重心和软垫仍待实测。无运行第三支点，不证明断电自立。

## 实际运行与检查

Blender {bm['blender']}（{bm['blender_hash']}）、Python {bm['python']}、Manifold{bm['manifold3d']}。实际命令、时间和返回码在mechanical/reports/commands.json，各脚本日志同目录。build/validate/render/export、重复生成、4030姿态包络、A/B渲染、逐件图册均实际执行。

计数：{v['counts']}。重复生成：{rebuild['status']}；最终模型/渲染/STL/输入哈希一致性：{consistency['status']}。STL全部通过边关联、绕序、正体积、退化检查及Blender实际重新导入，mm单位误差<0.01。打印件不含采购硬件；生成式图片未参与交付。

| 检查 | 结果 | 范围 |
|---|---|---|
{ct}

AABB用于初筛；刚性/联合干涉主要采用闭合三角网格实体交集，但LCD的两个接插件明确采用保守AABB实体代理，完整精确CAD检查仍BLOCKED。轮壳采用实体最小距离；有意接触不能豁免体积穿透。线束只是保守管状/环状预留，未模拟柔性、疲劳及拉力。壁厚为指定面成对射线抽查，不等同全局最小壁厚；精确全自交算法未执行。

## 交接与停止边界

1. 硬件任务继续补全components.json：CAM装件高度/孔径/声口/FPC、LCD购买版本/图纸差异/对插线束、SCS版本/附件、S288输出连接/径向允许值、3S电池与全部电源模块、扬声器和接插件。
2. 当前STM32后架只能容纳70×35，不能默认70×50矩形板一定装入；电源架44×16×10。选型超过限制需调整机械布局，并重跑检查，禁止缩放真实板。
3. 软件无需本次更改角度范围；接收相机外参与质量预算后再更新仿真，不把默认角度当实测反馈。电气/软件契约未擅改。
4. 预算≤1000元和60分钟混合工况续航均未验证。预算缺价/超支暂停采购批准与PCB冻结；继续结构预研。
5. 下一阶段：实物尺寸回写、打印接口小样、逐个紧固件/插头装拆、热/结构/音频/射频验证，再在可靠保护条件下进行台架和实机平衡。
'''
(PROJECT/'reports').mkdir(exist_ok=True);(PROJECT/'reports/mechanical_v1_2.md').write_text(report)
(ROOT/'reports/阶段A检查报告.md').write_text('# 已迁移至 V1.2\n\n当前权威机械报告为项目 reports/mechanical_v1_2.md；此路径仅保留兼容。A4原文在 revisions/V1-A4_before_V1_2/mechanical/reports/。\n')
# Contact sheets consist only of actual Blender renders; labels/compositing do not change geometry.
try:
 from PIL import Image,ImageDraw,ImageFont
 font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',24)
 sheet=Image.new('RGB',(1440,1050),'#f1f1ee');draw=ImageDraw.Draw(sheet)
 for row,var in enumerate(['A','B']):
  for col,view in enumerate(['front','side','45']):
   im=Image.open(ROOT/f'renders/variants/{var}_{view}.png').convert('RGB');im.thumbnail((470,470));sheet.paste(im,(col*480,row*520+35));draw.text((col*480+16,row*520+7),f'{var} | {view.upper()}'+(' | SELECTED' if var=='B' else ''),fill='#233333',font=font)
 sheet.save(ROOT/'renders/v1_2_shape_comparison.jpg',quality=93)
 for page in range((len(parts)+19)//20):
  group=parts[page*20:(page+1)*20];canvas=Image.new('RGB',(1250,6*280),'#eeeeea');dr=ImageDraw.Draw(canvas)
  dr.text((20,12),f'MORI V1.2 | PARTS {page+1}',fill='#16272d',font=font)
  for i,it in enumerate(group):
   im=Image.open(ROOT/it['file']).convert('RGB');im.thumbnail((245,245));x=(i%5)*250;y=(i//5)*330+50;canvas.paste(im,(x,y));dr.text((x+8,y+249),it['id'][:22],fill='#16272d',font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',15))
  canvas=canvas.crop((0,0,1250,50+math.ceil(len(group)/5)*330));canvas.save(ROOT/f'renders/parts_sheet_{page+1:02}.jpg',quality=91)
except ImportError:pass
viewlabels={'front':'正视','side':'侧视','rear':'后视','top':'顶视','bottom':'底视','exploded':'爆炸图','head_section':'双轴头部剖视','screen_outline_review':'原厂圆屏 CAD 背面 / 三柱安装架','internal':'内部布局','clearance':'高度 / 腹部离地','wheel_gap_detail':'轮壳间隙','pose_up':'yaw+60° / pitch+25°','pose_down':'yaw−60° / pitch−20°','docked':'维护禁驱托架'}
cards=''.join(f'<figure><img loading="lazy" src="renders/{n}.png" alt="{label}"><figcaption>{label}</figcaption></figure>' for n,label in viewlabels.items())
export_by={it['id']:it['file'] for it in ex['parts'] if it['status']=='PASS'}
stl_link=lambda it: ('<a href="'+esc(export_by[it['id']])+'">候选 STL</a>') if it['id'] in export_by else ''
partcards=''.join(f'<figure class="part" data-search="{esc(it["id"]+it["name"]+it["category"])}"><img loading="lazy" src="{it["file"]}" alt="{esc(it["name"])}"><figcaption><b>{esc(it["name"])}</b><small>{it["id"]}<br>{it["category"]} · {it["status"]}<br>{it.get("model_fidelity", "DESIGN_GEOMETRY")}<br>{" × ".join(str(x) for x in it["dimensions_mm"])} mm</small>{stl_link(it)}</figcaption></figure>' for it in parts)
rows=''.join(f'<tr><td>{esc(x["summary"])}</td><td class="{x["status"]}">{x["status"]}</td></tr>' for x in v['checks'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI V1.2 · 机械模型</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#edf0ed;color:#233437;font:16px/1.65 -apple-system,BlinkMacSystemFont,sans-serif}}main{{max-width:1320px;margin:auto;padding:34px}}a{{color:#16736e}}nav{{display:flex;gap:24px;flex-wrap:wrap}}h1{{font-size:52px;letter-spacing:-2px;line-height:1.1;margin:24px 0}}h2{{margin-top:65px;font-size:28px}}p{{max-width:930px}}.hero{{display:grid;grid-template-columns:1fr 1.3fr;gap:40px;align-items:center}}.hero img{{width:100%;border-radius:18px}}.pill{{display:inline-block;background:#dce5df;padding:6px 13px;border-radius:20px;margin:5px}}.warn{{padding:22px;background:#fff0d5;border-radius:13px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}figure{{margin:0;background:white;border-radius:14px;overflow:hidden}}figure img{{width:100%;display:block;cursor:zoom-in}}figcaption{{padding:15px}}small{{font-size:12px;display:block;color:#617173;word-break:break-word}}.parts{{grid-template-columns:repeat(4,1fr)}}input{{padding:13px 20px;border:1px solid #b7c6bf;border-radius:8px;width:100%;margin:20px 0;font:inherit}}table{{width:100%;border-collapse:collapse;background:white}}td{{padding:11px 16px;border-bottom:1px solid #e8eaea}}.PASS{{color:#087456}}.BLOCKED{{color:#a66209}}.FAIL{{color:#bc2727}}dialog{{border:0;padding:0;max-width:90vw;max-height:94vh;background:transparent}}dialog img{{max-width:88vw;max-height:90vh}}dialog::backdrop{{background:#000b}}.wide{{width:100%;border-radius:12px}}@media(max-width:800px){{main{{padding:20px}}.hero{{display:block}}.grid,.parts{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:42px}}}}
</style><main><nav><b>MORI / V1.2</b><a href="#views">实际模型</a><a href="#compare">A/B 比较</a><a href="#parts">所有零件</a><a href="#checks">检查</a></nav><section class="hero"><div><h1>圆润外形。<br>真实结构预研。</h1><p>按V1.2重建：120mm头、160mm身体，S288双轮、SCS0009隐藏双轴。CAM整板随头运动，黑色面罩内保留真实相机窗口。</p><span class="pill">M1 已完成</span><span class="pill">M2 部分完成</span><span class="pill">M3 候选件</span><p><b>{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} mm</b><br>腹部25mm · 轮壳网格计算间隙{wm['minimum']['distance_mm']:.2f}mm<br>估算整机{whole['mass_g_rounded']/1000:.2f}kg · 俯仰件{hp['mass_g_rounded']}g</p><nav><a href="mori_v1_2.blend">Blender工程</a><a href="../reports/mechanical_v1_2.md">完整报告</a><a href="README.md">重新生成</a></nav></div><img src="renders/45_assembled.png" alt="实际Blender渲染"></section><p class="warn">{limits} 两个原厂连接器的转换网格仍有拓扑问题，碰撞检查使用保守代理，完整精确装配尚未通过。这些文件尚不是最终加工图；待真实器件回写、试打与实机平衡。预算≤1000元和续航未验证。</p><h2 id="compare">同尺寸、同相机的两个方案</h2><p>选B：圆肩略收腹，深度仅作1.5%收分。保持相同120mm头、95mm车轮及显示/硬件包络，按最终B重新验证。图片由同一脚本真实建模渲染。</p><img class="wide" src="renders/v1_2_shape_comparison.jpg" alt="A B前侧45度对比"><h2 id="views">装配与结构视图</h2><div class="grid">{cards}</div><h2 id="checks">检查与证据边界</h2><p>{v['counts']['PASS']}项PASS · {v['counts']['FAIL']}项FAIL · {v['counts']['NOT_TESTED']}项NOT_TESTED · {v['counts']['BLOCKED']}项BLOCKED。有限采样不是连续运动证明，估算不是实测。</p><table>{rows}</table><p><a href="reports/validation.json">原始检查</a> · <a href="reports/commands.json">命令与日志</a> · <a href="reports/mass_budget.json">质量惯量</a> · <a href="reports/camera_kinematics.json">相机外参</a> · <a href="reports/display_outline_review.json">原厂屏幕装配检查</a> · <a href="reports/purchased_dimensions.md">采购件尺寸依据与缺项</a> · <a href="reports/purchased_geometry_audit.json">来源与比例核验</a> · <a href="reports/组装与打印.md">组装与试打</a> · <a href="reports/外购与自制.md">外购 / 自制</a> · <a href="reports/export_manifest.json">{ex['exported_count']}件STL清单</a></p><h2 id="parts">全部 {len(parts)} 件的真实预览</h2><p>采购参考件、限制包络和打印候选分别标记；尺寸是当前网格的包围尺寸；标PLACEHOLDER的不是已选实物。点击任意图片放大。</p><input id="filter" type="search" placeholder="搜索零件名称 / PRINTABLE / PURCHASED_REFERENCE / PLACEHOLDER"><div class="grid parts">{partcards}</div><p>以config/geometry.json和contracts/mechanical_interfaces.json为当前输入。旧A4已经归档，未覆盖无关硬件和软件成果。</p></main><dialog id="zoom"><img alt="放大实际渲染"></dialog><script>const dlg=document.querySelector('#zoom');document.querySelectorAll('img').forEach(im=>im.addEventListener('click',()=>{{if(im.closest('dialog'))return;dlg.querySelector('img').src=im.src;dlg.showModal()}}));dlg.addEventListener('click',()=>dlg.close());document.querySelector('#filter').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('.part').forEach(p=>p.hidden=!p.dataset.search.toLowerCase().includes(q))}});</script></html>'''
(ROOT/'index.html').write_text(page)
print('V1.2_REPORT_COMPLETE',len(parts),'parts',ex['exported_count'],'STLs')
