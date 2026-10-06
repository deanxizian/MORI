"""Publish J2 with its mating blockers, source dimensions and failed attempts."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[3];OUT=HERE/'terminal_threading'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
route=read(HERE/'joined_entry_screen.json');check=read(OUT/'candidate_screen.json')
audit=read(OUT/'cleaned/reloaded_mated_audit.json');clean=read(OUT/'cleaned/storage_rebuild.json')
body=read(HERE/'body_leads/inner_arc_prefix_pools.json')
assert check['status']==clean['status']=='PASS' and audit['status']=='BLOCKED'
assert all(r['status']=='PASS' for r in audit['raw_mesh_checks'])
assert audit['cleaned_installed_source_check']['status']=='PASS' and not audit['cleaned_installed_source_check']['hits']
assert sha(ROOT/'mechanical/mori_v1_2.blend')==route['source_blend_sha256']
assert sha(OUT/'cleaned/candidate.blend')==audit['source_candidate_sha256']==clean['candidate_blend_sha256']
sources=read(HERE/'amass_mating/source_receipt.json')
for r in sources:assert sha(HERE/'amass_mating'/r['file'])==r['sha256']
amass=dict(status='PASS',scope='Source receipt and per-field dimensions only; assembled route fit not established',
    sources={r['file']:r['sha256'] for r in sources},
    mating_pair=['XT30UPB-M','XT30U-F'],manufacturer_document='2025V1',page=1,
    drawing_mating_overall_mm={'nominal':20.1,'tolerance_plus_minus':.5,'evidence':'VENDOR_DOCUMENTED'},
    board_leg_mm={'nominal':3.,'tolerance_plus_minus':.3,'evidence':'VENDOR_DOCUMENTED'},
    above_board_seat_mm={'nominal':17.1,'independent_extremes':[16.3,17.9],'evidence':'DERIVED_FROM_DOCUMENTED_DIMENSIONS'},
    mating_width_mm={'nominal':10.2,'tolerance_plus_minus':.3,'evidence':'VENDOR_DOCUMENTED'},
    board_housing_thickness_mm={'nominal':5.6,'tolerance_plus_minus':.3,'evidence':'VENDOR_DOCUMENTED_BOARD_HALF_ONLY'},
    current_power_seat_world_z_mm=121.1,derived_top_z_mm={'nominal':138.2,'upper_limit':139.},
    prior_clearance_allocation_mm=23.1,main_model_applied=False,
    wire_end_solder_and_insulation='NOT_TESTED',female_thickness_tolerance='NOT_TESTED',full_harness='BLOCKED')
(HERE/'amass_mating/received_dimensions.json').write_text(json.dumps(amass,ensure_ascii=False,indent=2)+'\n')
review=f'''# J2：端子临时穿入与板端复核

**整体状态仍为 BLOCKED。主模型是 M1.47，未应用这两处候选打印件改动。**

这次找到了区别于装后线形的临时端子路线，同时补查了此前局部检查未包括的29个对插包络。后者暴露了板端过渡问题，不能只报局部通过。

![端子和装后线形](transit_sections.png)

## 已完成的具体检查

- JST SH 原厂目录中的3.9×1.35×0.8 mm名义示意，被明确建成参考长方体；不是完整压接后端子CAD。暂不装胶壳，零位穿过中央段，在两端给端子长度留出转向空间。
- 四个方向分别使用677段连续凸包覆盖，扣除插值误差后，参考包络对207个未改源实体/代理及14根固定线候选的间隙下界为{check['nominal_contact_to_source_gap_lower_bound_mm']:.3f} mm。**这个PASS没有包含29个对插包络。**
- 只在独立副本更改Yaw_Base和Pitch_Yoke；其余207个物体保持。原始保存网格的退化面已在独立清理副本修正：重新打开后，两件均为单一闭合实体、无零面积面、无非流形边。局部面到面完整误差未认证；双向顶点到表面的最大抽样差为0.001373 mm，不能拿拓扑代替强度检查。
- 清理副本中，既定局部线形对209源实体/代理的130头部姿态、520个导线姿态实例检查通过。固定方式、随端子运动的软线、最小壁厚和承载仍未完成。

## 加入插头后，为什么还不能应用

![原径向段与对插包络](body_mating_review.png)

旧J1径向段在45°、225°、315°三个方向进入了电源板J11、J4、J12的保守胶壳空间；13个Yaw姿态共39项未通过间隙检查。临时裸端子穿入的四个方向也分别与现有插头预留空间相交。

这些插头原来按完整未插合长度预留，**不是精确插合CAD，因此不把这一结果说成实物必然干涉。** 尚未确认“先穿线再装其他插头”的完整装配顺序，也没有省略插头来宣称全部通过。

已按基板Motion J5的真实针脚编号和2mm间距提取四个出线分配位置；CAM端仍只有照片估计区域，没有编造其真实针序视图或出线基准。

身体端分别尝试了单段三次曲线、R7出线转弯加平面曲线和降高S弯，以及把临时入口半径32mm内收到14.8mm的方案。内收版本只找到部分单线候选，未找到四线成组方案；有限家族失败不代表空间必然无解。没有移动板卡、互换针序、缩小真实硬件或为失败线路额外开孔。

## 新找到的原厂数据改变了下一步

[艾迈斯2025V1互配图](../amass_mating/README.md)明确给出XT30UPB-M与XT30U-F互配总长20.10±0.50mm，板端焊脚3.00±0.30mm。由此推导板上高度17.10mm、独立极限上界17.90mm。旧23.1mm只是未扣除插合量的保守分配，不能再把插合高度笼统列为找不到。

但新极限包络顶部可达当前电源板Z139mm，与旧径向线段同高，所以也不能直接撤销所有冲突。下一步先用这份资料重建插合空间，补齐焊接/绝缘出线，再继续板端和关节固定设计。无需先为旧过大包络修改打印结构。

完整俯仰段、CAM接口、相机FPC、固定/应力释放、拆装路径和逐线下料长度仍未完成。局部92.865mm不是加工长度。实际端子压接形状、配套舵盘和线材动态寿命仍有独立的资料或实物验证项。

## 文件

- [已清理的独立研究Blender](cleaned/candidate.blend)（未采用，不是可打印发布版）
- [保存/重载/插头复核](cleaned/reloaded_mated_audit.json)
- [网格清理记录](cleaned/storage_rebuild.json)；[最初失败的重载检查](reloaded_mated_audit.json)
- [207源物体的参考端子扫掠](candidate_screen.json)；[临时路线](transit_screen.json)
- [基板与CAM端点来源](../h06_ports.json)
- [原身体端曲线尝试](../body_leads/prefix_pools.json)；[R7过渡尝试](../body_leads/arc_prefix_pools.json)；[入口内收尝试](../body_leads/inner_arc_prefix_pools.json)
- [原厂互配尺寸](../amass_mating/received_dimensions.json)；[原厂压接参数与版本限制](../TOOLING_DETAILS.md)
- [命令记录](commands.json)

主模型SHA256：`{route['source_blend_sha256']}`。工具：Blender5.2.2 LTS / d13f752e3b9c；制图Python3.12.14。硬件文件只读，未发订单或加工图。
'''
(OUT/'README.md').write_text(review)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>J2 端子穿入与板端复核 · MORI</title><style>body{font:16px/1.8 -apple-system,BlinkMacSystemFont,sans-serif;max-width:1050px;margin:36px auto;padding:0 24px;color:#253f49;background:#f5f7f7}h1{font-size:30px}h2{font-size:23px;margin-top:32px}img{width:100%;border-radius:8px;background:white}a{color:#086b7c}.note{background:#fff0d9;padding:14px 18px;border-left:4px solid #b48232}table{border-collapse:collapse;width:100%}td,th{padding:10px 12px;border-bottom:1px solid #d4dede;text-align:left}</style>
<p><a href="../index.html">← A8研究和原厂资料</a></p><h1>临时穿入有了路线，完整线束仍未通过</h1>
<p class="note">独立研究J2 · 主模型M1.47未改 · 未采用、未发布加工。加入对插包络后的检查仍为BLOCKED。</p>
<table><tr><th>已完成</th><th>结果与范围</th></tr><tr><td>参考裸端子的连续穿入</td><td>PASS：四个方向，对207个未改源物体和14根固定线；未含对插包络</td></tr>
<tr><td>两件候选打印件的网格</td><td>已清理并重载；单一闭合实体、无退化面。强度/薄壁未验证</td></tr>
<tr><td>装后局部线形</td><td>PASS：对209源实体/代理，130个头部姿态</td></tr>
<tr><td>加入29个对插包络</td><td>BLOCKED：三根径向引出段及四条端子穿入路线占用了保守插头空间</td></tr>
<tr><td>完整板端连接与固定</td><td>BLOCKED：尚无四线成组连接、固定和完整加工长度</td></tr></table>
<h2>装后导线与装入动作是两条不同路线</h2><img src="transit_sections.png" alt="J2两处打印件剖面以及装后线形和临时端子路线">
<h2>先核实插合空间，再改走线</h2><img src="body_mating_review.png" alt="旧径向引出段与电源板对插包络的俯视关系">
<p>原来采用未扣除插合量的23.1mm保守空间。新找到的艾迈斯2025V1原厂图给出互配总长20.10±0.50mm，扣除板端焊脚后，板上名义高度17.10mm，独立极限上界17.90mm。仍需重建正确包络与焊接出线并复跑；当前结果不能解释成实物必然干涉。</p>
<p><a href="../amass_mating/README.md">查看原厂尺寸、图纸和推导</a> · <a href="../amass_mating/sources/XT30UPB_M_2025V1.pdf">原厂2025V1规格书</a></p>
<h2>尚未完成</h2><p>四根线的板端过渡与固定、完整俯仰段、CAM实际插头、相机FPC、装入和拆卸时的软线、逐线下料长度。已有局部长度不能给供应商下料。</p>
<p><a href="README.md">完整说明</a> · <a href="cleaned/candidate.blend">独立研究Blender</a> · <a href="cleaned/reloaded_mated_audit.json">清理后复核</a> · <a href="../TOOLING_DETAILS.md">压接工艺资料</a></p></html>'''
(OUT/'index.html').write_text(page)
commands=[
 '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/'+s+'.py'+extra
 for s,extra in [('plan_terminal_threading',''),('build_threading_candidate',''),('inspect_h06_ports',''),
 ('plan_h06_body_leads',''),('plan_h06_body_arcs',''),('plan_h06_body_arcs',' -- --inner-staging'),
 ('verify_threading_candidate',''),('verify_threading_candidate',' -- --cleaned')]]
commands += ['/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/studies/prearrival_finish/harness_A8/terminal_threading/candidate.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/'+s+'.py' for s in ['repair_threading_storage','rebuild_threading_storage']]
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/'+s+'.py' for s in ['plot_terminal_threading','publish_threading_review','verify_delivery']]
(OUT/'commands.json').write_text(json.dumps(dict(cwd=str(ROOT),commands=commands,
    known_failures=['Direct bmesh weld opened edges: cleaned/storage_cleanup.json retained.',
       'Initial kernel normalization used read-only ndarray input; corrected to explicit writable C-order copies.',
       'Existing 23.1mm conservative plug allocations fail; new vendor mating dimensions received, rerun still pending.'],
    main_model_applied=False),ensure_ascii=False,indent=2)+'\n')

state_path=PARENT/'work_status.json';state=read(state_path)
detail='A8/J2完成裸端子临时穿入的局部研究，并修正两件候选的保存网格；对209源实体的局部线形检查通过。加入29个保守对插包络后仍有冲突，身体端尚无四线成组路线。新取得AMASS 2025V1互配尺寸，推导板上名义17.1mm/极限17.9mm，需替换旧23.1mm分配再复跑。固定、俯仰段、CAM接口、FPC和逐线长度未完成；主模型未改。'
old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='harness_A8/terminal_threading/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/terminal_threading/index.html',
    J2_nominal_contact_vs_207_sources='PASS',J2_cleaned_raw_topology='PASS',J2_local_wire_vs_209_sources='PASS',
    J2_with_29_mating_allocations='BLOCKED',J2_body_four_wire_prefix='BLOCKED',
    J2_applied=False,AMASS_mated_dimensions='PASS',AMASS_mated_dimension_review='harness_A8/amass_mating/README.md',
    AMASS_new_mating_envelope_replay='NOT_TESTED',complete_UART_harness='BLOCKED')
state['updated_utc']=datetime.now(timezone.utc).isoformat();state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for p in [HERE/'index.html',PARENT/'index.html']:
    text=p.read_text();href='terminal_threading/index.html' if p.parent==HERE else 'harness_A8/terminal_threading/index.html'
    block=f'<section id="threading-update"><h2>最新：端子穿入与对插空间复核</h2><p>{detail}</p><p><a href="{href}">查看J2研究、当前冲突和新找到的原厂互配图</a>。下方J1和早期结果保留为历史记录。</p></section>'
    if 'id="threading-update"' in text:text=re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S)
    elif p.parent==HERE:text=text.replace('<section id="joined-entry">',block+'\n<section id="joined-entry">')
    else:text=re.sub(r'<section id="harness-A8-update">.*?</section>',block,text,flags=re.S);text=text.replace(old,detail)
    p.write_text(text)
p=HERE/'README.md';text=p.read_text();start='<!-- threading-update:start -->';end='<!-- threading-update:end -->'
block=f'{start}\n## 最新进展：J2与对插包络复核\n\n{detail}\n\n[最新评审](terminal_threading/index.html) · [新找到的AMASS互配尺寸](amass_mating/README.md)。下文J1的结果仅属此前范围。\n{end}'
if start in text:text=re.sub(re.escape(start)+'.*?'+re.escape(end),block,text,flags=re.S)
else:text=text.replace('<!-- joined-entry:start -->',block+'\n\n<!-- joined-entry:start -->')
p.write_text(text)
print('J2_AND_AMASS_REVIEW_PUBLISHED')
