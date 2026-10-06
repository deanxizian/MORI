"""Build Chinese review docs and local HTML from executed evidence; optional Pillow only lays out actual renders."""
from pathlib import Path
import json,html,collections,hashlib,datetime,csv,textwrap
ROOT=Path(__file__).resolve().parents[1]; PROJECT=ROOT.parent
j=lambda n:json.loads((ROOT/'reports'/n).read_text())
v=j('validation.json');checks={x['id']:x for x in v['checks']};b=j('bom.json');exp=j('export_manifest.json');mass=j('mass_budget.json')['totals'];motion=j('head_motion.json');full=j('body_head_envelope.json');build=j('build_manifest.json');previews=j('parts_preview_manifest.json');rebuild=j('rebuild_check.json')
geom=json.loads((PROJECT/'config/geometry.json').read_text());shape=checks['assembled_size']['measurement'];xyz=shape['xyz_mm'];tilt=checks['body_tilt_geometry']['measurement'];counts=collections.Counter(x['category'] for x in b)
fmt=lambda a:' × '.join(f'{x:.1f}' for x in a)
report=f'''# MORI V1 阶段 A 检查报告

已实际建立并运行 Blender 项目。这里交付参数化装配、器件最大包络、结构候选、实际渲染和候选 STL；不是成品硬件、生产图或平衡验证。

主规格是用户提供的 MORI_SPEC_V1.md。旧三执行器、无摄像头、-Y 向前约定已退出 V1 真值源；AGENTS 保留了不冲突的原规则。AGENTS_MORI_TEMPLATE.md 未找到，用户明确允许按任务正文继续，因此没有虚构模板内容。V1 的共享输入为 config/geometry.json 和 contracts/mechanical_interfaces.json。

## 结果与尺寸

| 项目 | 本次测量 / 状态 |
|---|---|
| 正常装配宽 × 深 × 高 | {fmt(xyz)} mm |
| yaw ±60° / pitch -20°…+25° 的整机包络 | {fmt(motion['size_xyz_mm'])} mm；130 个联合姿态 |
| 再叠加机身前后 ±15° 的几何包络 | {fmt(full['size_xyz_mm'])} mm；{full['poses']} 个姿态，深度约 185.8 mm |
| 腹部离地 | 25.0 mm；两只轮胎接地，其他件不穿地 |
| 机身倾斜 ±15° 的最低球腹 | {min(x['belly_z_mm'] for x in tilt):.1f} mm；只是几何测试 |
| 轮胎 / 轮毂 / 轮盖对壳体间隙 | 最小实际见证 4.0 mm；整周采样，每 10°，每轮 37 姿态 |
| 身体正面截后宽 / 头直径 | 124 / 105 mm，比例 1.181 |
| 原始母球 / 壳厚 | 头 Ø105、身 Ø150；未非等比缩放；名义壳厚 2.4 mm |
| 模型检查 | {v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL / {v['counts']['NOT_TESTED']} NOT_TESTED / {v['counts']['BLOCKED']} BLOCKED |
| 候选 STL | {exp['exported_count']} / {exp['candidate_count']} 通过拓扑、尺寸及 Blender 原生重新导入 |
| 场景内重复生成 | {rebuild['status']}；连续两次不堆积，未标记对象保留 |
| 部件与预览 | {len(b)} 个条目；每件独立对象与实际模型预览 |

尺寸由实际网格测量，0.1 mm 展示精度不等于打印精度。头部球心保持同一点，因此联合转头没有显著增加正常机身姿态的外部尺寸。加入 ±15° 身体倾斜会增加前后运动包络；这个角度不代表可安全运行或平衡的控制范围。

计算链：轮轴 z=95/2=47.5；身体球心 z=150/2+25=100；轴相对球心 z=-52.5；顶部 z=100+75-12=163；头球心 z=163+52.5-12=203.5；顶点约 256 mm。轮胎内侧 |x|=62+4=66，轮心 |x|=66+18/2=75。没有同时独立锁定总高、球心和离地。

采用 58 / 60 / 62 / 64 mm 四组侧切位置做了真实外观渲染对比。62 mm 使截后的身体仍明显比头丰满；相比 64 mm 少 4 mm 整机宽度。1.15 的参考比值是本次外观研究的选择标准，不是用户原规格中的硬阈值。详见 parameter_comparison.json 与 renders/variants/。

## 结构与相机

共有四个执行器包络：两只轮电机、yaw 舵机、pitch 舵机。Yaw 几何轴与 pitch 轴在头球心相交；实际 yaw 承重轴承中心在 z=148 mm。Yaw 固定座有真正连接的立柱和法兰，转盘驱动盘与中空轴连为一个实体；pitch 有双侧轴承及两根承重短轴。独立 wheel axle 的载荷进入框架，未用外壳充当承重梁。

为使低头时屏幕绕过支架，yaw 承重环下移、转盘半径减为 19 mm；头球心与 256 mm 外观高度没有改变。中空轴及有限 140° 弧形槽为线束提供实际通路；pitch 支架底座有同轴让位。它们仍须做强度、疲劳、夹线和线束弯曲试验。

相机在黑屏上方有独立开口和透明窗。假设 70°×50° 视场，99 条针孔射线穿过真实窗口、未被脸框遮挡；另对 130 个联合姿态与固定机身做了射线检查。**真实镜头、透明窗折射、反光和标定尚未验证。** 该视场是假设，不是已选传感器参数。

坐标区分 assembly_ground（装配地面原点）与 body_axle（轮轴中点原点）。后者的头中心 z=156 mm；相机零位入瞳在 body_axle 的 (0,37.4,189) mm。camera_kinematics.json 给出 CV 坐标、两关节变换和安装外参。相机观察和关节角需同一时间基准；未加实测反馈前，头角只能标为估计。

## 质量与惯量是估计

整机约 {mass['whole_robot']['mass_g_rounded']/1000:.2f} kg；随 pitch 运动约 {mass['head_pitch']['mass_g_rounded']} g；yaw 总运动负载约 {mass['head_yaw_total']['mass_g_rounded']} g。名义整机重心在装配坐标约 {mass['whole_robot']['center_mm_rounded']} mm。

用闭合网格四面体积分计算几何体积、一阶矩和二阶矩。假设 PLA 密度 1.24 g/cm³，薄壳有效实体比例 98%、普通支架 65%；电机各 75 g、电池 120 g、舵机各 18 g 等均为未选型质量预算。附件、线束和填充会改变结果，按至少 ±35% 不确定度看待。头部 pitch 轴惯量约 {mass['head_pitch']['inertia_at_head_joint_kg_m2'][0][0]:.2g} kg·m²，yaw 轴运动惯量约 {mass['head_yaw_total']['inertia_at_head_joint_kg_m2'][2][2]:.2g} kg·m²。不能按这些估算直接宣布舵机扭矩足够。

电池中心 (0,0,71) mm，Y 可有限调整 ±4 mm；两板中心 (0,±32,130) mm；身体 IMU 固定于刚性座、随身体而非头部运动，内视图标了 XYZ。各附件位置与材料假设详见 assembly_instances.json、mass_budget.json。

## 检查方法与边界

碰撞先用包围盒排除明显远离的零件，再用 **Manifold 3.5.3 对实际闭合三角实体求交体积**，包含一个实体完全位于另一个实体内部的情况。刚性零件超 0.01 mm³ 的交叠视为失败；线束分配管体采用 0.1 mm³ 的报告阈值。没有用“包围盒不重叠”代替相交检测，也没有把所有预期接口的体积穿插自动豁免。轴承、轴、螺钉等预期接触在 intended_contacts.json 单列。

联合角度步长 yaw=10°、pitch=5°；平面倾斜步长 1°。有限采样、三角网格与数值阈值不是连续构型空间数学证明，也未验证所有零间隙切触及全局最小分离距离。轮壳的 4 mm 下界另由侧平面与车轮旋转不变的 X 范围约束，并由实际点到三角面的距离达到该下界。

球面检查包括所有母球顶点，以及未截切外表面选定三角面；平面侧切、顶部切面、孔口、凸台不伪装成球面。壳厚是在内外球面之间进行径向射线抽查，约 2.40 mm；孔边和梁根的全局最小壁厚仍是 NOT_TESTED。正实体连通分量、未声明封闭内孔、边关联、绕序、退化面和正体积已检查；独立精确自交检查仍是 NOT_TESTED。

STL 使用正常装配坐标、数值单位 mm、缩放 1；先由独立二进制读取器复查，再用 Blender 原生 stl_import 导入核对包围尺寸。采购参考件、电子器件、轮胎及柔性线束不混进硬壳 STL。四片软托架垫有预览与几何参考，单独做软材料/裁切方案；未进入硬质候选 STL 批次。

## 尚未完成，不能放行制造的项目

- **极限抬头可看到部分内部结构。** pose_up 的 yaw=+60° / pitch=+25° 渲染中，下部开口和框架局部可见。本次没有声称全角度完全遮蔽。最小改动方向是：真实屏幕深度确定后缩小护罩扫掠让位，或增加经过摩擦/夹线检查的薄柔性遮光件；保持两轴、相机、头球心与外观高度，不增加明显脖子。
- 相机窗当前是随球面曲率的透明参考件，不是普通 FDM 打印件，也没有证明可直接购买。可评估低成本平片内凹座，再重新检查真实视场、反光和相机位置；本次未伪装成已采购光学件。
- 轮驱只是电机最大包络和独立承重/传动路线。带齿、整齿数带轮、带长、张紧、轮毂锁轴、反馈与实际扭矩响应未确定。不能把光滑带轮包络当加工图，也不能把有刷 PWM 接口当 Hover 的 FOC 力矩接口直接替换。
- 显示器、电机、舵机、双 MCU、电池与接口模块没有冻结型号。旧约 71 mm DevKit 超过本版 48 mm 板卡分配，不能缩放器件。需选紧凑模块或回改布局；电池容量须由实际平均功耗决定。
- 厂商安装孔、嵌件、舵盘花键、轴承精确配合、紧固长度、全部工具/手指可达、应力释放与附件轴向保持待阶段 B。已做电池拆出和四处工具杆路径，不代表所有零件装配路径已证明。
- 声学密封/回声、天线效果、发热、透明件光学、打印强度、自交/全局壁厚、软线变形与疲劳、托架摩擦及插线拉力、实机自平衡与 60 分钟续航待实测。
- 首台 ≤1000 元（建议 BOM+基础打样≤900，余量100）的完整成本表尚未有真实报价，当前 BLOCKED；没有通过漏项宣称预算达标。

托架名义四点支撑内的重心投影裕量约 {checks['dock_nominal_COM_projection']['measurement']['margin_mm']:.1f} mm，轮胎离地 8 mm；假设质量、无插线外力和刚性接触。它不是运行中的第三支撑，托架稳定不能证明断电自立。

## 逐项证据

| 检查 | 状态 | 说明 |
|---|---|---|
'''
for c in v['checks']:report+=f"| {c['id']} | {c['status']} | {c['summary']} |\n"
report+='\n运行命令见 commands.json / additional_commands.json；完整控制台见 build.log、validate.log、render.log、export.log。版本见 build_manifest.json。文件散列与历史文件保留情况见 preservation_check.json。\n'
(ROOT/'reports/阶段A检查报告.md').write_text(report)

