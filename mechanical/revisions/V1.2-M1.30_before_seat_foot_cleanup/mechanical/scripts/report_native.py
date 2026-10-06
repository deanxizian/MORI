"""Current mechanical delivery page, sourced from executed model/check manifests."""
from pathlib import Path
import json,html,hashlib
from parts_classification import generate as manufacturing_view
from module_report import printing_audit
from animation_page import generate as animation_view
from head_cleanup_report import generate as head_cleanup_view
from drive_cleanup_report import generate as drive_cleanup_view
from head_corner_report import generate as head_corner_view
from head_surface_report import generate as head_surface_view
from head_servo_report import generate as head_servo_view

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda n:json.loads((ROOT/'reports'/n).read_text())
esc=html.escape

def generate():
    p=json.loads((PROJECT/'config/geometry.json').read_text());rev=p['revision'];v=load('validation.json');bm=load('build_manifest.json');ex=load('export_manifest.json');rb=load('rebuild_check.json');dc=load('delivery_consistency.json');g=load('native_electronics_geometry.json');fit=load('native_electronics_validation.json');bom=load('bom.json');part_views=load('parts_preview_manifest.json');motion=load('head_motion.json');mass=load('mass_budget.json');con=load('part_consolidation.json')
    current_bom={r['id']:r for r in bom}
    for preview in part_views:
        row=current_bom[preview['id']]
        preview.update(name=row['name'],category=row['category'],status=row['data_status'])
    (ROOT/'reports/parts_preview_manifest.json').write_text(json.dumps(part_views,ensure_ascii=False,indent=2)+'\n')
    detail_check=load('electronics_detail_validation.json')
    if detail_check['status']!='PASS':raise RuntimeError('Editable PCB derivative failed source comparison')
    animation_section=animation_view(ROOT)
    animation_note=('当前动画 Blender、分步图与 MP4 均已按本页总装更新，含 P5R2 电路板。' if animation_section else '本轮已更新动画Blender与分步图；现有MP4尚未与当前动画核对。')
    animation_readme=('当前装配动画：mori_assembly_animation.blend；视频：animation/MORI_assembly.mp4；分步骤播放：animation/index.html。' if animation_section else '当前装配动画：mori_assembly_animation.blend（现有MP4尚未与当前动画核对）')
    checks={r['id']:r for r in v['checks']};con['robot_print_after']=sum(b['candidate_stl'] and b['group'] not in ['dock','coupon'] for b in bom);con['fasteners_after']=sum(any(x in r['id'] for x in ['Screw','Nut','Insert','Washer']) and not r['id'].startswith('Coupon') for r in bom)
    (ROOT/'reports/part_consolidation.json').write_text(json.dumps(con,ensure_ascii=False,indent=2)+'\n')
    manufacturing_section=manufacturing_view(ROOT,rev,bom,part_views,ex)
    (ROOT/'reports/打印件审查.md').write_text(printing_audit(bom))
    specs=[('运动基板','motion','70 × 35 × 1.6','P5R2：原生板框、全部安装孔、原生装件位置；WeAct 核心另用原厂 CAD'),('IMU 板','imu','20 × 16 × 1.6','P5R2：原生板框/孔/装件；保持刚性安装于托板背面'),('电源板','power','80 × 55 × 1.6','P5R2：装件替换旧容量盒；两只 EEUFR1C102 电容改为 Ø10 × 16'),('后接口板','rear','24 × 25 × 1.6','P5R2：双面装件、开关与 USB 按原生坐标；已适配板框和固定座')]
    table='| 电路板 | 裸板 mm | 当前模型 |\n|---|---|---|\n'+'\n'.join(f'| {a} | {size} | {note} |' for a,k,size,note in specs)
    evidence='''精度分三层：原生 PCB 的板框、孔、位号、位置、转角和安装面来自已交接 KiCad 文件；有原厂 STEP 的模组保留 1:1 原网格；缺 CAD 的封装按原厂尺寸图重建或使用 KiCad 名义库模型。后两者不等于每颗所选料号的实测外形。焊点、涂层公差、全部配对插头和导线折弯仍不完整。几何颜色仅帮助识别材质，绿色不表示已实测或可下单。

电源板的 XT30、保险丝、电感、TPS54302、16mm 电容，以及后板开关和 USB 已补上有尺寸依据的模型。XT30 是保守壳体/焊脚包络，未画成原厂完整接触结构；小封装引脚折弯及壳体倒角有简化。每个元件的 evidence、dimension_basis、limitations 写入独立模型对象与源 JSON。

LCD35079、WeAct V1.1 延用已有原厂 CAD；现有 Pololu D36V50Fx、D24V22Fx 家族原厂 CAD，分别对应硬件任务的 D36V50F9、D24V22F6 工程参考。家族外形不证明电压版本、热能力或额定电流已适配。

CAM33700 仍只有官方37×37板框与32.6mm孔网格可靠；完整装件高度、连接器、双麦精确坐标、FPC和实物厚度缺来源。M1.23建模时核对官方资源页，仅找到原理图与示例，未找到完整装件 STEP，不能用别家 ESP32-S3-CAM 代替。独立3S充电/PD板仍未选定，后接口板本身不是充电器。
'''
    rear=g['rear_mount'];gap=min(r['battery_gap_mm'] for r in fit['buck_mounts']);counts=v['counts'];topology=sum(1 for r in ex['parts'] if r.get('file'))
    feedback=f'''# PCB 机械反馈 · {rev}

当前装配以已接入的 V1.2-H0.5-P5R2 交接为依据。M1.23已同步三颗电阻的位置/方向变更。硬件任务之后的P5R4尚未接入本次装配；这里的反馈针对P5R2，不代表新版PCB仍有同样问题。硬件原文件保持只读。

1. **运动板70×35、IMU20×16、电源板80×55：当前裸装件实体可放入。** 不需要为了这一轮静态装入而缩板。各引脚/装件是否与最终料号完全相同、配对线头及散热仍须核对。
2. **后接口板24×25已装入。** 原生 H1/H2 `(3,11)/(21,11)` 未改动。顶面 Z={rear['board_top_z_mm']:.1f}，底面 Z={rear['board_bottom_z_mm']:.1f}；两枚 M2×6 从底面锁到壳体一体座，嵌件仍为试配。世界映射 `X=12−nativeX；Y=nativeY−75；Z=110.545+STEP_Z`，使用毫米。
3. **开关需要布局反馈。** SOFNG MS-202V-G3 的拨柄前端比 HRO Type-C 口面缩进约 {rear['stem_behind_USB_mouth_mm']:.1f} mm，当前不能从外壳正常拨动。为避免新增长拨杆/打印件，建议硬件任务先评估把 SW1 沿原生 −Y 移约8.8mm，中心从Y12.9改到约Y4.1，使拨柄与USB口面接近。此值是机械修改提案，未修改PCB、未做电气/焊接/布线验收；必须复核背面的USB固定脚、器件公差及开关真实朝向。
4. 两个实际操作轴高差约{rear['switch_actuator_axis_z_mm']-rear['USB_axis_z_mm']:.1f}mm，小于旧操作间距8mm要求。若保留该器件组合，需要实物验证插着USB时能否拨动；移动整板不能改变两个操作轴的高差。外壳当前开孔只用于审查，尚不可冻结加工。
5. 后板J3对插高度接近运动基板，J2在板底侧出。请提供完整配对插头和出线弯曲范围；不能只凭裸插座不穿插认定线束装得下。
6. 两块Pololu降压板已平放到Load_Frame下方、电池上方，最小名义实体距离约{gap:.1f}mm。五个短座并入原托板，共四枚M2×6和四枚试配嵌件。维修须先取出电池/托盘。间距是几何结果，电池附近的发热与电源方案仍待电气任务确认。
7. 请补CAM33700所购版本的完整STEP或实测：板厚、双面最高件、USB/PH/MIC/天线坐标、镜头小板和FPC。还需选定独立充电/PD板与WeAct排母，才能关闭整机电子装配待核项。

硬件文件与 `contracts/components.json` 均保持只读。当前源文件SHA、原生位号、重建尺寸依据分别见 `sources/populated_P5/inventory.json`、`supplement_audit.json` 与 `reports/native_electronics_geometry.json`。孔、模块位置以 `config/geometry.json#/native_electronics` 为当前尺寸来源；旧24×14接口提案已被取代。
'''
    (ROOT/'PCB_LAYOUT_FEEDBACK_M1_23.md').write_text(feedback)
    (ROOT/'INTERFACE_PCB_REQUIREMENTS.md').write_text(feedback+'\n接口装配：拆下上壳、断开线束后，从底部卸两枚螺钉，再向下取出整块板。实际壳座、工具和有限拆出采样见 rear_interface_geometry.json / layout_cleanup_validation.json。没有独立功能键或RESET。\n')
    native_doc=f'''# MORI 电路板模型与精度边界 · {rev}

{table}

{evidence}
安装调整：电源板保留原来的四矮座和两个对角M2×6；后接口板适配真实24×25板框、原生两孔及双面元件；降压板以原孔固定到托板下方。打印件数量不增加，仍为本体{con['robot_print_after']}件。M1.23的降压板固定使用四枚螺钉及四枚试配嵌件，本轮保持。

检查：源文件哈希、1:1导入顶点、四块1.6mm成品板厚、静态实体交集、安装螺钉/工具和指定拆出路径。当前刚性实体穿插{len(load('static_interference.json')['failed_pairs'])}项；全头部{motion['poses']}姿态仍用原总装检查。整机检查统计{counts}，其中BLOCKED/NOT_TESTED均保留，不代表成品通过。

导出：{ex['exported_count']}个独立候选STL已重新导入核对毫米尺寸。电子板不混入打印STL。打印强度、散热、完整线束、实际平衡均未实测。

Blender里查看：`mori_v1_2.blend` 是当前总装；`mori_electronics_detail.blend` 的 `MORI_PCB_Component_Detail` 场景按电路板分集合，四块原生板中的每个已建模位号都是独立对象，坐标与总装相同。对象自定义属性保留证据和未知项。总装对象里也保留按位号命名的顶点组。需要改板时应改原生PCB后重新交接、重新导出，不能只拖动某个3D元件后宣称PCB已同步。

已重新打开详细模型，核对{detail_check['independent_reference_objects_checked']}个拆分对象：顶点与装配变换全部与总装源对象一致，毫米单位和总装来源哈希一致。详见[electronics_detail_validation.json](electronics_detail_validation.json)。此项验证拆分过程，不证明厂家未提供的尺寸。

[需要硬件任务处理的尺寸反馈](../PCB_LAYOUT_FEEDBACK_M1_23.md)

来源：[Waveshare CAM资源](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)、[D36V50Fx尺寸](https://www.pololu.com/file/0J1732/d36v50fx-step-down-voltage-regulator-dimensions.pdf)、[D24V22Fx尺寸](https://www.pololu.com/file/0J1031/d24v22fx-step-down-voltage-regulator-dimension-diagram.pdf)。本地原厂文件和哈希见 sources/populated_P5/vendor/retrievals.json；其他封装厂图来自项目已有硬件资料，只读使用。
'''
    (ROOT/'reports/电路板精细模型.md').write_text(native_doc)
    retained='''
现有非电路板部件继续保留：

| 部件 | 当前依据与状态 |
|---|---|
| 扬声器 | 用户指定福声 FS4545DB0450-H25-R01，厂图箱体45×45×25mm、含耳60mm、孔距52.8mm、2×Ø3.2mm；4Ω5W、31.5±1.5g。原厂耳固定在上壳，未实测声音或装配。 |
| 电池 | Tenergy31013 成品3S候选，名义71×55×20mm、150g；导线、公差、NTC、均衡与充电方案待核。本轮未改成六节18650电池包。 |
| 两侧轮驱 | S288尺寸图和已建六孔接口；金属法兰轴、686ZZ承重轴承、双扁轮毂及端部保持保留。自攻牙型、实配与载荷未验收，详见S288轮驱连接与加工要求.md。 |
| 头部舵机 | SCS0009×2按尺寸图，承重环与双侧俯仰支撑保留；舵盘、公差、实际持续载荷待验证。 |
| 麦克风 | CAM33700原板双麦，不另购独立模块，无打印导管；精确进声坐标与声学效果待实板确认。 |
| 轮胎、光学保护片与紧固件 | 采购/加工方案及试配尺寸依各对象标记，普通五金不是打印件。厂家名义尺寸不等于已实测。 |

原有厂图文件和哈希保留在contracts/mechanical_interfaces.json。电气选型、原生PCB和采购预算仍由硬件任务维护；机械侧不下采购或制造订单。
'''
    for n in ['采购件选型.md','purchased_dimensions.md','设计与选型分工.md','外购与自制.md']:(ROOT/'reports'/n).write_text(native_doc+retained)
    assembly=f'''# 组装与打印 · {rev}

本体{con['robot_print_after']}个候选打印件，另有停放托架1件、小样4件。电路板元件不是打印件；普通五金见[零件分类](零件分类与精简建议.md)。本轮不增加打印件与紧固件；M1.23已加入的4枚降压板M2螺钉和4枚试配嵌件继续保留，总计{con['fasteners_after']}个已示意紧固件。

1. 台面预装IMU、两块降压板到Load_Frame底面，再接合轮驱框架。四个降压板螺钉均从底面操作；装电池前完成。材料强度、热量和实际线束未验收。
2. 运动基板P5R2、WeAct原厂模组以及P5R2电源板由顶部装入；电源板四个矮座承托、两枚对角M2×6保持。WeAct排母仍是6mm安装高度假设，须选型确认。
3. 保留M1.22承重桥插接、两侧M3×8配金属螺母；轮子卸下才能从侧面拧紧，电池托盘可保留。桥与头部先于封壳安装。
4. 电池和托盘沿既定前向路径放入，侧向M2限位。显示/相机独立上仰10°，头壳机械零位水平；双轴、承重环、服务环和原有支撑关系不变。
5. 扬声器与后接口板在拆下的上壳上预装。P5R2后板从底面贴到两个壳体一体座，再从下方锁M2×6；当前开关深度/插线操作仍待PCB改版，外壳开孔不可用于最终加工。
6. 接入可断开线束、合壳、安装车轮。托架使用时必须禁轮驱；几何支撑不代表断电自立。

打印仍只交付候选：先验证嵌件、轴承、轴孔、平面配合缝及新增PCB座小样。没有进行切片、打印、抗拔、疲劳、热测试或实机平衡。不要把0.3mm试配值推广为通用公差。新增降压板座位于主托板底面；打印方向和局部支撑由切片验证。源网格拓扑与STL回读报告见export_manifest.json。
'''
    if p.get('head_servo_detail',{}).get('enabled'):
        assembly=assembly.replace('本轮不增加打印件与紧固件；','本轮不增加打印件；两只舵机各用两枚M2×5和两枚试配嵌件，俯仰耳座新增四件五金，原Yaw两枚螺母改为嵌件。')
        assembly=assembly.replace('双轴、承重环、服务环和原有支撑关系不变。','双轴和独立承重轴承保留。走线、服务环和应力释放留待后续设计，预估线束已隐藏。')
        assembly=assembly.replace('6. 接入可断开线束、合壳、安装车轮。','6. 空U托上先装四枚试配嵌件，Pitch舵机从中央沿−X装入并锁两耳，再从上方装倒置Yaw舵机并锁两耳；最后装头托和光学件。舵盘仍是占位，实际啮合与零位待所购件确认。\n7. 完成后续线束设计与验证后，再接线、合壳、安装车轮。')
    for n in ['组装与打印.md','结构简化说明.md']:(ROOT/'reports'/n).write_text(assembly)
    report=f'''# MORI {rev} 当前机械交付

已实际建立、验证和渲染原生PCB装件模型；当前总装保留M1.22的承重桥与短Yaw限位。

{table}

{evidence}
实际检查{counts}；静态穿插{len(load('static_interference.json')['failed_pairs'])}项；候选STL {ex['exported_count']}/{ex['candidate_count']}；重复生成{rb['status']}；当前输入/渲染/STL一致性{dc['status']}。Blender{bm['blender']}，KiCad10.0.6。完整命令见commands.json和sources/populated_P5/export_commands.json。

必须继续处理后接口板开关可操作性、配对插头/走线、CAM完整资料、排母和充电板选型。详见[PCB反馈](../PCB_LAYOUT_FEEDBACK_M1_23.md)。不能把裸装件通过当成整机已可制造。

生成：主模型、逐位号详细模型、当前装配动画Blender、实际渲染、部件表和候选STL。
通过的项目及条件见[validation.json](validation.json)，完整来源见[电路板模型报告](电路板精细模型.md)。打印、载荷、热与实机平衡仍未实测。

| 检查 | 状态 | 内容 |\n|---|---|---|\n'''+ '\n'.join(f"| {x['id']} | {x['status']} | {x['summary']} |" for x in v['checks'])
    (ROOT/'reports/REPORT.md').write_text(report+'\n')
    (ROOT/'README.md').write_text(f'''# MORI {rev}

[当前预览](index.html) · [电路板精度与来源](reports/电路板精细模型.md) · [PCB尺寸反馈](PCB_LAYOUT_FEEDBACK_M1_23.md)

- 总装：mori_v1_2.blend
- 逐位号编辑：mori_electronics_detail.blend
- {animation_readme}
- 共享尺寸：../config/geometry.json；接口：../contracts/mechanical_interfaces.json

重新生成模型与候选输出：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/render.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/export.py
```

原生PCB更新后，先运行prepare_populated_pcbs.py inventory/export（KiCad Python），再运行convert_populated_pcbs.py和supplement_populated_pcbs.py（OCP Python），检查差异并重新验证。不得修改硬件原件以匹配机械旧孔。详细来源/已执行命令见reports/commands.json。

{counts}；几何不等于制造放行。后接口开关、CAM完整装件、配对插头、排母和独立充电板仍待处理。各轮机械快照保留在revisions/。
''')
    def gallery(items):return '<div class="grid">'+''.join(f'<a class="card" href="renders/{key}.png"><img loading="lazy" src="renders/{key}.png?revision={rev}" alt="{esc(title)}"><h3>{esc(title)}</h3></a>' for key,title in items)+'</div>'
    rows=''.join(f'<tr><td>{esc(a)}</td><td>{size}</td><td>{esc(note)}</td></tr>' for a,k,size,note in specs)
    head=f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI {rev} · 机械装配预览</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#eef0ed;color:#1c2928;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:1240px;margin:auto;padding:34px 28px 90px}}nav{{display:flex;gap:22px;flex-wrap:wrap;border-bottom:1px solid #cbd4cc;padding-bottom:18px;position:sticky;top:0;background:#eef0edf2;z-index:2}}a{{color:#216556;text-decoration:none}}h1{{font-size:44px;line-height:1.2;letter-spacing:-1px}}h2{{font-size:27px;margin-top:55px}}h3{{font-size:16px;margin:14px 16px}}.kicker{{font-size:12px;letter-spacing:2px;color:#5b7469}}.intro{{font-size:19px;max-width:860px}}.notice{{background:#fff7dd;border:1px solid #e1cea0;padding:18px 22px;border-radius:12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}.card{{background:#fff;border:1px solid #d4dcd6;border-radius:14px;overflow:hidden;color:inherit}}.card img{{width:100%;display:block}}table{{width:100%;border-collapse:collapse;background:#fff}}td,th{{padding:13px 16px;border:1px solid #d4dcd6;text-align:left}}.links{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}.links a{{padding:9px 16px;background:#fff;border:1px solid #bbcec4;border-radius:8px}}small{{color:#5b6b63}}@media(max-width:700px){{main{{padding:22px 16px}}h1{{font-size:32px}}.grid{{grid-template-columns:1fr}}table{{font-size:13px}}}}</style><main><nav><b>MORI / {rev}</b><a href="#electronics">电路板</a><a href="#structure">内部安装</a><a href="#appearance">外观</a><a href="#views">全部视图</a><a href="parts.html">全部零件</a><a href="#checks">检查与文件</a></nav><p class="kicker">NATIVE PCB · SOURCE CAD · ACTUAL BLENDER RENDERS</p><h1>电路板已按原生布局装入。</h1><p class="intro">四块自绘板替换为实际板框、安装孔和装件；保留原厂 LCD、WeAct，补入两块降压板。逐个元件可以在 Blender 里选中核对。</p><div class="links"><a href="mori_v1_2.blend">总装 Blender</a><a href="mori_electronics_detail.blend">逐位号详细 Blender</a><a href="reports/电路板精细模型.md">精度与来源</a><a href="PCB_LAYOUT_FEEDBACK_M1_23.md">PCB 修改反馈</a></div><div class="notice"><b>尚未冻结加工：</b>后接口板的开关拨柄比 USB 口面缩进约{rear['stem_behind_USB_mouth_mm']:.1f}mm，外部操作仍需调整；CAM 完整装件、配对插头、排母和独立充电板资料未齐。绿色元件和“无穿插”都不表示实物已验证。</div>'''
    page=head+'<section id="electronics"><h2>原生电路板</h2><p>板框和放置来自 P5R2。封装注明原厂CAD、库模型或尺寸图重建，不用未知细节冒充实测。</p><table><tr><th>电路板</th><th>裸板 mm</th><th>建模依据</th></tr>'+rows+'</table>'+gallery([('pcb_power','电源板 P5R2 · 实际装件'),('pcb_motion','运动基板 P5R2 + WeAct'),('pcb_imu','IMU P5R2 · 器件朝下'),('pcb_rear','后接口板 P5R2 · 顶面开关'),('pcb_rear_bottom','后接口板 P5R2 · 底面 USB-C'),('pcb_bucks','两块 Pololu · 原厂家族 CAD')])+'</section>'
    page+='<section id="structure"><h2>实际安装位置</h2><p>两块外置9V/6V降压板落在主托板背面，与电池最近约'+f'{gap:.1f}mm'+'。五个固定座并入现有托板；四枚螺钉与四枚嵌件是五金，不是打印件。后接口板原生两孔对应壳体一体座。M1.22 的承重桥接合保持。</p>'+gallery([('electronics_bay','电路板与主托板'),('electronics_underside','托板背面 · IMU 与两块降压板'),('rear_interface_detail','后接口板与上壳安装座'),('bridge_joint_detail','保留的插接＋横向 M3 接合')])+'</section>'
    page+='<section id="appearance"><h2>同一套总装外观</h2>'+gallery([('45_assembled','45°总装'),('rear','后视 · 接口开孔仍待确认')])+'</section><section id="views"><h2>检查视图</h2>'+gallery([('front','正视'),('side','侧视'),('top','顶视'),('bottom','底视'),('internal','内部布局'),('head_section','双轴头部剖视'),('exploded','分解展示 · 导出仍用装配坐标'),('clearance','离地与轮壳间隙')])+'</section>'
    page+=f'''<section id="mounting"><h2>安装与打印</h2><p>当前本体{con['robot_print_after']}个候选打印件，{con['fasteners_after']}个已示意紧固件。电子板不在STL导出中；CAD总成内的元件也不应重复采购。先装托板底面电路，再装板卡与承重桥，最后接入可断开线束并合壳。</p><div class="links"><a href="manufacturing.html">打印件与常规五金</a><a href="reports/组装与打印.md">组装顺序</a><a href="mori_assembly_animation.blend">当前 Blender 装配动画</a></div><small>动画是顺序讲解，未证明全程无干涉。本轮更新动画Blender与分步图，旧MP4仍属于M1.22。</small></section><section id="checks"><h2>实际检查结果</h2><p>{counts['PASS']} PASS · {counts['FAIL']} FAIL · {counts['BLOCKED']} BLOCKED · {counts['NOT_TESTED']} NOT_TESTED。静态实体检测到的穿插为{len(load('static_interference.json')['failed_pairs'])}项；全头部{motion['poses']}姿态为有限采样。{ex['exported_count']}个候选STL已回读单位/尺寸。重复生成{rb['status']}，输入/渲染/导出一致性{dc['status']}。</p><p>这里的结果以名义模型为范围。完整CAM、配对插头、焊接与公差、散热、打印强度和实机平衡仍未通过。</p><div class="links"><a href="reports/REPORT.md">完整报告</a><a href="reports/validation.json">检查明细</a><a href="reports/native_electronics_validation.json">PCB专项检查</a><a href="reports/commands.json">执行命令</a><a href="reports/export_manifest.json">STL清单</a><a href="reports/bom.csv">部件表CSV</a></div><small>工具：Blender{bm['blender']} / KiCad10.0.6。所有图均来自实际Blender网格，无生成式概念图。原生电路文件保持只读；当前模型未宣称任何尺寸经过实测。</small></section></main></html>'''
    page=page.replace('本轮更新动画Blender与分步图，旧MP4仍属于M1.22。',animation_note)
    if animation_section:
        page=page.replace('<section id="checks">',animation_section+'<section id="checks">')
        page=page.replace('<a href="parts.html">全部零件</a>','<a href="parts.html">全部零件</a><a href="#animation">装配动画</a>')
    head_cleanup_section=head_cleanup_view(ROOT)
    if head_cleanup_section:
        page=page.replace('<section id="electronics">',head_cleanup_section+'<section id="electronics">')
        page=page.replace('<a href="#electronics">电路板</a>','<a href="#head-cleanup">头部简化</a><a href="#electronics">电路板</a>')
        page=page.replace('电路板已按原生布局装入。','头部打印支架已简化。')
        page=page.replace('四块自绘板替换为实际板框、安装孔和装件；保留原厂 LCD、WeAct，补入两块降压板。逐个元件可以在 Blender 里选中核对。','取消旧声道高耳，理顺屏幕侧接和转台底座；器件位置与双轴运动保持。总装、独立候选 STL 和装配动画使用同一套几何。')
    drive_cleanup_section=drive_cleanup_view(ROOT)
    if drive_cleanup_section:
        page=page.replace('<section id="head-cleanup">',drive_cleanup_section+'<section id="head-cleanup">')
        page=page.replace('<a href="#head-cleanup">头部简化</a>','<a href="#drive-cleanup">轮驱简化</a><a href="#head-cleanup">头部简化</a>')
        page=page.replace('头部打印支架已简化。','轮驱支架的凸条与台阶已简化。')
        page=page.replace('取消旧声道高耳，理顺屏幕侧接和转台底座；器件位置与双轴运动保持。总装、独立候选 STL 和装配动画使用同一套几何。','轮驱上座改为连续平面侧壁，共用底盖改为平板与连续轴承座。两个打印件原位修改，保持电机、金属传动、紧固件和电路板位置；总装、候选 STL 与装配动画已同步。')
    corner_section=head_corner_view(ROOT)
    if corner_section:
        page=page.replace('<section id="drive-cleanup">',corner_section+'<section id="drive-cleanup">')
        page=page.replace('<a href="#drive-cleanup">轮驱简化</a>','<a href="#head-corners">头托折角</a><a href="#drive-cleanup">轮驱简化</a>')
        page=page.replace('轮驱支架的凸条与台阶已简化。','头托恢复连续大折角。')
        page=page.replace('轮驱上座改为连续平面侧壁，共用底盖改为平板与连续轴承座。两个打印件原位修改，保持电机、金属传动、紧固件和电路板位置；总装、候选 STL 与装配动画已同步。','后横板与左右侧板通过两段等厚斜壁连接，恢复旧版大折角轮廓。总装、候选 STL 与装配动画已同步。')
    surface_section=head_surface_view(ROOT)
    if surface_section:
        page=page.replace('<section id="head-corners">',surface_section+'<section id="head-corners">')
        page=page.replace('<a href="#head-corners">头托折角</a>','<a href="#head-surfaces">表面修正</a><a href="#head-corners">头托折角</a>')
        page=page.replace('头托恢复连续大折角。','头部平面的假折皱已修正。')
        page=page.replace('后横板与左右侧板通过两段等厚斜壁连接，恢复旧版大折角轮廓。总装、候选 STL 与装配动画已同步。','结构平面按实际法线显示，孔边与曲面保持平滑。真实壁厚、孔位和大折角几何保持；Blender、预览及装配动画已同步。')
    servo_section=head_servo_view(ROOT)
    if servo_section:
        page=page.replace('<section id="head-surfaces">',servo_section+'<section id="head-surfaces">')
        page=page.replace('<a href="#electronics">电路板</a>','<a href="#head-servos">小舵机</a><a href="#electronics">电路板</a>')
        page=page.replace('头部平面的假折皱已修正。','小舵机与固定座已重建。')
        page=page.replace('结构平面按实际法线显示，孔边与曲面保持平滑。真实壁厚、孔位和大折角几何保持；Blender、预览及装配动画已同步。','SCS0009安装耳接回壳体，耳座高度与输出端按厂图纠正；固定座简化，预估线孔和线夹撤掉。走线延后，现有舵盘仍待实物配合确认。')
    (ROOT/'index.html').write_text(page)
    anim=load('../animation/manifest.json');ap='<h1>MORI '+rev+' · Blender 装配动画</h1><p>本轮更新可编辑动画与18张分步渲染；现有MP4尚未与当前关键帧核对，本页暂不将其作为当前视频展示。</p><a href=../mori_assembly_animation.blend>当前动画 Blender</a><p>动画仅作顺序讲解；未验证连续装配路径、手部和真实线束。</p>'+''.join(f'<figure><img style="width:100%;max-width:800px" src="step_{z["index"]:02d}.png?revision={rev}"><figcaption>{z["index"]:02d} · {esc(z["title"])} · {esc(z["note"])}</figcaption></figure>' for z in anim['stages'])
    if not animation_section:
        (ROOT/'animation/index.html').write_text('<!doctype html><html lang=zh><meta charset=utf-8><title>MORI 当前装配步骤</title><style>body{max-width:1000px;margin:30px auto;padding:20px;font:16px/1.7 system-ui;background:#eef0ed;color:#234}figure{margin:25px 0}a{color:#216556}</style><a href=../index.html>返回总装</a>'+ap+'</html>')
    basic='<!doctype html><html lang=zh><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><style>body{font:16px/1.7 system-ui;margin:24px;background:#eef0ed;color:#234}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}figure{background:white;margin:0;padding:14px;border-radius:10px}img{width:100%}td,th{padding:10px;border:1px solid #ccd}a{color:#216556}input{padding:12px;width:min(500px,90%)}main{max-width:1250px;margin:auto}</style><main><a href=index.html>← MORI 当前总装</a>'
    (ROOT/'manufacturing.html').write_text(basic+manufacturing_section+'</main></html>')
    cards=''.join(f'<figure data-search="{esc(a["id"]+a["name"]+a["category"])}"><a href="{esc(a["file"])}"><img loading=lazy src="{esc(a["file"])}?revision={rev}"></a><figcaption>{esc(a["name"])}<br><small>{esc(a["id"])} · {esc(a["category"])}</small></figcaption></figure>' for a in part_views)
    (ROOT/'parts.html').write_text(basic+f'<h1>{rev} · 全部{len(part_views)}个对象</h1><p>对象数不等于采购件数或打印件数。电子总成不要按芯片重复采购。</p><input id=search placeholder="搜索零件名称 / PRINTABLE"><div class=grid>'+cards+'</div></main><script>document.getElementById("search").oninput=e=>document.querySelectorAll("figure").forEach(f=>f.hidden=!f.dataset.search.toLowerCase().includes(e.target.value.toLowerCase()))</script></html>')
    (ROOT/'reports/电子模型来源完整性.json').write_text(json.dumps({'revision':rev,'native_sources_unchanged':all(r['sha256_matches'] for r in fit['sources']),'counts':counts,'renderer':'actual Blender','sources':fit['sources'],'unknown':fit['unknown']},ensure_ascii=False,indent=2)+'\n')
    print('NATIVE_REPORT_COMPLETE',rev,flush=True)

if __name__=='__main__':generate()
