"""Publish the user-selected CAM support repair and bounded whole-print audit."""
import json,html,hashlib
from pathlib import Path

def publish(root,rev,current_report):
    load=lambda p:json.loads(p.read_text())
    study=root/'studies/mount_root_cleanup';a=load(study/('audit_'+rev.replace('.','_')+'.json'));before=load(study/'audit_V1_2-M1_39.json');v=load(root/'reports/mount_root_validation.json');whole=load(root/'reports/validation.json');motion=load(root/'reports/head_motion.json');mic=load(root/'reports/microphone_open_path.json');bom=load(root/'reports/bom.json');delivery=load(root/'reports/delivery_consistency.json')
    assert v['status']=='PASS' and not a['root_failures'] and not whole['counts']['FAIL'] and mic['status']=='PASS' and delivery['status']=='PASS'
    functions=[
     ('Pitch_Cradle','CAM上两座根部曾偏出31mm后板；改44mm平直板和四个方座，两个进声孔保持原通路。侧壁、折弯角、转轴孔和头壳耳座保持。','本轮修复'),
     ('Load_Frame','4处运动基板、2处IMU、4处电源板、5处9V/6V模块座根部均完整落在托板实体内；保留短座以留元件间隙。','根部实体探针通过'),
     ('Pitch_Yoke','两轴舵机耳座、后连接臂、两侧轴承壁与本体连续；保留已确认穿栓螺母、承重轴承台肩和运动限位。','源轮廓/连续实体/既有耳座检查通过'),
     ('Display_Frame','屏幕三座和相机捕获槽为定位/锁紧接口；下横板已整条加深、前移，不能删掉必要承压面。','既有承压、装板及联合姿态检查通过'),
     ('Yaw_Base','两脚插接舌与横向M3连接、轴承肩和短限位块都有对应功能；不恢复外伸螺丝耳或工具槽。','插接与承压专项通过'),
     ('Yaw_Reaction_Link','圆形夹头与直杆是固定反力路径；端部夹缝和紧固孔保留，未见孤立凸块。','源轮廓及单一实体检查通过'),
     ('Drive_Bridge','电机/轮轴轴承座与连续箱壁结合，四个底盖螺钉列已并入箱壁。','既有连接截面及底盖取出检查通过'),
     ('Motor_Retainer','共用平底盖和必要半圆轴承鞍座保留；此前右侧1.5mm窄边已删除。','局部差分及轴承支承检查通过'),
     ('Battery_Tray','两侧壁、平底、绑带槽和侧向限位孔保留；没有重新加入内伸小托边。','托盘承托及带电池抽出采样通过'),
     ('Body_Upper','喇叭与后接口板座直接连壳；其径向材料与嵌件最终规格仍需定型，不据根部连续声称强度合格。','根部源轮廓/既有拆卸路径检查；嵌件选型BLOCKED'),
     ('Body_Lower','壳体内部拼接座和轴孔边缘保持，连续连接到曲面壳壁。','源轮廓与单一实体检查通过'),
     ('Head_Front','LCD黑圈、相机限位唇和拼缝座均有功能；拼缝嵌件规格仍需定型。','源轮廓/相机捕获检查；嵌件选型BLOCKED'),
     ('Head_Rear','拼缝固定座、壳孔与切口是固定和装入接口。未检出同类窄搭接柱端。','源轮廓及壳体装入检查通过'),
     ('Wheel_Hub_L','轴孔双D止转和轴端螺钉沉入为轮轴接口；轴承/输出螺钉属于金属采购件。','既有轮轴配合/360°旋转采样通过'),
     ('Wheel_Hub_R','与左轮相同的必要止转/轴端保持结构；没有新增外盖或支撑耳。','既有轮轴配合/360°旋转采样通过')]
    assert {r[0] for r in functions}=={r['id'] for r in a['all_15_prints']}
    audit={'revision':rev,'scope':'15robot prints;19board-seat root-footprints;34current insert sites; source/function review and finite current solid checks','printed_part_review':[dict(id=x,review=y,result=z) for x,y,z in functions],'before_root_failures':before['root_failures'],'after_root_failures':a['root_failures'],'root_evidence':str((study/('audit_'+rev.replace('.','_')+'.json')).relative_to(root)),'limits':'Root footprint probes are not stress/strength tests or an exhaustive global defect algorithm. Common-insert wall screening is compatibility evidence for an unselected reference, not a pass/fail of purchased hardware.'}
    (root/'reports/mount_root_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    oldfails=[r for r in before['root_footprint_checks'] if r['status']=='FAIL']
    table='| 打印件 | 排查结果 | 保留/修复依据 |\n|---|---|---|\n'+'\n'.join(f'| {x} | {z} | {y} |' for x,y,z in functions)
    details=f'''# 安装座根部修复与排查 · {rev}

用户选择A：平直后板＋两个进声孔。CAM背板由31mm加宽到44mm，四个Ø5.6短圆座整理为5.6×5.6mm方座，全端面接入后板；保留板后5.66mm名义空间、32.6mm孔网格、四枚M2×6及原试配嵌件。只改Pitch_Cradle一件，其他零件逐个网格/位姿哈希保持；没有新增打印件、五金或走线孔。进声孔沿原名义路径，实际端口和声学仍待样件确认。

19处板卡座的根部材料检查，原来只有CAM_1/CAM_3不完整：去除中心孔后的环形截面承接比例约{oldfails[0]['material_fraction']*100:.1f}%。这不是强度百分比。其他17处没有同类根部越界；本版CAM四座按完整矩形端面检查，均100%有背板材料。当前15件打印件均为单一连续实体。

本轮还逐件查看功能与局部轮廓，结果如下。没有把所有凸起都当成缺陷删除；轴承肩、舵机耳座、屏幕座、壳体内固定座和装配分件有对应功能。

{table}

对34处现存嵌件座另做径向材料筛查。若直接换成此前FINE参考规格，多处仍不满足其包边要求，涉及电源/降压模块、后接口板、喇叭和头壳拼缝等。这里是**未选定嵌件的兼容性问题**，并非此次CAM柱根越界；需要先确定真实嵌件尺寸再改孔/座。当前试配嵌件与孔没有擅自放大，不能称所有固定接口已定型。完整数据见[根部与嵌件筛查](../{audit['root_evidence']})。

实际模型检查：{whole['counts']['PASS']} PASS / {whole['counts']['FAIL']} FAIL；{motion['poses']}个名义头部联合姿态未检出穿插。CAM装板61个位置、4支螺丝刀直杆、原双麦进声路径通过；完整采购件资格仍受照片估计、舵盘与螺纹代理等限制。重复生成及外部对象保留、毫米STL回读、主模型与装配动画几何一致性已检查。PA12打印件仍15件、紧固件对象仍129个。有限几何检查不证明强度、疲劳或实物装配。

文件：[当前Blender](../mori_v1_2.blend) · [修复专题](../studies/mount_root_cleanup/index.html) · [局部验证](mount_root_validation.json) · [全部验证](validation.json) · [命令/日志](mount_roots_commands.json)。没有制造放行或订单。
'''
    (root/'reports'/current_report).write_text(details)
    (root/'reports/REPORT.md').write_text(details)
    (study/'README.md').write_text(details)
    cards=lambda entries: '<div class="grid">'+''.join(f'<figure><img src="{path}?revision={rev}"><figcaption>{html.escape(title)}</figcaption></figure>' for path,title in entries)+'</div>'
    style='<style>body{font:16px/1.7 system-ui;margin:30px auto;max-width:1100px;padding:20px;background:#edf0ed;color:#20312c}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;background:white}img{width:100%;display:block}figcaption{padding:12px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cad2cd;padding:10px;text-align:left}a{color:#17694f}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>'
    section='<section id="mount-roots"><h2>CAM安装座已修复</h2><p>按确认的A方案：44mm平直后板、四个方形短座、两个功能进声孔。孔位和硬件保持，没有增加零件。</p>'+cards([('studies/mount_root_cleanup/after_rear.png','当前后视：完整连接、平直轮廓'),('studies/mount_root_cleanup/after_front.png','当前装板：四孔及板后空间保持')])+f'<p>排查15件打印件和19处板卡座根部；同类问题仅见CAM上两座，现已修复。其余嵌件规格仍需定型，不能把几何检查当作强度通过。</p><p><a href="reports/{current_report}">逐件排查记录</a> · <a href="studies/mount_root_cleanup/index.html">修复前后比较</a></p></section>'
    page=(root/'index.html').read_text().replace('舵机改穿栓螺母，<br>相机采用连续椭圆扩口。','CAM固定座完整接入后板，<br>排查其他安装座。').replace('<section id="prearrival">',section+'<section id="prearrival">').replace('<nav><b>','<nav><a href="#mount-roots">本轮修复</a><b>')
    (root/'index.html').write_text(page)
    rows=''.join('<tr><td>'+html.escape(x)+'</td><td>'+html.escape(z)+'</td><td>'+html.escape(y)+'</td></tr>' for x,y,z in functions)
    study_page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+style+f'<a href="../../index.html?revision={rev}#mount-roots">返回当前总装</a><h1>{rev} · 安装座根部修复</h1><p>原31mm后板未完整承接32.6mm孔距的上侧圆座；现为44mm平直后板和方座，两个进声孔沿原路径。打印件、孔位和硬件数量保持。</p>'+cards([('before_rear.png','修复前：座中心偏出后板'),('after_rear.png','修复后：端面完整承接'),('after_front.png','当前CAM安装'),('deck_bottom.png','复查托板底面的IMU和降压模块短座')])+f'<h2>15件打印件排查</h2><table><tr><th>零件</th><th>结果</th><th>功能依据</th></tr>{rows}</table><p><a href="../../reports/{current_report}">完整审查及未完成接口</a> · <a href="../../reports/mount_root_validation.json">本轮实体检查</a></p><p>19处根部材料检查全部通过；34处嵌件座仍需匹配真实规格。PA12强度、音频、实际公差及动态性能未验证。没有制造放行。</p></html>'
    (study/'index.html').write_text(study_page)
    progress=load(root/'reports/assembly_completion_progress.json');progress['rows'].insert(0,{'item':'CAM座根与类似问题排查','status':'本轮修复/有限几何检查完成','detail':'44mm平直后板＋两个进声孔；四方座全端面接入。15件打印件、19处座根已查；嵌件规格继续待定。'});(root/'reports/assembly_completion_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
    print('MOUNT_ROOT_REPORT_COMPLETE',rev)