def route(x):
 n=x['id']
 if n.startswith('Dock_Pad'):return '软垫裁切 / 单独 TPU 试样，未进硬壳 STL'
 if x['category']=='PRINTABLE':return '定制打印候选' if x['candidate_stl'] else '定制打印待深化'
 if n=='Camera_Window':return '透明光学件定制 / 平片方案待适配'
 if n=='Face_Protector':return '透明片材采购后裁切'
 if n.startswith('Tire_'):return '软胶轮胎外购待选；TPU 备选须验证'
 if n.startswith(('Pulley_','Belt_')):return '标准传动件选型；当前仅光滑包络'
 return '通用器件采购方向，具体型号待选'
rows=[dict(id=x['id'],name=x['name'],category=x['category'],data_status=x['data_status'],route=route(x),dimensions_mm=fmt(x['dimensions_mm']),candidate_stl=x['candidate_stl']) for x in b]
with (ROOT/'reports/外购与自制.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
md='''# 外购与自制 · V1

类别说明：PRINTABLE 是自制打印方向，PURCHASED_REFERENCE 是采购/透明片参考，PLACEHOLDER 是未选型号的硬件空间分配。所有当前尺寸均 ASSUMED，没有把旧候选器件冒充已验证 V1 选型。

BOM 的 113 个几何条目不等于 113 个采购 SKU。显示层/PCB/连接器通常属于同一显示模组，相机/镜筒同理；采购时按真实整件合并数量。

通常外购的类目包括 2 只轮电机与反馈/驱动、2 只头部舵机、轴承、金属轴/紧固件、2 块 MCU、IMU、圆屏、相机、麦克风、功放/扬声器、电池及保护/充电/稳压、USB-C 插座、按钮、开关、线束。它们是通用采购方向，**不表示任意网购件都能装进模型**。传动比、扭矩响应、价格、续航和器件孔距都要重新核对。

自制打印方向是球壳、显示框/相机支架、yaw/pitch 承重件及托座、内部框架、电机座、轮毂与盖、电池托架、PCB/IMU/音频/接口固定件、约束夹、独立托架和配合试样。轮毂锁轴与标准件配合未完成，STL 仅是候选。

轮胎不能跟硬壳一批用普通 PLA 打印。透明圆屏片可采购片材裁切；相机的曲面保护窗是待适配光学参考，不能把普通透明 FDM 当作成品光学窗口。

| ID | 部件 | 工艺 / 采购方向 | 状态 | 包围尺寸 mm |
|---|---|---|---|---|
'''
for x in rows:md+=f"| {x['id']} | {x['name']} | {x['route']} | {x['data_status']} | {x['dimensions_mm']} |\n"
(ROOT/'reports/外购与自制.md').write_text(md)
# Source preservation: permitted changes are recorded explicitly, never imply other work was overwritten.
old=j('preexisting_hashes.json');allowed={'AGENTS.md','README.md','params.json','hardware/mechanical_interfaces.json'};changed=[];missing=[]
for rel,digest in old.items():
 p=PROJECT/rel
 if not p.exists():missing.append(rel)
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(rel)
(ROOT/'reports/preservation_check.json').write_text(json.dumps({'status':'PASS' if not missing and not(set(changed)-allowed) else 'NOT_TESTED','changed_existing_files':changed,'authorized_migration_files':sorted(allowed),'unexpected_changes_or_concurrent_edits':sorted(set(changed)-allowed),'missing_preexisting_files':missing,'note':'Hash comparison only; if another task edited a file concurrently this report does not attribute authorship. Original A0 models/scripts/exports were not edited by V1 work.'},ensure_ascii=False,indent=2))
# Contact sheets ONLY arrange actual Blender PNGs; no synthetic rendering or geometry edits.
try:
 from PIL import Image,ImageDraw,ImageFont
 font=ImageFont.load_default(size=15);big=ImageFont.load_default(size=25)
 for label,selected,cols,cell in [('printable_parts',[x for x in previews if x['category']=='PRINTABLE'],7,228),('hardware_parts',[x for x in previews if x['category']!='PRINTABLE'],8,200)]:
  height=70+((len(selected)+cols-1)//cols)*cell;im=Image.new('RGB',(cols*cell,height),(22,29,36));dr=ImageDraw.Draw(im);dr.text((20,20),'MORI V1 / '+label.replace('_',' ').upper()+' / ASSUMED',fill='white',font=big)
  for i,x in enumerate(selected):
   pic=Image.open(ROOT/x['file']).convert('RGB');pic.thumbnail((cell-12,cell-58));xx=(i%cols)*cell+6;yy=70+(i//cols)*cell;im.paste(pic,(xx+(cell-12-pic.width)//2,yy))
   for k,t in enumerate(textwrap.wrap(x['id'],26)):dr.text((xx,yy+cell-53+k*17),t,fill=(222,235,240),font=font)
  im.save(ROOT/'renders'/(label+'.jpg'),quality=92)
except ImportError:
 for name in ['printable_parts.jpg','hardware_parts.jpg']:
  q=ROOT/'renders'/name
  if q.exists():q.unlink()
 print('Pillow unavailable: optional contact sheets skipped; individual Blender previews remain.')
views=[('45_assembled','45° 装配'),('front','前视'),('side','侧视'),('rear','后视与接口'),('top','顶视'),('bottom','底视'),('exploded','爆炸图'),('head_section','头部双轴剖视'),('internal','内部布局与 IMU 方向'),('clearance','离地与间隙标注'),('wheel_gap_detail','轮壳局部'),('pose_up','yaw +60° / pitch +25°'),('pose_down','yaw -60° / pitch -20°'),('docked','独立维护托架')]
style='''*{box-sizing:border-box}body{margin:0;background:#111c25;color:#edf0ee;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1360px;margin:auto;padding:36px 28px}h1{font-size:44px;margin:4px 0}h2{margin-top:44px}p{max-width:1000px;color:#bfcbd0}a{color:#8ae0e5}small{color:#b7c9ce}.tag{display:inline-block;padding:3px 10px;border:1px solid #526674;border-radius:20px;font-size:12px}.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.fact{background:#1d2c36;padding:18px;border-radius:14px}.fact b{font-size:25px;display:block}.hero{width:100%;max-height:740px;object-fit:contain;background:#27323d;border-radius:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}.card{background:#1d2c36;border-radius:12px;padding:12px;overflow:hidden}.card img{width:100%;aspect-ratio:1;object-fit:contain;background:#303841;border-radius:8px}.card strong{display:block;margin-top:8px}.card code{font-size:12px;color:#96c7d6;word-break:break-all}input,select{padding:12px;border-radius:8px;border:1px solid #657f8d;background:#1d2c36;color:white;margin:4px;font-size:16px}input{min-width:280px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:10px;border-bottom:1px solid #344954;text-align:left}.PASS{color:#8bddb1}.FAIL{color:#ffb19e}.NOT_TESTED,.BLOCKED{color:#edc680}.note{padding:18px;border-left:3px solid #edc680;background:#26333c}.parts-hidden{display:none}@media(max-width:650px){.facts{grid-template-columns:repeat(2,1fr)}main{padding:22px 14px}h1{font-size:34px}}'''
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI V1 · 参数化机械项目</title><style>{style}</style><main><span class="tag">STAGE A · ASSUMED · 实际 Blender 模型</span><h1>MORI V1</h1><p>可编辑装配、双轴头部、四执行器、摄像头与独立维护托架。此图册所有视图来自同一套真实网格；零件缩略图仅单独显示各个对象。</p><p><a href="models/MORI_V1_A.blend">打开 / 下载 .blend</a> · <a href="reports/阶段A检查报告.md">完整检查报告</a> · <a href="reports/组装与打印.md">装配与打印</a> · <a href="reports/外购与自制.csv">外购 / 自制 CSV</a> · <a href="README.md">重新生成说明</a></p><div class="facts"><div class="fact"><b>256 mm</b>正常装配总高</div><div class="fact"><b>25 / 4 mm</b>腹部离地 / 轮壳间隙</div><div class="fact"><b>130 姿态</b>yaw / pitch 联合采样</div><div class="fact"><b>{len(b)} / {exp['exported_count']}</b>部件预览 / 候选 STL</div></div><p></p><img class="hero" src="renders/45_assembled.png" alt="MORI V1 实际装配渲染"><p class="note">阶段 A 不是成品放行。真实器件、加工孔、线束疲劳、预算、打印与实机平衡尚未完成；极限抬头可见部分内部结构。当前检查：{v['counts']['PASS']} PASS，{v['counts']['FAIL']} FAIL，{v['counts']['NOT_TESTED']} NOT_TESTED，{v['counts']['BLOCKED']} BLOCKED。</p><h2>装配、结构与运动</h2><div class="grid">'''
for name,label in views:page+=f'<article class="card"><a href="renders/{name}.png"><img loading="lazy" src="renders/{name}.png" alt="{label}"></a><strong>{label}</strong></article>'
page+='</div><h2>侧切参数比较</h2><p>四种真实外轮廓试算；选用 |x|=62 mm。只比较外观，不表示其他三组也通过器件装配检查。</p><div class="grid">'
for c in j('parameter_comparison.json')['candidates']:page+=f'<article class="card"><img loading="lazy" src="{c["image"]}"><strong>侧切 {c["side_cut_abs_x_mm"]} mm {"· 已选" if c["selected"] else ""}</strong><small>身体正面宽 {c["cut_body_front_width_mm"]} / 头 105 mm；整机宽 {c["overall_width_mm"]:.1f} mm</small></article>'
page+='</div><h2>逐件预览与工艺</h2><p>PRINTABLE 表示拟打印，PLACEHOLDER 表示未选定硬件。尺寸是装配坐标下的包围盒；真实型号和孔距仍待确认。</p><input id="search" placeholder="搜索中文名称或 ID"><select id="kind"><option value="">全部类别</option><option>PRINTABLE</option><option>PLACEHOLDER</option><option>PURCHASED_REFERENCE</option></select><div class="grid" id="parts">'
by={x['id']:x for x in rows};stls={x['id']:x for x in exp['parts']}
for x in previews:
 row=by[x['id']];link=f'<a href="{stls[x["id"]]["file"]}">候选 STL</a>' if x['id'] in stls and stls[x['id']]['status']=='PASS' else '无硬质 STL'
 page+=f'<article class="card part" data-kind="{x["category"]}" data-search="{html.escape(x["id"]+x["name"])}"><a href="{x["file"]}"><img loading="lazy" src="{x["file"]}" alt="{html.escape(x["name"])}"></a><strong>{html.escape(x["name"])}</strong><code>{x["id"]}</code><br><span class="tag">{x["category"]}</span> <small>ASSUMED</small><p>{html.escape(row["route"])}<br>{row["dimensions_mm"]} mm<br>{link}</p></article>'
page+='</div><h2>检查状态</h2><table><thead><tr><th>项目</th><th>结果</th></tr></thead><tbody>'
for c in v['checks']:page+=f'<tr><td>{html.escape(c["summary"])}</td><td class="{c["status"]}">{c["status"]}</td></tr>'
page+='</tbody></table><p>复现日志、算法及未覆盖范围见 reports。修改尺寸后必须重新运行；STL 拓扑通过不代表可制造、负载或平衡性能通过。</p><p><a href="THIRD_PARTY_NOTICES.md">来源与第三方说明</a></p></main><script>function filter(){const q=document.querySelector("#search").value.toLowerCase(),k=document.querySelector("#kind").value;document.querySelectorAll(".part").forEach(e=>e.classList.toggle("parts-hidden",!e.dataset.search.toLowerCase().includes(q)||(k&&e.dataset.kind!==k)))}document.querySelector("#search").addEventListener("input",filter);document.querySelector("#kind").addEventListener("change",filter);</script></html>'
(ROOT/'index.html').write_text(page)
print('REPORT_COMPLETE',len(b),'parts',exp['exported_count'],'STLs')
