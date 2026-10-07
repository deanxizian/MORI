# -*- coding: utf-8 -*-
"""Publish verified M1.45 outputs; historical reviews stay explicitly historical."""
from pathlib import Path
import json,hashlib,html,re,datetime
from animation_page import generate as animation_view
from parts_classification import generate as parts_view
R=Path(__file__).resolve().parents[1];PROJECT=R.parent
read=lambda p:json.loads((R/p).read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((PROJECT/'config/geometry.json').read_text());rev=p['revision'];source=digest(R/'mori_v1_2.blend')
a=read('reports/p5r7_adoption_validation.json');v=read('reports/validation.json');paths=read('reports/p5r7_current/followthrough.json');service=read('reports/p5r7_current/service.json');body=read('reports/head_retention_body_sequence.json');retention=read('reports/head_axial_retention_validation.json');views=read('reports/p5r7_views.json');ex=read('reports/export_manifest.json');am=read('animation/manifest.json');av=read('animation/validation.json')
assert a['adoption_status']=='PASS' and v['counts']['FAIL']==0 and service['status']==body['status']==retention['status']=='PASS'
assert all(x['status']=='PASS' for x in paths['mated_plugs']) and a['full_mated_fit']=='BLOCKED'
assert all(x==source for x in [a['source_blend_sha256'],paths['source_main_sha256'],service['source_main_sha256'],body['source_blend_sha256'],retention['source_blend_sha256'],views['source_blend_sha256'],am['source_blend_sha256']])
assert am['rendered_video'] and am['p5r7_adopted'] and av['status']=='PASS'
assert read('reports/delivery_consistency.json')['status']=='PASS'
page=(R/'index.html').read_text();style=re.search(r'<style>.*?</style>',page,re.S).group(0)
page=page.replace('V1.2-M1.44',rev).replace('<h1>头身防脱压板已并入主模型。</h1>','<h1>P5R7 已应用到主模型。</h1>').replace('16件本体候选打印件 · PA12首轮结构验证 · 新增一片防脱压板','运动基板、后接口板 P5R7 · 保留16件打印件及头身防脱方案')
old='P5R7已正式交接，并完成独立接收模型的装配复核；E针/孔的原厂STEP内部不一致已核实，实物配合资料仍缺，主模型暂未替换。'
page=page.replace(old,'P5R7板卡与WeAct插接候选已应用。E排针与原厂STEP孔径资料矛盾仍为BLOCKED，未缩针或扩孔；不能把本次更新视为实物插合通过。')
page=page.replace('<a href="#p5r7">P5R7板卡</a>','')
page=page.replace('<a href="#head-retention">头身防脱</a>','<a href="#p5r7">P5R7板卡</a><a href="#head-retention">头身防脱</a>',1)
page=page.replace('<a href="reports/头身防脱_M1_44.md">本次结构报告</a>','<a href="reports/P5R7应用_M1_45.md">本次板卡报告</a><a href="reports/头身防脱_M1_44.md">此前防脱结构</a>')
section=f'''<section id="p5r7"><h2>P5R7 当前安装状态</h2><table><tr><th>部件</th><th>主模型版本／变化</th></tr><tr><td>运动基板 MCU_Carrier</td><td>P5R7；采用正式交接的68针位置。</td></tr><tr><td>WeAct 核心板</td><td>元件面朝上，四组原排针刚性翻转朝下；E口改为直排针候选。</td></tr><tr><td>三组排母</td><td>AC、BD各一组，E一组；目录壳体建模，接点及真实插入深度待核。板面间距11.04mm是候选叠层。</td></tr><tr><td>后接口板 Rear_Interface_PCB</td><td>P5R7；J3移至背面并向下插拔，旧位置与排母针尾的冲突已解除。</td></tr><tr><td>电源板／IMU</td><td>分别保持P5R6／P5R4原生板。</td></tr></table><div class="grid"><figure><img src="renders/p5r7/boards.png?revision={rev}" alt="当前主模型中的P5R7板卡与桥座"><figcaption>当前主模型实际坐标；隐藏外壳便于检查，未移动或缩放硬件。</figcaption></figure><figure><img src="renders/p5r7/stack.png?revision={rev}" alt="元件朝上的WeAct及三组排母"><figcaption>橙色排针、排母为未完整确认的候选。原厂STEP的E孔约Ø0.812mm，与0.64mm方针仍有约0.123mm³名义重叠。</figcaption></figure></div><p>三个原对象更新，新增四个采购参考对象；全部打印件的网格与位置均保持。68针编号对应、223个保留的原厂实体坐标已复核；29处对插壳包络、130个头部姿态、407个上壳／承重桥装配位置及规定维护工具包络已重新检查。</p><p class="notice">E针孔资料、真实插入／保持力、公差与软线束仍未完成。此处为允许继续结构工作的候选应用，不是采购、打印或通电放行。</p><div class="links"><a href="reports/P5R7应用_M1_45.md">更新说明</a><a href="reports/p5r7_adoption_validation.json">来源与变更范围</a><a href="reports/p5r7_current/followthrough.json">29处对插件</a><a href="reports/p5r7_current/service.json">维护空间</a><a href="mori_electronics_detail.blend">逐元件电子模型</a></div></section>'''
page=re.sub(r'<section id="p5r7">.*?</section>','',page,flags=re.S);page=page.replace('<section id="head-retention">',section+'<section id="head-retention">',1)
page=re.sub(r'<section id="animation">.*?</section>',lambda _:animation_view(R),page,flags=re.S)
failed=[x['id'] for x in ex['parts'] if x['status']!='PASS']
notice='Head_Rear原有6条非流形边仍待处理，STL已隔离；本次未改变打印件。' if failed==['Head_Rear'] else 'STL未通过：'+', '.join(failed) if failed else '全部候选STL通过拓扑检查。'
checks=f'''<section id="checks"><h2>当前检查</h2><p>{v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL / {v['counts']['BLOCKED']} BLOCKED / {v['counts']['NOT_TESTED']} NOT_TESTED。P5R7应用范围及原厂坐标复核通过；E孔针资料矛盾单独保留BLOCKED。所有打印件保持M1.44；防脱装入、螺钉工具、头部130姿态与身体407位置重查通过。</p><p>装配视频{am['animation_revision']}已同步，{am['duration_seconds']:g}秒、{am['stage_count']}章；保留上壳与桥独立运动及转60°锁防脱压板的步骤。保存后的关键帧及源模型一致性已检查。</p><p class="notice">STL {ex['exported_count']}/{ex['candidate_count']}通过（含托架与试片）。{notice}采购件实配、PA12强度、完整线束和连续扫掠不由以上有限检查证明。</p><div class="links"><a href="reports/validation.json">全部检查</a><a href="reports/p5r7_adoption_validation.json">P5R7专项</a><a href="reports/head_retention_body_sequence.json">身体装配顺序</a><a href="reports/export_manifest.json">STL清单</a><a href="reports/p5r7_delivery_commands.json">生成命令</a></div></section>'''
page=re.sub(r'<section id="checks">.*?</section>',lambda _:checks,page,flags=re.S)
page=re.sub(r'<tr><td>7</td><td>BLOCKED</td><td>.*?</td></tr>', '<tr><td>7</td><td>BLOCKED / 实配资料</td><td>P5R7已应用到主模型和动画，E针位及后板J3旧位置冲突已处理；E方针与原厂STEP孔径资料矛盾、真实插入深度和保持力仍待厂家确认。</td></tr>',page,flags=re.S)
page=page.replace('P5R7尚未应用到主模型','P5R7已应用，E针孔配合仍待核').replace('P5R7未应用','P5R7已应用，E配合仍待核')
(R/'index.html').write_text(page)
bom=read('reports/bom.json');previews=read('reports/parts_preview_manifest.json');manufacturing=parts_view(R,rev,bom,previews,ex)
(R/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html#p5r7">返回主模型</a><h1>{rev} 零件与候选打印文件</h1><p class="notice">打印件保持M1.44的16件，首轮PA12。新增排母和E排针是采购参考件。{notice}未进行采购或打印下单。</p>'+manufacturing+'</main></html>')
(R/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{x["file"]}?revision={rev}"><figcaption>{html.escape(x["id"]+" · "+x["name"])}</figcaption></figure>' for x in previews)+'</div></main></html>')
md=f'''# MORI {rev} · P5R7应用

按用户“先把P5 R7应用上去吧”的确认，已应用到当前主模型、逐元件电子模型及装配视频。

| 部件 | 当前来源 |
|---|---|
| 运动基板、后接口板 | P5R7正式交接 |
| 电源板 | P5R6，保持 |
| IMU | P5R4，保持20×16mm、两孔 |
| WeAct | 原厂V1.1 STEP，元件朝上；223个原实体保留，4组排针刚性翻转；旧弯E排针换为61300821121候选 |
| 排母 | 2×61303021821及1×61300821821目录外壳，内部接点是明确标注的估算 |

所有16件本体打印件以及维护托架、试片、既有五金和M1.44头身防脱保持。未修改hardware/、components.json、电气契约或原生PCB。

## 已执行检查

- 变更范围：3个旧对象，4个新采购参考对象；打印件坐标和网格哈希不变。
- 正式交接来源hash、68个编号引脚映射、223个保留源实体坐标一致；硬件按1:1建模。
- 新主模型与此前独立P5R7候选实体对称差小于0.02mm³。
- 当前主模型29个对插壳位置及各25个台面插拔位置通过；工具及核心板向上30mm抽出路径通过（先拆头、上壳和承重桥）。
- 130个联合头部姿态及407个两件独立支承的身体装配位置未见新增刚体干涉；防脱专项复查通过。
- 主模型重复生成、逐元件文件、渲染和动画源模型一致性检查通过。视频{am['animation_revision']}，{am['duration_seconds']:g}秒/{am['stage_count']}章。
- STL {ex['exported_count']}/{ex['candidate_count']}通过。{notice}

## 保留的未核接口

E候选方针0.64mm与原厂STEP约Ø0.812mm孔产生{a['E_source_discrepancy']['overlap_mm3']:.6f}mm³重叠。硬件增补A1确认原厂弯针也有同类模型内矛盾，不能据此断定实物不兼容或兼容。保持原始针孔，不缩针、扩孔或豁免；等待实际成品孔、匹配针型号与公差。

板面间距11.04mm仅为8.5mm排母壳体加2.54mm排针塑座的候选叠层，非实测接触啮合。弹片、插入力和保持力、焊接版本、完整线束与弯曲仍为BLOCKED/NOT_TESTED。头部舵盘、短轴以及既有实物验证事项未因本次更新关闭。

主模型SHA256：`{source}`。
PROTOTYPE / UNVALIDATED；几何候选应用，不是制造放行。
'''
for name in ['P5R7应用_M1_45.md','REPORT.md','组装与打印.md']:(R/'reports'/name).write_text(md)
(R/'README.md').write_text(f'# MORI {rev}\n\nP5R7已应用；16件打印件和M1.44防脱保持。[主模型](mori_v1_2.blend) · [本次报告](reports/P5R7应用_M1_45.md) · [逐元件电子模型](mori_electronics_detail.blend) · [装配动画](animation/index.html)。\n\nE针孔配合资料、完整线束、舵盘资料与实物验证仍待完成。'+notice+'\n')
(R/'animation/CHANGELOG_M1.45_A1.md').write_text('# M1.45-A1\n\n主模型P5R7更新：WeAct元件朝上，先装三组排母、再插核心板及E直排针候选；后板J3采用P5R7位置。保留防脱压板和上壳／桥的独立装配顺序。E针孔配套资料仍BLOCKED，动画不是实配证明。\n')
for name in ['interface_completion_status.json','assembly_completion_progress.json']:
    f=R/'reports'/name;d=json.loads(f.read_text());d.update(revision=rev,source_blend_sha256=source,p5r7_adopted=True,part_count=16,part_count_change=0,manufacturing_release=False)
    for x in d.get('pending',[]):
        if x.get('item')=='7':x.update(status='BLOCKED',detail='P5R7已按用户确认应用到主模型与动画；E方针/原厂STEP孔资料矛盾和真实啮合仍待厂家确认。')
    f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
# Keep old review evidence and label its scope instead of relabeling old tests.
study=R/'studies/prearrival_closure/index.html';s=study.read_text();s=re.sub(r'<aside id="current-p5r7">.*?</aside>','',s,flags=re.S)
banner=f'<aside id="current-p5r7" class="notice">当前主模型已于{rev}应用P5R7，并同步完整视频；本页仍是M1.43历史检查及独立候选记录。<a href="../../index.html#p5r7">查看当前模型、插接限制与复核结果</a>。</aside>'
s=s.replace('<main>','<main>'+banner,1);s=s.replace('P5R7仍是独立候选。','P5R7在此页记录为历史独立候选，当前已应用，见顶部链接。').replace('主模型和更新后的整机动画仍沿用旧板几何，P5R7未应用。','上述为当时未采用的状态；当前M1.45已采用，E配合资料仍待核。');study.write_text(s)
delivery=dict(revision=rev,source_blend_sha256=source,status='PASS',status_scope='P5R7 adoption and synchronization only',full_mated_fit='BLOCKED',printed_geometry_changed=False,robot_print_count=16,hardware_revisions=dict(motion='P5R7',rear='P5R7',power='P5R6',imu='P5R4'),animation_revision=am['animation_revision'],stl_topology_failed_ids=failed,manufacturing_release=False)
(R/'reports/p5r7_delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n')
print('P5R7_PUBLISHED',rev,flush=True)
