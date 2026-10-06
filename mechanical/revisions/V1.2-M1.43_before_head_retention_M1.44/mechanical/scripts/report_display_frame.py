"""Publish the accepted flat U connection and synchronized current artifacts."""
import json,html

def publish(root,rev,report_name):
    load=lambda name:json.loads((root/'reports'/name).read_text())
    cfg=json.loads((root.parent/'config/geometry.json').read_text())
    v=load('display_frame_validation.json');allv=load('validation.json');motion=load('head_motion.json')
    geo=load('display_frame_geometry.json');bom=load('bom.json');delivery=load('delivery_consistency.json')
    assert v['status']=='PASS' and allv['counts']['FAIL']==0 and delivery['status']=='PASS'
    assert load('rebuild_check.json')['status']=='PASS'
    nprints=sum(b['candidate_stl'] and b['group'] not in ['dock','coupon'] for b in bom)
    nfast=sum(any(k in b['id'] for k in ['Screw','Nut','Insert','Washer']) and not b['id'].startswith('Coupon') for b in bom)
    delta=v['accepted_solid'];d=geo['dimensions_mm'];study=root/'studies/display_frame_transition'
    text=f'''# Display Frame 平直连接 · {rev}

用户确认第二版平直 U 形候选。两侧固定耳和下横梁前面齐平（Y={d['front']:g} mm），底边齐平（Z={d['bot']:g} mm）；去掉旧内侧回折竖片，并清除横梁上沿约 0.001 mm 的历史布尔运算残片。原侧耳上保留四个螺孔及螺母沉槽。

只改 Display_Frame 一个打印件。中央立柱、相机夹持座、三个 LCD 原厂安装轴线/倾斜承压面、屏幕和相机位姿、其他打印件及所有硬件保持。相对于 M1.40，新增材料 {delta['added_mm3']:.3f} mm³、去除 {delta['removed_mm3']:.3f} mm³，净增约 {(geo['after_volume_mm3']-geo['before_volume_mm3'])/1000:.2f} cm³。打印件仍 {nprints} 件，紧固件对象仍 {nfast} 个；没有新孔、额外走线孔或新零件。

当前外轮廓与确认候选的差量 {delta['difference_from_accepted_outside_lcd_cutters_mm3']:.6f} mm³。正式生成保留 M1.40 原 LCD 孔面，避免候选中重复切孔产生的微小碎面；原孔面区域差量 {delta['original_LCD_interface_difference_mm3']:.6f} mm³，网格清理沿用项目 0.0005 mm 容差。对 M1.40 逐件网格/位姿核对，只有 Display_Frame 改变。其前面、底边承接和旧薄片清除的实体探针通过，打印件保持单一连续实体。

完整检查结果：{allv['counts']['PASS']} PASS / {allv['counts']['FAIL']} FAIL / {allv['counts'].get('NOT_TESTED',0)} NOT_TESTED / {allv['counts'].get('BLOCKED',0)} BLOCKED。{motion['poses']} 个组合头部姿态未检出干涉，保留低头 20°。三个 LCD 螺钉的承压面、装入与直杆工具路径，以及四个侧面螺母的装入路径通过。重复生成、非生成对象保留、当前预览与毫米 STL、装配动画几何一致性已检查。采购件尺寸不缩放，硬件源文件未修改。

Blender、打印候选 STL、零件预览、总装页面、可编辑装配动画与视频已同步。首轮 PA12；实物公差、螺纹/嵌件匹配、承载强度与动态性能仍未验证。本次几何修改没有解决此前舵盘/短轴等未定接口，也不构成制造放行。

- [当前主模型](../mori_v1_2.blend)
- [可编辑装配动画](../mori_assembly_animation.blend)
- [装配视频](../animation/MORI_assembly.mp4)
- [当前形状与对比](../studies/display_frame_transition/index.html)
- [改动范围及实体检查](display_frame_validation.json)
- [全部检查](validation.json)
- [同步交付检查](delivery_consistency.json)
- [实际命令与日志](display_frame_commands.json)

M1.40 快照：`mechanical/revisions/V1.2-M1.40_before_display_frame_flush/`。当前唯一尺寸源：`config/geometry.json`；本次参数入口：`display_frame_simplification`。
'''
    (root/'reports'/report_name).write_text(text);(root/'reports/REPORT.md').write_text(text);(study/'README.md').write_text(text)
    cards=lambda entries: '<div class="frame-grid">'+''.join(f'<figure><img src="{p}?revision={rev}"><figcaption>{html.escape(t)}</figcaption></figure>' for p,t in entries)+'</div>'
    style='<style>.frame-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.frame-grid figure{margin:0;background:#fff}.frame-grid img{width:100%;display:block}.frame-grid figcaption{padding:12px}@media(max-width:700px){.frame-grid{grid-template-columns:1fr}}</style>'
    section=style+'<section id="display-frame"><h2>Display Frame 已简化</h2><p>两侧固定耳与横梁前面、底边齐平，旧回折片及薄边已清除。中央立柱保持，孔位和硬件不变。</p>'+cards([('studies/display_frame_transition/current_detail.png','当前总装局部：平直U形连接'),('studies/display_frame_transition/current_part.png','当前独立打印件')])+f'<p>只改1个打印件，未增加零件或紧固件。{motion["poses"]}个组合头部姿态及相关紧固件装入检查通过；实际强度与公差仍待验证。</p><p><a href="reports/{report_name}">本轮记录</a> · <a href="studies/display_frame_transition/index.html">修改前后对比</a></p></section>'
    page=(root/'index.html').read_text().replace('CAM固定座完整接入后板，<br>排查其他安装座。','Display Frame 两侧连接齐平，<br>去掉多余错层。').replace('<section id="mount-roots">',section+'<section id="mount-roots">').replace('<nav><a href="#mount-roots">本轮修复</a>','<nav><a href="#display-frame">本轮简化</a><a href="#mount-roots">CAM固定座</a>')
    (root/'index.html').write_text(page)
    study_page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Display Frame · '+rev+'</title>'+style+'<style>body{font:16px/1.7 system-ui;background:#edf1f2;color:#22313a;margin:30px auto;max-width:1200px;padding:20px}a{color:#165c8a}</style>'+f'<a href="../../index.html?revision={rev}#display-frame">返回当前总装</a><h1>{rev} · Display Frame 已应用</h1><p>按确认的第二版方案：侧耳与横梁前面、底边分别齐平，形成平直 U 形连接。只修改 Display Frame，中央立柱及全部硬件保持。</p>'+cards([('before_detail.png','M1.40 原连接'),('current_detail.png','当前已应用：前面和底边齐平'),('before_part.png','M1.40 原零件'),('current_part.png','当前正式零件')])+f'<p>{nprints}件机器人打印件、{nfast}个紧固件对象，数量不变。完整几何检查没有新增失败，低头20°保留。PA12强度、螺纹、公差和真实器件配合仍待验证。</p><p><a href="../../reports/{report_name}">修改与验证记录</a> · <a href="../../mori_v1_2.blend">当前Blender</a> · <a href="../../animation/index.html?revision={rev}-A1">已同步装配动画</a></p></html>'
    (study/'index.html').write_text(study_page)
    session=json.loads((study/'session.json').read_text());session.update(status='APPLIED_'+rev,approval='USER_APPROVED_FLUSH_U_CENTRAL_MAST_UNCHANGED',production_validation='../../reports/display_frame_validation.json',current_model='../../mori_v1_2.blend');(study/'session.json').write_text(json.dumps(session,ensure_ascii=False,indent=2)+'\n')
    progress=load('assembly_completion_progress.json');progress['rows'].insert(0,dict(item='Display Frame 连接简化',status='已应用/完整几何检查完成',detail='两侧前面与底边齐平；旧内侧片及约0.001mm残片删除。中央立柱、孔位和硬件保持。'));(root/'reports/assembly_completion_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
    print('DISPLAY_FRAME_REPORT_COMPLETE',rev,flush=True)
