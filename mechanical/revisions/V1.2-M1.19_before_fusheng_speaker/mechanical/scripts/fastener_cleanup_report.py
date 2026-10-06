"""User-facing review of the executed M1.15 mounting cleanup."""
import json,html
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def generate(root):
    root=Path(root);p=json.loads((root.parent/'config/geometry.json').read_text());load=lambda n:json.loads((root/'reports'/n).read_text())
    evidence=load('fastener_cleanup_validation.json');bom=load('bom.json');names={a['id']:a['name'] for a in bom};manufacture=load('manufacturing_classification.json');v=load('validation.json')
    assert evidence['revision']==p['revision'] and evidence['status']=='PASS_GEOMETRY_ONLY' and v['counts']['FAIL']==0
    changes=[('固定Yaw承重桥','取消两侧外伸脚与竖向螺丝槽；两个桥脚保持直边，主托板底面两枚M2×8锁入盲孔嵌件。','flush_bridge'),('主托板底面','螺钉头藏在4mm板厚内；两孔在X±45、Y−17，避开电池托盘前侧限位；旧安装位不保留空槽。','flush_bridge_underside'),('扬声器后盖','取消两只外伸耳及侧面长工具槽，改为连续椭圆轮廓、背面两枚沉入式M2×20；仍只固定到上壳。','flush_speaker'),('轮驱底盖','四个孔内收至X±29、Y±23，改为简单倒角平板和沉入式M3螺钉；轴承支座保留。','flush_cap'),('反力轴夹口','取消两块外加凸耳；夹口改为连续圆柱外形，横向螺钉和螺母藏在轮廓内。','flush_reaction')]
    battery=load('battery_retention_validation.json')
    assert battery['revision']==p['revision'] and battery['status']=='PASS'
    ligament=min(r['minimum_closed_ligament_mm'] for r in battery['mounts'])
    changes.extend([('电池托盘侧向固定孔',f'M1.16修复：左右孔心与嵌件由Y20移至Y0，消除沉孔切穿侧板边缘。实测网格孔边连续材料最小约{ligament:.1f}mm；没有增加零件。','battery_retention_detail'),('固定孔内部查看','暂时隐藏螺钉和嵌件，展示完整圆形沉孔；M1.18孔后改由统一厚度侧板提供承压材料，不再伸出局部凸块。','battery_retention_open')])
    power=load('power_board_mount_validation.json')
    assert power['revision']==p['revision'] and power['status']=='PASS'
    changes.extend([('删除长电源托边','两条52mm长凸起改为四个Ø5.6×4.5mm矮座，直接并入原托板；安装孔来自P4原生交接，没有新增打印件。此图隐藏电源包络、承重桥与头部，展示实际支座。','power_seats'),('电源板支撑与固定','两个对角M2×6配两枚试配嵌件锁紧，其余两座承托。橙色仍是容量包络，孔周避让是待硬件核对的元件禁布要求；P5改版和完整装件尚未验证。','power_board_mounted')])
    tray=load('battery_tray_fit.json')
    assert tray['revision']==p['revision'] and tray['status']=='PASS'
    changes.extend([('加宽电池托盘',f'M1.18：托盘外宽90→{tray["width_after_mm"]:.1f}mm，每侧0.3mm试配间隙。电池位置、81mm内通道、软垫和束带位置保留；不增加零件和螺钉。','battery_tray_fit'),('平侧板取消过渡凸块','两处向内伸出的限位螺钉座删除；侧板采用统一3.6mm厚度，原沉孔减浅至1.8mm，孔后仍保留1.8mm材料。底部原有承托台阶接到托盘底面。','battery_frame_flat'),('托盘独立件','底板和两侧直挡边仍为一个简单打印件。只把外侧扩到框架内面附近，原电池内通道不扩大；两枚M2×6仍从左右侧板锁入托盘。','battery_tray_wide')])
    translated={a:'已调整' if r['review'].startswith('Changed:') else '保留必要功能' for a,r in [(r['id'],r) for r in evidence['printed_part_feature_audit']]}
    notes={'Load_Frame':'内侧短折边承接轮驱；PCB座和壳体连接位保留。','Body_Upper':'盲孔支座、接口板座均在壳内，不做外露螺丝耳。','Body_Lower':'壳内缝合座及轴槽保留；轴槽用于下壳拆出，不是螺丝避让。','Head_Front':'保留内侧壳体连接、相机遮光与定位。','Head_Rear':'保留内侧壳缝连接，外面没有安装耳。','Battery_Tray':'保留连续滑轨与侧向限位孔。','Display_Frame':'保留原厂LCD安装柱对应座和短光学角度安装面。','Pitch_Cradle':'保留双侧承重、头壳定位和屏幕侧向连接面。','Pitch_Yoke':'保留双侧轴承、实际舵机耳对应座与应力释放线导。','Mic_Duct_L':'独立麦克风声道，没有螺丝安装凸耳。','Mic_Duct_R':'独立麦克风声道，没有螺丝安装凸耳。','Wheel_Hub_L':'止转孔与端部螺钉均在轮毂轮廓内。','Wheel_Hub_R':'止转孔与端部螺钉均在轮毂轮廓内。','Yaw_Base':changes[0][1],'Speaker_Mount':changes[2][1],'Motor_Retainer':changes[3][1],'Drive_Bridge':'底盖螺钉座移到电机舱角部；外伸部分仅保留轴承承重所需宽度。','Yaw_Reaction_Link':changes[4][1]}
    notes['Load_Frame']='M1.18删除电池限位过渡凸块，统一3.6mm平侧板；底部原台阶承托电池托盘，四个轮驱连接孔原位保留。M1.17电源矮座保留。'
    notes['Battery_Tray']='M1.18外宽94.2mm，配合平侧板；原81mm内通道、包络和束带不变，左右M2×6数量不变。'
    audit='\n'.join(f'| {names[r["id"]]} / {r["id"]} | {translated[r["id"]]} | {notes[r["id"]]} |' for r in evidence['printed_part_feature_audit'])
    text=f'''# MORI {p['revision']} · 安装结构巡检与修改

已检查{len(evidence['printed_part_feature_audit'])}个本体硬质打印件，按用户要求去掉外伸螺丝耳和外侧长工具槽；保留轴承、原厂光学安装、壳内连接和维修分界。数据来自实际总装与逐件检查，不是自动证明所有几何特征的用途。

## 已修改

'''+''.join(f'- **{title}**：{description}\n' for title,description,_ in changes)+f'''
没有新增打印件：本体{manufacture['counts']['robot_print']}件；全机紧固件{manufacture['counts']['fasteners']}件（螺钉{manufacture['screw_count']}、螺母{manufacture['nut_count']}、嵌件{manufacture['insert_count']}、垫圈{manufacture['washer_count']}）。M1.18打印件和五金数量均不变。M1.17给电源板补的两枚螺钉、两枚嵌件保留；此前只有托边，不能将其当作完整固定方案。体积/质量变化见部件表与估重报告。

## 安装与维修

1. 先预装电源板两枚试配嵌件，把板放到四个矮座上，从顶部拧紧两个对角M2×6；再将两枚M2试配嵌件装入承重桥脚底的盲孔，把桥脚放在Load_Frame上，从主托板底面拧入两枚M2×8。该步在安装电池托盘前完成。维修电源板需先禁驱/断电并支撑头部，拆上壳和桥/头组件；桥脚底面螺钉需先断开并取出电池和托盘后操作。
2. 电机底盖四枚M3×25从板底沉孔进入，螺母从上座角部装入。轮驱安装、轴承、轮毂及下壳拆卸顺序延续轮驱接口报告。
3. 喇叭连同上壳取下并断线后，从后盖背面拧两枚M2×20；压紧仍经后盖、喇叭法兰、垫圈传到上壳。后盖不固定在内部承重框架上。
4. 反力轴夹口的螺母从横向口预装，M2×10从对面沉孔拧入。装入头部前先完成舵盘夹紧；舵盘、嵌件和螺纹尺寸均需匹配采购样件。
5. 电池托盘仍用左右各一枚M2×6限位；M1.16内移后的Y0/Z79孔位保留，M1.18螺钉和嵌件沿X适配加宽托盘。底部原有台阶承担竖向载荷，侧向螺钉限制抽出。维修前需支撑、断电并按原顺序移除车轮和壳体，松开两枚限位螺钉后向前抽出；卸托盘后才能操作四个轮驱连接沉孔。

## 检查结果与边界

总检查{v['counts']}。新增检查测了桥脚外面是否平直、螺丝头是否收进轮廓、桥脚螺钉每1mm/20mm及喇叭螺钉每1mm/30mm的装入过程。原有整机静态实体、130组联合头部姿态、轮转一周、轮驱拆卸和工具检查已重新执行。

M1.15的安装特征巡检漏掉了电池固定沉孔的开边：旧孔心距侧板边缘2mm，小于沉孔半径2.3mm。M1.16专门对两侧各180条射线检查孔边连续材料，并检查螺钉头后方实体承压环、25mm螺钉装入和4.2×30mm工具杆；最小闭合孔边约{ligament:.1f}mm。旧模型的同一检查为FAIL，见battery_retention_before.json；当前结果见battery_retention_validation.json。无干涉和网格闭合本身不能证明固定孔有完整支承。

桥脚嵌件孔的名义最薄侧壁约1.3mm，只是候选局部尺寸；需用选定嵌件和打印材料试打、验证抗拔与蠕变，不能作为强度通过结论。后盖密封/声学、全局壁厚、线缆公差、手柄/手指、打印及平衡仍未验证。采购件未缩放、未改电路板源文件。

M1.17实际支座承压环完整，旧长托边中段实体为零；两枚螺钉25mm装入（每1mm）与Ø4.2×30mm工具杆检查通过，电源容量包络向上40mm取出（每2mm）无碰撞。条件是承重桥/头部和上壳尚未安装或已卸下。PCB底面保持Z119.5，预留的3mm底面装件区距离托板1.5mm。孔位来自已交接P4；底面孔周Ø5.8与锁紧孔顶面Ø5.4禁布区是机械要求，P5实际器件必须复核。电源支座嵌件孔名义侧壁1.2mm，两个对角紧固点的抗振、防松与抗拔尚未实测。详见power_board_mount_validation.json。

M1.18对平侧板做40条实际实体射线检查，16组侧间隙和30处底部承托面检查。原M1.17托盘底面与原下折边存在2.5mm空隙，旧的“滑轨承重”描述不能证明实体接触；本次一并修正。当前承托面名义零间隙，等效平面接触面积每侧约{min(tray['equivalent_bearing_area_each_side_mm2']):.0f}mm²，侧面名义0.3mm；这不是打印公差或强度证明。4mm侧板试案曾挡住Yaw工具杆，已拒绝并改为统一3.6mm，无另挖长槽。完整孔边、孔后1.8mm承压材料、螺钉装入、轮驱/Yaw工具路径以及托盘120mm前向抽出均有独立实际几何检查，见battery_tray_fit.json与battery_retention_validation.json。0.3mm滑动配合、嵌件热压、载荷和振动仍需试打与实物验证。

## 逐件巡检

| 打印件 | 处理 | 保留/变更依据 |
|---|---|---|
{audit}

[实际检查JSON](fastener_cleanup_validation.json) · [当前总装](../mori_v1_2.blend) · [所有部件与STL](零件分类与精简建议.md)
'''
    (root/'reports/安装结构巡检与修改.md').write_text(text)
    cards=''.join(f'<figure><a href="renders/{image}.png?revision={p["revision"]}"><img src="renders/{image}.png?revision={p["revision"]}" alt="{html.escape(title)}"></a><figcaption><b>{html.escape(title)}</b><br>{html.escape(description)}</figcaption></figure>' for title,description,image in changes[9:]+changes[7:9]+changes[5:7]+changes[:5])
    section=f'<section id="mounting"><h2>加宽托盘，取消过渡凸块</h2><p>M1.18电池托盘由90加宽到94.2mm，直接配合平侧板，取消两处向内伸出的固定座。底部台阶接到托盘，左右各一枚M2×6限制抽出；零件和螺钉数量不增加。原电源板四矮座与完整电池固定孔边保留。<a href="POWER_BOARD_MOUNT_REQUIREMENTS.md">电源PCB安装要求</a> · <a href="reports/安装结构巡检与修改.md">查看实际网格检查与装配要求</a></p><div class="grid">{cards}</div></section>'
    sheet=Image.new('RGB',(1600,1680),'#26313b');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',23)
    for i,(imname,title) in enumerate([('flush_bridge','STRAIGHT BRIDGE / NO PROJECTING EARS'),('flush_bridge_underside','UNDERSIDE RECESSED MOUNTING'),('flush_speaker','CONTINUOUS SPEAKER COVER'),('flush_cap','INSET CAP SCREWS / FLAT PLATE')]):
        x=i%2*800;y=i//2*840
        with Image.open(root/'renders'/f'{imname}.png') as im:sheet.paste(im.convert('RGB').resize((800,800)),(x,y+40))
        draw.text((x+10,y+7),title,font=font,fill='#e6eef4')
    sheet.save(root/'renders/fastener_cleanup_overview.jpg',quality=94)
    return section
