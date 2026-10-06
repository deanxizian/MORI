"""Publish the executed wheel design, evidence and machining-reference handoff."""
from pathlib import Path
import json,html,hashlib,math
from PIL import Image,ImageDraw,ImageFont


def generate(root):
 root=Path(root);project=root.parent;p=json.loads((project/'config/geometry.json').read_text());w=p['wheel_interface'];out=root/'studies/s288_interface_review'
 load=lambda n:json.loads((root/'reports'/n).read_text())
 v=load('wheel_interface_validation.json');d=load('wheel_interface_design.json');bom=load('bom.json');metal=load('wheel_metal_export.json');delivery=load('delivery_consistency.json')
 d['status']=v['status'];d['source_geometry_sha256']=delivery['render_geometry_sha256'];(root/'reports/wheel_interface_design.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 screws=[x for x in bom if 'Screw' in x['id']];nuts=[x for x in bom if 'Nut' in x['id']];inserts=[x for x in bom if 'Insert' in x['id'] and not x['id'].startswith('Coupon')];washers=[x for x in bom if 'Washer' in x['id']]
 count=len(screws)+len(nuts)+len(inserts)+len(washers)
 loadcase=v['load_screening'];gap=v['sweep_minimum']['gap_mm_capped2'];wheelgap=load('wheel_clearance.json')['minimum']['distance_mm']
 body=f'''# MORI {p['revision']} · S288 轮驱连接设计

M1.14 已将原来的转接毛坯和圆轴占位替换成可检查的传动结构；M1.15 进一步将底盖改为简单倒角平板，四个孔内收至 X±29、Y±23，螺钉头沉入底面。当前总装已重新运行实体、转动、工具和拆装检查。**{v['status']}，尚未打印、加工或做实物载荷试验。** M1.13 的零啮合问题仅保留在历史快照中。

## 现在怎么连接

S288 原配输出盘 → 每侧六枚 M2 自攻螺钉 → **一根整体金属法兰轴** → **双扁位打印轮毂** → 软轮胎。轮毂端部用一枚 M3×8 螺钉及平垫圈保持。金属轴和法兰是一个加工件，没有两个零件之间的空接头。

轮载由轮毂、金属轴、每侧两只 686ZZ 轴承、分体轴承座传到承重框架。轴承上座并入 Drive_Bridge，下座并入同一块 Motor_Retainer；共用底盖由四枚 M3×25 和防转螺母固定。电机矩形壳体由上座、底盖及定厚软垫约束，不使用未经确认深度的电机壳体螺孔。夹紧量、回差、软垫蠕变和长期反力承受能力必须实测。

原厂电机输出是短圆盘，**不包含另加的长金属轴**。相机、LCD、头部双轴、板卡和电池位置未随本次轮轴设计移动；轮胎仍为105×18mm、轮心高度52.5mm。

## 关键接口（mm）

| 项目 | 本次设计 / 依据 |
|---|---|
| 旋转轴 | 沿 X，Y=0，Z=52.5；右输出端面 X=27、左端面 X=−27 |
| S288 输出盘 | 原厂 Ø14，两面各突出3；六孔 PCD Ø10.5，Ø1.7 自攻底孔，允许伸入最大3 |
| 六枚输出螺钉 | 厂家兼容 M2 自攻×8的选型要求；法兰厚5.5，名义伸入2.5；头径≤3.8、高≤1.6；不能用普通M2机牙代替 |
| 一体金属轴 | 端面至轴尾45.7；模型轴颈Ø5.98，名义6mm级；钢材候选。法兰背面Ø6×2凹位避让原装中心螺钉，实际螺钉突出量待量 |
| 轴承 | 686ZZ，6×13×5；每侧中心距{w["bearing_centers_abs_x_mm"][1]-w["bearing_centers_abs_x_mm"][0]:g}，X绝对值{w["bearing_centers_abs_x_mm"][0]:g}/{w["bearing_centers_abs_x_mm"][1]:g}；轮心至外轴承20 |
| 内圈轴向堆叠 | 轴肩 X{w["shoulder_end_abs_x_mm"]:g} → 内轴承5 → 金属隔套4.5 → 外轴承5 → 金属隔套10 → 轮毂12.4 → 垫圈0.5 → M3端螺钉 |
| 轮毂止转 | 双扁轴跨平面4.8；孔跨平面4.84、圆弧径6.08为试配模型；轴与孔啮合12.2；端面压紧座比轴尾外伸0.2 |
| 壳体维修 | 轮窝中的轴槽宽10，向上开到壳缝；壳缝螺钉移到 X±22 / Y±71，避开电池托盘和框架螺丝刀路径 |

## 先后顺序

1. 在台面上，将整体法兰轴用六枚厂家匹配的自攻螺钉连接 S288 输出盘。此时尚未装轴承，2.5mm 工具杆可通过轴肩的六个开口。逐步对称紧固、检查同轴；紧固扭矩由样件试验决定。
2. 从轴尾依次套入内轴承、4.5mm金属隔套、外轴承。两套电机/轴/轴承组件从上座下方装入。四枚 M3 螺母先放入上座的防转口，再装共用底盖及 M3×25 螺钉；均匀收紧，检查轴承自由转动，不依靠强拧消除错位。
3. 连接主承重架、板卡和电池，接好可断开的电机线。合壳时，下壳从下方向上套入，轴经开放轴槽就位；不需要先拔出一体轴。之后安装外侧10mm隔套、双扁孔轮毂、平垫圈和 M3×8 端部螺钉。螺纹锁固方式、扭矩及防松效果仍需试配；不能让螺钉顶到盲孔底。
4. 维修时禁轮驱、断开电源并支撑机身：先卸两侧轮毂端螺钉/垫圈，取下轮毂与外隔套，再卸壳缝螺钉，下壳向下取出。电池沿原 +Y 方向取出。若维修电机，再断开其引线、卸四枚共用底盖螺钉，取下底盖，电机/轴/轴承可成组向下取出。请托住松开的零件。

## 打印、采购和加工分开

本体硬质候选打印件 **15件**；M1.14 删除两只打印转接盘，M1.15 没有新增打印件。轮驱相关仍是上座一件、共用底盖一件、左右轮毂两件；下壳沿用维修轴槽。整机另有维护托架1件、试配样块4件，共23个候选 STL。

轮驱使用六孔紧固与四点底盖：当前全机 **{count}件紧固件**，包括螺钉{len(screws)}、螺母{len(nuts)}、嵌件{len(inserts)}、平垫圈{len(washers)}。比 M1.13 的74件增加{count-74}件；M1.15 总数不变，仅承重桥两枚螺母改为嵌件。这些数量按全机实例统计，包含头部未冻结的试配紧固件；不是可直接付款的采购清单。

需要金属加工：整体法兰轴同款2根，OD8/ID6.1×4.5隔套2个、×10隔套2个。可采购通用件：686ZZ轴承4只、匹配的M3螺钉/螺母/垫圈；S288输出必须配原厂兼容自攻牙型。未完成报价，**没有证明总预算≤1000元，也没有下单**。软轮胎仍按单独方案选型/试制，轮胎与轮毂的摩擦保持、粘接或TPU咬合方式未通过试验；不能据此声称整车传动已实机可用。

先打印 Coupon_Wheel_Fit：轴承孔12.9/13.0/13.1，双扁孔6.03×4.79和6.08×4.84；用真实轴承、轴和相同材料/层向选择补偿，再打印轮毂和轴承座。上座可顶板落床，底盖大平面落床、短台阶局部支撑；轮毂外面落床。候选墙厚与切片支撑尚需检查，不通用承诺0.3mm公差。轴颈/内圈台阶的实际配合、粗糙度、同轴度和隔套长度应与已采购轴承匹配后才放行金属加工。

## 已运行的检查

- 输出六孔螺钉沿轴线每1mm进行装入测试，核对头部包络、工具杆与2.5mm名义伸入量。
- 双扁位相对旋转每0.1°查实际实体接触；模型在约±0.7°出现止转接触。它只是名义间隙下的几何回差，不是实测，也不包含电机回差及打印弹性。
- 整套转动件每5°旋转一周，两侧各73姿态，无实体穿透；所列固定件中的最小非轴承间隙约{gap:.2f}mm。轮胎/轮毂对壳体的原检查最小值{wheelgap:.1f}mm；0.49mm局部传动间隙不等于4mm轮壳间隙。
- 下壳90mm、共用底盖45mm、两套电机组件60mm的取出过程每1mm测试，四条路径均通过。线缆插头、人手、工具柄、装配变形没有纳入通过声明。
- 粗算假设总质量1.5kg、3倍竖向载荷：每轮约{loadcase['wheel_radial_load_N']}N，两轴承反力幅值约{loadcase['inner_bearing_reaction_magnitude_N']}/{loadcase['outer_bearing_reaction_magnitude_N']}N。以0.6N·m作峰值筛查，光轴段等效应力约{loadcase['nominal_von_Mises_MPa']}MPa。未含孔、台阶、双扁位应力集中；塑料输出盘、自攻孔、FDM、疲劳和冲击没有强度通过结论，0.6N·m不是连续可用扭矩承诺。

完整证据：[轮驱检查JSON](../../reports/wheel_interface_validation.json)、[全机检查](../../reports/validation.json)、[当前总装](../../mori_v1_2.blend)、[金属设计STEP清单](../../reports/wheel_metal_export.json)、[部件表](../../reports/bom.json)。全局最小壁厚、自交全覆盖、实际线束、选型公差、热/强度/平衡验证继续保留 NOT_TESTED/BLOCKED。

来源：[Unitree S288 原厂手册](https://www.unitree.com/images/%E6%97%A0%E5%88%B7%E6%95%B0%E5%AD%97%E8%88%B5%E6%9C%BAJ288S288%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C.pdf)、[SMB 686ZZ 尺寸资料]({w['bearing_source']})。采用图纸名义尺寸，未取得完整S288 CAD或购买样件测量记录。
'''
 (out/'README.md').write_text(body)
 # Same text with links adjusted for its second, mechanical-report location.
 (root/'reports/S288轮驱连接与加工要求.md').write_text(body.replace('../../reports/','').replace('../../mori_v1_2.blend','../mori_v1_2.blend'))
 views=[('drive_axis','S288、整体金属轴、轴承与轮毂；固定座隐藏以便查看'),('axial_section','实际轴向剖切：金属轴、轴承堆叠、双扁轮毂与端螺钉'),('split_seat','两个打印件：上座与共用底盖；只作展示分离'),('hub_lock','双扁位与端部锁紧的实际局部剖切'),('shell_service','下壳向下22mm的维修姿态；轮子和外隔套已取下')]
 images=''.join(f'<figure><a href="{n}.png?revision={p["revision"]}"><img src="{n}.png?revision={p["revision"]}"></a><figcaption>{html.escape(c)}</figcaption></figure>' for n,c in views)
 check_labels={'wheel_positive_drive_and_axial_stack':'双扁止转与轴向定位','s288_six_hole_flange_installation':'六孔输出连接与螺钉装入','complete_wheel_drive_sweep':'轮驱完整转动采样','wheel_drive_service_sequence':'下壳、底盖和电机拆装路径','wheel_cap_tools':'底盖紧固工具空间','wheel_shell_local_walls':'壳体局部壁厚复核','wheel_drive_strength_and_fit':'实物配合、强度与寿命'}
 status_labels={'PASS':'几何检查通过','NOT_TESTED':'待实物验证'}
 rows=''.join(f'<tr><td>{html.escape(check_labels.get(c["id"],c["id"]))}</td><td>{status_labels.get(c["status"],c["status"])}</td></tr>' for c in v['checks'])
 page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MORI {p['revision']} S288连接设计</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#151b22;color:#e6edf4;font:16px/1.75 system-ui}}main{{max-width:1250px;margin:auto;padding:30px}}h1{{margin:0}}a{{color:#8ddfe9}}.note{{background:#26343f;padding:20px;border-radius:12px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:18px}}figure{{margin:0;background:#28323c;border-radius:12px;overflow:hidden}}img{{width:100%;display:block}}figcaption{{padding:12px}}td{{padding:8px;border-bottom:1px solid #40505d}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}main{{padding:18px}}}}</style><main><h1>S288轮驱连接 · {p['revision']}</h1><p>整体金属法兰轴 · 双独立轴承 · 双扁轮毂 · 共用可拆底盖</p><p><a href="../../mori_v1_2.blend">打开当前Blender总装</a> · <a href="README.md">连接、装配与加工要求</a> · <a href="../../metal_design/Wheel_Axle_Common_DESIGN_REFERENCE.step">金属轴STEP参考</a> · <a href="../../metal_design/wheel_shaft_drawing.svg">名义尺寸图</a> · <a href="../../index.html?revision={p['revision']}#wheel-interface">全机页面</a></p><div class="note">已生成并通过本页规定的几何检查：输出螺钉可装、双扁位能止转、整套转动件无采样穿透、下壳/底盖/电机可按顺序取出。尚未完成金属加工、打印、真实紧固件试配和载荷测试。蓝色为自制金属轴，金色为轴承，配色仅用于看清连接。</div><p>本体硬质打印件15件，本次没有增加。M1.43内轴承外移0.5mm、轴肩延长0.5mm、短隔套改4.5mm；配套STEP与尺寸图已同步。全机紧固件{count}件。预算、原厂自攻螺钉型号及实物配合待确认。</p><div class="grid">{images}</div><p>卸轮毂及外隔套 → 卸壳缝螺钉 → 下壳向下取出 → 断开电机引线 → 卸共用底盖 → 电机/轴/轴承整组取出。壳缝安装位移到X±22 / Y±71以避让托盘及框架工具路径。</p><table>{rows}</table><p>轴向堆叠：一体轴肩 / 5mm轴承 / 4.5mm金属隔套 / 5mm轴承 / 10mm金属隔套 / 双扁轮毂 / 垫圈 / M3端螺钉。轴承内外圈配合、同轴、预紧和塑料输出盘寿命必须用样件验证。</p><p><a href="../../reports/wheel_interface_validation.json">测量与算法JSON</a> · <a href="../../exports/stl/Coupon_Wheel_Fit.stl">试配样块（以导出清单路径为准）</a> · <a href="../../reports/零件分类与精简建议.md">打印/采购/加工分类</a></p></main></html>'''
 (out/'index.html').write_text(page)
 font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22);sheet=Image.new('RGB',(1600,1212),'#202b34');draw=ImageDraw.Draw(sheet)
 for i,(name,title) in enumerate([('axial_section','ACTUAL SECTION / INTEGRAL METAL SHAFT'),('hub_lock','DOUBLE-D HUB / M3 AXIAL RETENTION'),('split_seat','SHARED CAGE + REMOVABLE BEARING CAP'),('shell_service','OPEN AXLE SLOTS / LOWER SHELL REMOVAL')]):
  x=i%2*800;y=i//2*606
  with Image.open(out/(name+'.png')) as im:sheet.paste(im.convert('RGB').resize((800,571)),(x,y+35))
  draw.text((x+12,y+5),title,fill='#eff8fa',font=font)
 sheet.save(out/'design_overview.jpg',quality=94)
 return body

if __name__=='__main__':generate(Path(__file__).resolve().parents[1])
