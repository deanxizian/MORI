"""Manufacturing view of the executed BOM; never a second geometry source."""
from collections import Counter
from pathlib import Path
import hashlib
import html
import json


PRINT_GROUPS = [
    ('外壳', ['Head_Front', 'Head_Rear', 'Body_Upper', 'Body_Lower']),
    ('腹部承重与电池', ['Load_Frame', 'Drive_Bridge', 'Motor_Retainer', 'Battery_Tray']),
    ('头部双轴支撑', ['Yaw_Base', 'Yaw_Reaction_Link', 'Yaw_Turntable', 'Pitch_Yoke', 'Pitch_Cradle']),
    ('光学、声道与线夹', ['Display_Frame', 'Camera_Baffle', 'Mic_Duct_L', 'Mic_Duct_R', 'Pitch_Cable_Clip', 'Body_Top_Shroud']),
    ('扬声器固定', ['Speaker_Mount']),
    ('轮组', ['Wheel_Hub_L', 'Wheel_Hub_R', 'Wheel_Cap_L', 'Wheel_Cap_R', 'Wheel_Coupler_L', 'Wheel_Coupler_R']),
]
OTHER_GROUPS = [
    ('custom_pcb', '自画 PCB · 交给 PCB 厂制作', {'MCU_Carrier', 'Body_IMU', 'Power_Module', 'Rear_Interface_PCB'},
     '运动基板、IMU、电源板及后接口板。不是打印件，也不是现成通用板；P2参考、P3交接及接口板提案的状态仍按原报告。'),
    ('assemblies', '外购电子与机电总成', {'Battery', 'CAM_Mainboard', 'Display_PCB', 'Drive_Motor_L', 'Drive_Motor_R', 'MCU_Motion', 'Pitch_Servo', 'Yaw_Servo', 'Speaker'},
     '按完整电池、板卡、舵机或扬声器采购；这里是模型中的总成数量，尚未执行采购。'),
    ('assembly_details', '上述总成的拆分表示', {'Camera_Lens', 'Camera_PCB', 'Onboard_MIC_L', 'Onboard_MIC_R', 'Pitch_Output', 'Yaw_Output', 'S288_Output_L_Inner', 'S288_Output_L_Outer', 'S288_Output_R_Inner', 'S288_Output_R_Outer'},
     '镜头小板/镜筒、板载双麦克风和舵机输出端。不要按每个对象重复买一套；摄像头是否随具体套餐附带仍需核对。'),
    ('transmission', '轴承、短轴与舵盘', {'Pitch_Bearing_L', 'Pitch_Bearing_R', 'Yaw_Bearing', 'Wheel_Bearing_L_33', 'Wheel_Bearing_L_39', 'Wheel_Bearing_R_33', 'Wheel_Bearing_R_39', 'Pitch_Trunnion_L', 'Pitch_Trunnion_R', 'Wheel_Axle_L', 'Wheel_Axle_R', 'Pitch_Horn', 'Yaw_Horn'},
     '7个轴承、4根短轴、2个舵盘的当前示意。轴承属于采购支撑件；短轴可能需要定长加工；舵盘随件供应或另购待核。不能默认用打印件代替。'),
    ('soft_sheet', '轮胎、软垫与光学片', {'Tire_L', 'Tire_R', 'Battery_Pad_-38.0', 'Battery_Pad_38.0', 'Battery_Pad_Base', 'Motor_Retainer_Pad_-1', 'Motor_Retainer_Pad_1', 'Dock_Pad_0', 'Dock_Pad_1', 'Dock_Pad_2', 'Dock_Pad_3', 'Speaker_Gasket', 'Face_Mask', 'Face_Protector', 'Camera_Window'},
     '软轮胎2、可裁切软垫9、扬声器垫圈1、黑遮罩/透明保护片/相机窗3。轮胎优先另选合适的软胎；TPU只是后续试验方案。4块托架软垫虽标PRINTABLE，但没有混入本次硬质STL。'),
    ('interface_components', '接口板上的待选器件', {'Power_Switch', 'USB_Receptacle'},
     '电源开关和USB-C插座是采购并焊到接口PCB上的器件，不是3D打印件。橙色包络不是已冻结型号。'),
]
PROPOSALS = [
    ('先评估', '两只轮盖 → 轮毂外观面', ['Wheel_Cap_L', 'Wheel_Cap_R'], 2,
     '轮毂直接提供白色外观面，保留轴端装配/锁紧通道；实物轮轴保持方式确认后才能取消独立盖。'),
    ('先评估', '相机遮光框 → 前壳的短安装特征', ['Camera_Baffle'], 1,
     '保留独立相机窗口、遮光内壁和拆装口；白壳内壁须作黑色遮光处理，重新检查视场。'),
    ('先评估', '线夹 → 俯仰U托上的开口线槽', ['Pitch_Cable_Clip'], 1,
     '两者同属yaw运动组；不能把穿线闭环封死，保留线束装入、应力释放和服务环。'),
    ('第二步', '短Yaw转台 + 俯仰U托', ['Yaw_Turntable'], 1,
     '同属yaw组，当前连接使用2枚螺钉和2枚螺母。只有轴承、反力轴、舵盘和舵机仍能顺序装入时，才可省这4个紧固件。'),
    ('第二步', '固定遮光环 → 上壳或固定Yaw座', ['Body_Top_Shroud'], 1,
     '只并入身体固定件，保留旋转间隙、走线与承重桥拆装空间，避免形成深腔大整体。'),
]


