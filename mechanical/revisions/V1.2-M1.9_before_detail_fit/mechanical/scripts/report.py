"""M1.9 report/gallery from executed Blender evidence, never synthetic images."""
from pathlib import Path
import json,html,math
from module_report import structure_text,printing_audit
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text())
esc=html.escape
p=json.loads((PROJECT/'config/geometry.json').read_text());v=load('validation.json');mass=load('mass_budget.json');ex=load('export_manifest.json');bm=load('build_manifest.json');motion=load('head_motion.json');wm=load('wheel_clearance.json');pose=load('body_head_envelope.json');parts=load('parts_preview_manifest.json');consistency=load('delivery_consistency.json');rebuild=load('rebuild_check.json');lower=load('lower_body_comparison.json');belly=load('belly_relayout_validation.json');bom=load('bom.json');datums=load('derived.json');structure=load('structure_changes.json');hardware=json.loads((PROJECT/'contracts/components.json').read_text())
checks={a['id']:a for a in v['checks']};size=checks['assembled_size']['measurement']['xyz_mm'];hp=mass['totals']['head_pitch'];whole=mass['totals']['whole_robot'];c=hp['center_mm_rounded'];hz=datums['head_z']
torque=[{'pitch_deg':a,'gravity_Nm':round(abs((c[1]*math.cos(math.radians(a))-(c[2]-hz)*math.sin(math.radians(a)))/1000*hp['mass_g_rounded']/1000*9.81),4)} for a in range(-20,26,5)]
(ROOT/'reports/head_load_estimate.json').write_text(json.dumps({'status':'ASSUMED','gravity_samples':torque,'sampled_max_Nm':round(max(x['gravity_Nm'] for x in torque),3),'inertia_kg_m2':hp['inertia_at_head_joint_kg_m2'][0][0],'dynamic_equation':'tau=gravity+Ixx*alpha+cable/friction; no continuous-torque qualification','mass_uncertainty_percent':35},indent=2))
structure['geometry_status']='FAIL' if v['counts']['FAIL'] else 'BLOCKED' if v['counts']['BLOCKED'] else 'PASS';structure['validation_summary']=v['counts'];structure['geometry_evidence']='validation.json: LCD two connector proxies remain; zero observed overlap does not certify actual hardware'
(ROOT/'reports/structure_changes.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2))
assembly=structure_text(p,structure,mass,v,bom,load('module_service_checks.json'))
for name in ['组装与打印.md','结构简化说明.md']:(ROOT/'reports'/name).write_text(assembly)
(ROOT/'reports/打印件审查.md').write_text(printing_audit(bom))
limits='电池80×65×30、运动载板70×35×12、电源板80×40×18均是空间预留。S3电源PCB尚无完整外形、装件高度、孔位和插头CAD；新托板只固定到机械框架，PCB专用夹片仍待设计。LCD按原厂CAD1:1导入，但两连接器使用保守检查代理。橙色表示资料未全；未采购、未实物测量、未打印或实机平衡。'
procurement='''# 外购与自制

| 分类 | 内容 | 状态 |
|---|---|---|
| V1.2指定外购 | S288×2、SCS0009×2、CAM33700、LCD35079 | 采用原厂尺寸/资料。LCD原CAD导入1:1；S288/SCS为尺寸图简化几何；CAM只有板框等部分尺寸可核 |
| 通用件待选型/实测 | 3S电池、4Ω3W喇叭、轮胎、轴承、短轴、20T舵盘、紧固件、按钮、开关、USB-C充电和6V电源模块、线束 | 占位与候选尺寸不是已存在的合适商品，采购前需核对 |
| 需硬件设计 | S3电源PCB及其装件、载板/线束出口 | TPS54302芯片封装不代表完整电路板。机械提供80×40×18容量目标；最终包络未定 |
| 需打印候选 | 分壳、13个主体支撑组件、声腔、轮毂/盖、维护托架等 | STL只包含打印件和试样；最终孔、强度、材料与切片尚未冻结 |
| 平片 | 黑面罩、屏保护片、独立相机窗口 | 优先平片加工；光学反射/透过率待测 |

S288含轮驱，不增加额外FOC；CAM板载音频不重复增加Codec、功放或独立麦克风。相机和显示由pitch组件承载，Yaw舵机装在yaw组。外置托架没有电机或充电触点，充电/刷机时车轮必须禁驱。硬件契约由硬件任务拥有，机械任务只读。
'''
(ROOT/'reports/外购与自制.md').write_text(procurement)
(ROOT/'reports/设计与选型分工.md').write_text(procurement+'\n当前新设计：横躺轮驱浅座/底盖、开口Yaw承重桥、U托短耳座、可拆固定反力轴、电源平托板。仍待选型：真实舵盘、轴承保持、轮输出转接、最终电池与电源模块。待硬件给尺寸后设计：电源PCB固定片、CAM/运动载板紧固和完整插头应力释放。\n')
ct='\n'.join(f"| {x['id']} | {x['status']} | {x['summary']} |" for x in v['checks'])
report=f'''# MORI {p['revision']} — 参数化装配预研报告

本次完成横躺轮驱与头内倒装Yaw的联合调整，目标是给电池、电源板、运动/驱动接口板留连续空间。结果为可编辑Blender、脚本、候选STL及同几何实际渲染；不是实物装配或生产发布。

{limits}

## 结果与空间

| 项目 | M1.8 | M1.9 |
|---|---:|---:|
| 轮驱机身最高点 | 77mm | 62.5mm |
| 电池中心Z | 103mm | 91mm |
| 主安装板上表面Z | 127mm | 115mm |
| 电源板空间预留 | 44×16×10mm | 80×40×18mm |
| 主体支撑打印组件 | 11 | {structure['support_printed_parts_after']} |

电池到板底名义间隙{belly['measurements']['battery_to_deck_mm']:.1f}mm；电源预留底面落在独立托板上，与Yaw承重桥最小网格距离{belly['measurements']['power_to_yaw_bridge_min_gap_mm']:.1f}mm。连接器、实际散热面、手指和容差需另留，不能把全部包络体积视为可装任意PCB。

外观尺寸、轮地关系和屏幕保持：装配宽×深×高{size[0]:.1f}×{size[1]:.1f}×{size[2]:.1f}mm；名义头120、身体160、轮胎105×18mm；球腹离地20mm、轮轴52.5mm、身体中心100mm、头中心222mm。轮壳计算最小间隙{wm['minimum']['distance_mm']:.2f}mm。282mm低于原285～295mm偏好，但满足300mm产品上限，这是已记录的用户低身位调整。母球保留；身体B采用声明的轻微卵形公式，未称其修形面为严格正球。

全头动作包围尺寸{[round(x,1) for x in motion['size_xyz_mm']]}mm；130组离散姿态，yaw−60～60°步长10°、pitch−20～25°步长5°。身体±15°几何检查与4030组身体/头组合包络见body_head_envelope.json，不代表安全控制范围。

## 机构、维护与走线

Yaw舵机机壳固定在头内yaw框架，输出/舵盘经可拆D形反力轴固定到身体。机壳转动驱动头左右转；关系为head_yaw=−shaft_relative_angle，真实舵机零位、角反馈方向和限位须台架标定。Pitch仍独立双侧支撑，不增加机械roll。负载经转台/独立承重轴承/宽侧板桥传给框架，不经过细舵机轴悬臂。

反力轴的D形槽、横向防退和舵盘夹口均为明确候选几何。舵盘实际型号、夹紧预载、扭矩、打印层强度、轴承保持尚未验证。没有把圆滑的占位连接当成已经可承载的真实花键。电源平托板有4枚试配短螺钉；最终PCB孔位和固定夹片未编造。

IMU在刚性平板局部座上绕Z90°放置，其坐标与轴标记已更新；不能安装在维修盖上。运动载板后置，CAM随pitch头运动。Yaw服务环、下段至头部引线、pitch环和线端只是保守空间，静态路由冲突、跨运动组碰撞分别报告；柔性、连接器拔插和线疲劳尚未实测。

完整拆装和打印建议见mechanical/reports/组装与打印.md。电池仍须禁驱、托架支撑、拆轮/抽轴并解除壳体后取出，不宣称快换。头内Yaw维修先取pitch头，再取Yaw舵机、U托、反力轴；有限抽出轨迹和工具杆空间实际检查，不以爆炸图代替。

## 质量、惯量和控制交接

整机估重约{whole['mass_g_rounded']/1000:.2f}kg；pitch运动件约{hp['mass_g_rounded']}g，含完整头的yaw运动组约{mass['totals']['head_yaw_total']['mass_g_rounded']}g。pitch质心{hp['center_mm_rounded']}mm，绕俯仰轴Ixx约{hp['inertia_at_head_joint_kg_m2'][0][0]:.2g}kg·m²。采样重力矩峰值约{max(t['gravity_Nm'] for t in torque):.3f}N·m，未计真实加速度、摩擦和线力。

统一假设下COM离地约{lower['before']['estimated_COM_ground_mm'][2]:.1f}→{lower['after']['estimated_COM_ground_mm'][2]:.1f}mm，相对轮轴{lower['before']['estimated_COM_above_axle_mm']:.1f}→{lower['after']['estimated_COM_above_axle_mm']:.1f}mm。变化{lower['changes']['estimated_COM_lowering_mm']:.1f}mm。为避免将预留空盒当实心材料，未知电源板在两版比较均统一假设30g；旧版存档原估算因此与这里的标准化比较不同。其它密度/有效填充保持一致；新增结构按真实网格计重。

PLA1.24g/cm³、外壳98%/当前支撑95%/其它65%有效实体量，电池190g、CAM18g等是假设。至少±35%不确定。低重心不是控制验收，必须按新COM、惯量、Yaw方向和IMU安装姿态复核控制模型。相机外参仍按T_body_axle_camera=T(head) Rz(yaw) Rx(pitch) T(pupil) R_CV导出，CV光轴+Y。相机内外参、零位和时序需实机标定。交接见ADR-MECH-021。

外置无源维护托架将车轮抬高8mm，要求DISARM/DOCKED_MAINTENANCE。假设COM投影和网格接触已检查；软垫、摩擦、插线拉力和实物防倾覆未测，不代表机器人断电可站立。

## 已执行验证

Blender {bm['blender']}（{bm['blender_hash']}），Python {bm['python']}，Manifold {bm['manifold3d']}。实际命令、返回码、日志在mechanical/reports/commands.json。重复执行build两次：{rebuild['status']}；输入/模型/渲染/STL一致性：{consistency['status']}。导出{ex['exported_count']}件候选STL并实际重新导入检查毫米尺寸；不含采购件、轮胎和爆炸位移。

检查计数：{v['counts']}。AABB只作初筛，干涉用三角网格体积交集；有意接触不豁免穿透。LCD两个连接器使用披露的保守代理，完整精确适配仍BLOCKED。全自交、全局最小壁厚、真实线束柔性、紧固扭矩和动态平衡未通过验证。有限采样不构成连续空间证明。

| 检查 | 结果 | 范围 |
|---|---|---|
{ct}

## 硬件与交付边界

只读核对{hardware['revision']}。components.json由硬件拥有，机械任务未修改。S3电源PCB尺寸未定，TPS54302的2.9×2.8×1.1mm仅是IC封装。运动载板70×35×12、CAM37×37×12、电池80×65×30及扬声器/充电模块占位须回写真实装件和插头。缺项详见purchased_dimensions.md与purchased_geometry_audit.json。

已生成：参数、接口、模型、候选打印件、实际视图、逐件表和装配说明。已执行几何检查：见上表及各JSON原始证据。待硬件选型/PCB：真实舵盘、安装孔、连接器、供电模块和电池。待打印：间隙/孔/夹口试样、切片与承载。待实机：称重、IMU/相机/舵机标定、热/声学/射频及自平衡。预算≤1000元和续航尚未验证，没有采购或PCB冻结。
'''
(PROJECT/'reports/mechanical_v1_2.md').write_text(report)
(ROOT/'reports/阶段A检查报告.md').write_text('# 当前报告路径\n\n当前依据为项目reports/mechanical_v1_2.md。历史版本在mechanical/revisions/；不定义当前参数。\n')
# Contact sheets use existing Blender renders without altering any model.
from PIL import Image,ImageDraw,ImageFont
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',24)
for target,folder,row_names,col_names,w in [('structure_comparison.jpg','structure',['whole','belly'],['before','after'],800),('appearance_comparison.jpg','appearance',['before','after'],['front','side','oblique'],600),('v1_2_shape_comparison.jpg','variants',['A','B'],['front','side','45'],480)]:
 sheet=Image.new('RGB',(len(col_names)*w,len(row_names)*(w+35)),'#edf0ed');d=ImageDraw.Draw(sheet)
 for ri,r in enumerate(row_names):
  for ci,col in enumerate(col_names):
   f=f'{col}_{r}.png' if folder=='structure' else f'{r}_{col}.png'
   im=Image.open(ROOT/'renders'/folder/f).convert('RGB').resize((w,w));sheet.paste(im,(ci*w,ri*(w+35)+35))
   label=f'{r} / {col}'
   if folder=='structure':label=(p['structure']['comparison_baseline']['revision'] if col=='before' else p['revision'])+' / '+r
   if folder=='appearance':label=(p['structure']['comparison_baseline']['revision'] if r=='before' else p['revision'])+' / '+col
   d.text((ci*w+12,ri*(w+35)+4),label,fill='#24343d',font=font)
 sheet.save(ROOT/'renders'/target,quality=94)
for page in range(math.ceil(len(parts)/20)):
 group=parts[page*20:(page+1)*20];sheet=Image.new('RGB',(1250,50+math.ceil(len(group)/5)*300),'#eeeeea');d=ImageDraw.Draw(sheet);d.text((20,10),p['revision']+f' | PARTS {page+1}',fill='#24343d',font=font)
 for i,a in enumerate(group):
  im=Image.open(ROOT/a['file']).convert('RGB').resize((245,245));x=i%5*250;y=i//5*300+50;sheet.paste(im,(x,y));d.text((x+5,y+248),a['id'][:24],fill='#24343d',font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',14))
 sheet.save(ROOT/f'renders/parts_sheet_{page+1:02}.jpg',quality=92)
labels={'belly_detail':'降低电池与连续板卡区','yaw_drive_detail':'头内倒装Yaw、承重与反力连接','internal':'内部整体布局','front':'正视','side':'侧视','rear':'后视','top':'顶视','bottom':'底视','exploded':'爆炸展示','head_section':'双轴头部剖视','structure_only':'承重结构','structure_exploded':'支撑组件拆分','deck_detail':'降低安装板与电源托板','head_support':'平板头托','face_detail':'居中圆屏与独立相机','screen_outline_review':'原厂LCD和安装框','clearance':'离地与高度','wheel_gap_detail':'轮壳间隙','balance_side':'假设质量重心','pose_up':'Yaw+60 / Pitch+25','pose_down':'Yaw−60 / Pitch−20','docked':'维护禁驱托架'}
cards=''.join(f'<figure><img loading="lazy" src="renders/{n}.png" alt="{label}"><figcaption>{label}</figcaption></figure>' for n,label in labels.items())
partcards=''.join(f'<figure class="part" data-search="{esc(str(a))}"><img loading="lazy" src="{a["file"]}" alt="{esc(a["id"])}"><figcaption><b>{esc(a.get("name",a["id"]))}</b><br>{esc(a["id"])}<br>{esc(str(a.get("dimensions_mm",[])))} mm<br>{esc(str(a.get("category","")))} / {esc(str(a.get("status","")))}</figcaption></figure>' for a in parts)
rows=''.join(f'<tr><td>{esc(x["summary"])}</td><td>{x["status"]}</td></tr>' for x in v['checks'])
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {p['revision']}</title><style>body{{margin:0;background:#eef1ef;color:#203238;font:16px/1.7 system-ui,sans-serif}}main{{max-width:1280px;margin:auto;padding:32px}}nav{{display:flex;flex-wrap:wrap;gap:22px;margin-bottom:28px}}a{{color:#12647a}}h1{{font-size:40px;line-height:1.25}}h2{{margin-top:54px}}.hero{{display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:center}}img{{width:100%;border-radius:12px;cursor:zoom-in}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}figure{{margin:0;background:white;padding:12px;border-radius:14px}}figcaption{{font-size:14px;padding-top:8px}}.parts{{grid-template-columns:repeat(4,1fr)}}.warn{{background:#fff1d7;padding:20px;border-radius:12px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #dce1df}}input{{padding:14px;margin:20px 0;width:90%}}dialog{{width:85vw;max-width:1200px;padding:10px;border:0;border-radius:16px}}dialog img{{max-height:85vh;object-fit:contain}}[hidden]{{display:none!important}}@media(max-width:750px){{main{{padding:18px}}.hero,.grid{{grid-template-columns:1fr}}.parts{{grid-template-columns:repeat(2,1fr)}}}}</style><main>
<nav><b>MORI / {p['revision']}</b><a href="#appearance">本次调整</a><a href="#structure">内部结构</a><a href="#views">实际视图</a><a href="#parts">全部零件</a><a href="#checks">检查</a></nav>
<section class="hero"><div><h1>给肚子里的<br>电池和板卡腾空间。</h1><p>轮驱横躺90°，左右转头舵机倒装进头内。电池与主安装板下降12mm，保留简单分件、独立承重轴承和真实轮地关系。</p><p><b>{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} mm</b><br>球腹离地20mm · 轮壳{wm['minimum']['distance_mm']:.2f}mm<br>估重{whole['mass_g_rounded']/1000:.2f}kg，非实测</p><nav><a href="mori_v1_2.blend">Blender工程</a><a href="../reports/mechanical_v1_2.md">完整报告</a><a href="README.md">重新生成</a></nav></div><img src="renders/45_assembled.png" alt="同一实际模型外观"></section>
<p class="warn">{limits}</p><h2 id="appearance">M1.9 · 两处舵机一起重排</h2><table><tr><th>项目</th><th>之前</th><th>现在</th></tr><tr><td>轮驱机身顶部</td><td>77mm</td><td>62.5mm</td></tr><tr><td>电池中心</td><td>103mm</td><td>91mm</td></tr><tr><td>主安装板上表面</td><td>127mm</td><td>115mm</td></tr><tr><td>电源板容量预留</td><td>44×16×10mm</td><td>80×40×18mm，有可拆平托板</td></tr></table><p>电池上方仍有5mm名义间隙；电源预留与承重桥最小距离{belly['measurements']['power_to_yaw_bridge_min_gap_mm']:.1f}mm。真实S3板孔、装件和插头未定。外形、轮胎、居中圆屏及独立相机保持。</p>
<h2 id="structure">承重、驱动和装配</h2><p>头部重量经过独立轴承和开口承重桥传给框架。头内Yaw机壳随左右转头运动，舵盘通过可拆反力轴固定在身体；需要重新标定舵机转向。维修时先取pitch头，再取Yaw舵机、U托和反力轴。支撑从11件变为{structure['support_printed_parts_after']}件，新增反力轴与电源平托板。<a href="reports/结构简化说明.md">装配顺序与结构说明</a></p><img src="renders/structure_comparison.jpg" alt="M1.8和M1.9同相机真实结构及腹部比较">
<p>同一附件质量假设下，估计COM离地{lower['before']['estimated_COM_ground_mm'][2]:.1f}→{lower['after']['estimated_COM_ground_mm'][2]:.1f}mm。未知电源板两版统一按30g估算，至少±35%质量不确定；这不是动态平衡验收。<a href="reports/lower_body_comparison.json">质量与惯量比较</a></p>
<h2 id="views">同几何实际Blender视图</h2><div class="grid">{cards}</div><h2 id="checks">检查与尚未覆盖的范围</h2><p>{v['counts']['PASS']} PASS · {v['counts']['FAIL']} FAIL · {v['counts']['NOT_TESTED']} NOT_TESTED · {v['counts']['BLOCKED']} BLOCKED。130组联合姿态是有限采样，完整实物适配仍未通过。</p><table>{rows}</table><p><a href="reports/validation.json">完整检查</a> · <a href="reports/belly_relayout_validation.json">本次空间与拆装</a> · <a href="reports/commands.json">实际命令</a> · <a href="reports/mass_budget.json">质量惯量</a> · <a href="reports/camera_kinematics.json">相机外参</a> · <a href="reports/purchased_dimensions.md">尺寸来源</a> · <a href="reports/组装与打印.md">组装打印</a> · <a href="reports/打印件审查.md">打印件作用</a> · <a href="reports/外购与自制.md">外购与自制</a> · <a href="reports/export_manifest.json">{ex['exported_count']}件STL</a></p>
<h2 id="parts">全部{len(parts)}件真实预览</h2><p>采购参考、打印候选和未确认预留分别标记；橙色是未知/待选型，不能据此认定实物尺寸。每件完整信息见<a href="reports/bom.json">BOM</a>。</p><input id="filter" placeholder="搜索零件 / PRINTABLE / PURCHASED_REFERENCE / PLACEHOLDER"><div class="grid parts">{partcards}</div></main><dialog id="zoom"><img alt="实际模型放大图"></dialog><script>const d=document.querySelector('#zoom');document.querySelectorAll('img').forEach(i=>i.onclick=()=>{{if(i.closest('dialog'))return;d.querySelector('img').src=i.src;d.showModal()}});d.onclick=()=>d.close();document.querySelector('#filter').oninput=e=>document.querySelectorAll('.part').forEach(p=>p.hidden=!p.dataset.search.toLowerCase().includes(e.target.value.toLowerCase()));</script></html>'''
(ROOT/'index.html').write_text(page)
print('REPORT_COMPLETE',p['revision'],v['counts'])