def generate(root, revision, bom, previews, exports):
    root = Path(root)
    by_id = {a['id']: a for a in bom}
    preview = {a['id']: a for a in previews}
    stls = {a['id']: a['file'] for a in exports['parts']}
    if len(by_id) != len(bom) or set(preview) != set(by_id):
        raise ValueError('BOM and part previews must have matching unique IDs')
    robot = [n for _, ids in PRINT_GROUPS for n in ids]
    auxiliary = [n for n, a in by_id.items() if a['candidate_stl'] and n not in robot]
    if set(auxiliary) != {'Parking_Cradle', 'Coupon_Insert', 'Coupon_Mating_Tab', 'Coupon_Plane_Fit'}:
        raise ValueError('New printable part needs a manufacturing group')
    if set(stls) != set(robot + auxiliary):
        raise ValueError('Manufacturing print list differs from actual STL export list')
    screws = [n for n in by_id if 'Screw' in n]
    nuts = [n for n in by_id if 'Nut' in n]
    inserts = [n for n in by_id if 'Insert' in n and not n.startswith('Coupon')]
    fasteners = screws + nuts + inserts
    categories = {'robot_print': robot, 'auxiliary_print': auxiliary, 'fasteners': fasteners}
    categories.update({key: sorted(ids) for key, _, ids, _ in OTHER_GROUPS})
    assigned = [n for ids in categories.values() for n in ids]
    if Counter(assigned) != Counter(by_id.keys()):
        raise ValueError('Manufacturing categories must cover every BOM row exactly once')
    m3 = lambda n: n.startswith(('Frame_', 'Shell_'))
    servo_screws = {'Pitch_Lock_Screw', 'Yaw_Lock_Screw'}
    fastener_groups = [
        ('M2普通机螺钉', [n for n in screws if not m3(n) and n not in servo_screws], '当前试配有5/6/8/12mm等长度；长度、头型与伸入量未最终统一。'),
        ('M3机螺钉', [n for n in screws if m3(n)], '框架4枚、身体壳缝4枚；现为光杆包络，未模拟真实螺纹。'),
        ('舵盘中心锁紧螺钉', sorted(servo_screws), '模型按M2占位；应核对舵机原装螺钉的真实牙型和长度，不能直接套用普通M2。'),
        ('M2六角螺母', nuts, '用于轮驱连接、屏幕叉架、Yaw支撑与反力连接等位置。'),
        ('M2热熔嵌件', [n for n in inserts if not m3(n)], '嵌入打印件，供螺钉重复拆装；孔径须按选定嵌件和试打确定。'),
        ('M3热熔嵌件', [n for n in inserts if m3(n)], '框架4枚、身体壳缝4枚；不是打印出来的螺母。'),
    ]
    total_fasteners = sum(len(ids) for _, ids, _ in fastener_groups)
    if total_fasteners != len(fasteners):
        raise ValueError('Fastener grouping mismatch')
    counts = {key: len(ids) for key, ids in categories.items()}
    source_hashes = {name: hashlib.sha256((root/'reports'/name).read_bytes()).hexdigest()
                     for name in ['bom.json', 'parts_preview_manifest.json', 'export_manifest.json']}
    data = {
        'revision': revision, 'scope': 'Classification only; model geometry unchanged',
        'count_basis': 'One BOM object per row, including repeated instances and assembly subgeometry; not a final purchasing BOM',
        'source_sha256': source_hashes, 'counts': counts,
        'screw_count': len(screws), 'nut_count': len(nuts), 'insert_count': len(inserts),
        'categories': categories,
        'fastener_groups': [{'name': label, 'count': len(ids), 'ids': ids, 'note': note} for label, ids, note in fastener_groups],
        'simplification': {'status': 'PROPOSED_NOT_IMPLEMENTED', 'initial_target_printed_pieces': len(robot)-4,
                           'further_conditional_target': len(robot)-6,
                           'proposals': [{'priority': rank, 'proposal': label, 'ids': ids, 'potential_print_reduction': count, 'condition': note}
                                         for rank, label, ids, count, note in PROPOSALS]},
        'limitations': ['Candidate STL is not print qualification', 'Assembly fasteners not yet complete or frozen',
                        'No physical purchasing, slicing, printing, assembly or strength validation performed by this classification']}
    (root/'reports/manufacturing_classification.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    overview = [
        ('机器人本体硬质候选打印件', len(robot)),
        ('外部托架与试打小样', len(auxiliary)),
        ('螺钉/螺母/嵌件', len(fasteners)),
    ] + [(label, len(ids)) for _, label, ids, _ in OTHER_GROUPS]
    md = [f'# MORI {revision} 零件分类与精简建议',
          f'当前部件表有{len(bom)}个对象，其中本体打印件{len(robot)}件、外置托架1件、试打小样3件，合计{len(stls)}个已导出的候选STL。紧固件{len(fasteners)}个，其中螺钉{len(screws)}、螺母{len(nuts)}、嵌件{len(inserts)}。',
          '数量按实物位置计：左右件和每枚螺钉分别算一项。采购总成的麦克风、输出轴、镜筒等也可能单独显示，不应重复采购。此161项清单未把眼睛像素、走线辅助体或旋转轴算作零件。',
          '本报告仅整理当前模型和精简候选，没有修改Blender几何。原有PRINTABLE/PLACEHOLDER字段描述模型状态，与制造分类不是同一件事：橙色螺钉不等于要自行设计或打印。',
          '| 制造/供应分类 | 当前模型对象数 |\n|---|---:|\n' + '\n'.join(f'| {a} | {b} |' for a, b in overview),
          '## 需要3D打印的本体件',
          '以下26件是当前设计的候选件数量，左右件分别计数，并非26种互不相同的工艺。链接直接指向已经导出的装配坐标STL。']
    for label, ids in PRINT_GROUPS:
        md.append(f'### {label} · {len(ids)}件\n\n| 对象 | 作用/名称 | 候选文件 |\n|---|---|---|\n' +
                  '\n'.join(f"| `{n}` | {by_id[n]['name']} | [STL](../{stls[n]}) |" for n in ids))
    md += ['另有独立停放托架1件、试打小样3件。4块托架软垫单列采购/裁切或后续TPU，不算这30件硬质候选STL。',
           '## 常规紧固件',
           '| 当前类别 | 数量 | 说明 |\n|---|---:|---|\n' + '\n'.join(f'| {label} | {len(ids)} | {note} |' for label, ids, note in fastener_groups),
           '这些是已经示意的数量，不是可直接下单的完整整机紧固件清单。LCD、相机、轴端保持及未冻结接口仍可能补充固定件。热熔嵌件与螺母互换一般只是换种类，不能宣传成数量减少。轴承、短轴、舵盘另列，不属于普通螺钉紧固件。',
           '## 可以怎样减少',
           '先评估取消4个独立打印小件，把本体26件收敛到22件；第二步的两处合并都能通过装配和运动复查后，才可能到20件。以上均为尚未实施的候选，不能当作已经完成或验证。',
           '| 顺序 | 合并候选 | 可少打印件 | 条件 |\n|---|---|---:|---|\n'+
           '\n'.join(f'| {rank} | {label} | {count} | {note} |' for rank, label, _, count, note in PROPOSALS),
           '目前优先保留电池托盘、轮驱底盖、扬声器后盖、屏幕叉架和前后/上下壳的维修分界；保留固定反力轴与旋转转台的相对运动。不要为了少件再合成难打印、难装配的大深腔。两条麦克风声道待CAM实板位置核准后再考虑壳内集成，声学通道仍须独立。',
           '## 其他件如何获得']
    for _, label, ids, note in OTHER_GROUPS:
        md.append(f'### {label}\n\n{note}\n\n'+', '.join(f'`{n}`' for n in sorted(ids)))
    md.append('数据来源：当前bom.json、export_manifest.json、parts_preview_manifest.json；哈希和完整分类映射见[manufacturing_classification.json](manufacturing_classification.json)。没有创建第二份尺寸真值源。')
    (root/'reports/零件分类与精简建议.md').write_text('\n\n'.join(md)+'\n')

    esc = html.escape
    def cards(ids, show_stl=False):
        result = []
        for n in ids:
            a = preview[n]
            link = f' · <a href="{esc(stls[n])}">候选 STL</a>' if show_stl and n in stls else ''
            result.append(f'<figure><a href="{esc(a["file"])}"><img loading="lazy" src="{esc(a["file"])}" alt="{esc(a["name"])}"></a><figcaption>{esc(a["name"])}<br><small>{esc(n)}</small>{link}</figcaption></figure>')
        return '<div class="grid parts">'+''.join(result)+'</div>'
    section = [f'<section id="parts"><h2>打印件与采购件 · 按用途查看</h2><div class="note"><b>本体打印 {len(robot)} 件 · 常规紧固件 {len(fasteners)} 个</b><p>原列表的 {len(bom)} 项按模型对象计数，包含每枚螺钉和总成子件；不等于 {len(bom)} 个定制件。紧固件为 {len(screws)} 枚螺钉、{len(nuts)} 枚螺母、{len(inserts)} 个嵌件。当前几何仍为 {esc(revision)}。</p></div>',
               '<p><a href="reports/零件分类与精简建议.md">完整分类与精简建议</a> · <a href="reports/bom.csv">原始BOM</a> · <a href="reports/打印件审查.md">打印审查</a></p>',
               '<h3>本体候选打印件</h3><p>以下全部是已有Blender模型的实际零件渲染。左/右件分别计数；已导出不等于已经切片或可直接投产。</p>']
    for label, ids in PRINT_GROUPS:
        section.append(f'<h4>{label} · {len(ids)}件</h4>'+cards(ids, True))
    section += [f'<details><summary>外部托架与试打小样 · {len(auxiliary)}件</summary>{cards(auxiliary, True)}</details>',
                f'<h3>常规紧固件 · {len(fasteners)}个</h3><table><tr><th>类别</th><th>数量</th><th>当前状态</th></tr>'+''.join(f'<tr><td>{label}</td><td>{len(ids)}</td><td>{note}</td></tr>' for label, ids, note in fastener_groups)+'</table>',
                '<p>这些属于采购五金，无需3D打印。螺纹与长度仍为试配；舵盘中心螺钉须按原厂核准。此数量尚不是完整的最终采购清单。</p>',
                f'<details><summary>展开每一枚紧固件的原模型 · {len(fasteners)}项</summary>{cards(fasteners)}</details>',
                '<h3>精简候选 · 尚未改动几何</h3><p>第一步目标：26 → 22件。优先评估轮盖两件、相机遮光框一件和线夹一件的集成。第二步再评估Yaw转台/U托及固定遮光环，可能收敛到20件。每项仍需重建、装配路径和运动检查。</p>',
                '<table><tr><th>顺序</th><th>合并候选</th><th>可少打印件</th><th>条件</th></tr>'+''.join(f'<tr><td>{rank}</td><td>{label}</td><td>{count}</td><td>{note}</td></tr>' for rank, label, _, count, note in PROPOSALS)+'</table>',
                '<p>电池托盘、轮驱底盖、扬声器后盖与屏幕叉架先保留，便于安装和维修。固定件与转动件不得合并。</p>',
                '<h3>其他采购、板件与材料</h3>']
    for _, label, ids, note in OTHER_GROUPS:
        section.append(f'<details><summary>{label} · {len(ids)}个模型对象</summary><p>{note}</p>{cards(sorted(ids))}</details>')
    section.append('</section>')
    return '\n'.join(section)
