"""Publish M1.44 from verified saved source, exports and animation."""
from pathlib import Path
import json,hashlib,html,re,csv,datetime
from animation_page import generate as animation_view
from parts_classification import generate as parts_view
R=Path(__file__).resolve().parents[1];PROJECT=R.parent
read=lambda f:json.loads((R/f).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((PROJECT/'config/geometry.json').read_text());q=p['head_axial_retention'];rev=p['revision'];source=sha(R/'mori_v1_2.blend')
v=read('reports/validation.json');a=read('reports/head_axial_retention_validation.json');b=read('reports/head_retention_body_sequence.json');delivery=read('reports/delivery_consistency.json');ex=read('reports/export_manifest.json')
assert v['counts']['FAIL']==0 and a['status']==b['status']==delivery['status']=='PASS'
assert a['source_blend_sha256']==b['source_blend_sha256']==source
stl_failed=[r['id'] for r in ex['parts'] if r['status']!='PASS']
assert all(r['status']=='PASS' for r in ex['parts'] if r['id'] in ['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper'])
stl_notice=('现有头后壳 Head_Rear 的STL仍有6条非流形边，已隔离，不包含在通过的打印文件中。' if stl_failed==['Head_Rear'] else 'STL未通过：'+', '.join(stl_failed) if stl_failed else '所有候选STL通过当前拓扑回读。')
am=read('animation/manifest.json');assert am['rendered_video'] and am['source_blend_sha256']==source and am['head_retention_readback']['status']=='PASS'
animation=animation_view(R);assert animation
bom=read('reports/bom.json');previews=read('reports/parts_preview_manifest.json');count=sum(r['candidate_stl'] and r['group'] not in ['dock','coupon'] for r in bom)
assert count==16
style=re.search(r'<style>.*?</style>',(R/'index.html').read_text(),re.S).group(0)
seq=['承重桥离机预装两枚SL-M3×4嵌件和Yaw轴承。','C形压板从侧面套到转动座，连同已预装舵机的转动座一起下放到承重桥；俯仰头部暂不安装。','转动座转至约+60°露出左右孔位，用2mm内六角长柄从上方锁两枚M3×8；压板固定在承重桥上，不随Yaw转动。','回到机械零位，再装俯仰头托和头壳。维修时先拆俯仰头部，卸下压板螺钉并解除反力轴连接，压板与转动座一起上提。']
summary=f'''<section id="head-retention"><h2>头身防脱方案已应用</h2><p>新增1片PA12 C形压板、2枚M3×8螺钉和2枚SL-M3×4嵌件。本体打印件15→16件。Yaw轴承与配套限位下移4.5mm；头壳、屏幕、摄像头、舵机及轮轴基准保持。</p><div class="grid"><figure><img src="studies/head_axial_retention/adopted/section.png?revision={rev}" alt="当前模型实际剖面"><figcaption>蓝色转动轴肩被黄色压板挡住；压板与灰色桥座锁紧。保留0.4mm名义间隙，不是轴承预紧。</figcaption></figure><figure><img src="studies/head_axial_retention/adopted/keeper.png?revision={rev}" alt="单片C形压板"><figcaption>一片平板式压板，左右螺钉沉入板内；先侧套，再随头座下放。</figcaption></figure></div><h3>装配顺序</h3><ol>'''+''.join('<li>'+s+'</li>' for s in seq)+'''</ol><p>首次装配可从上方操作；维修需先拆俯仰总成，不属于整头快拆。舵盘、中心螺钉及最终传动叠层仍等厂家资料。</p><div class="links"><a href="reports/头身防脱_M1_44.md">设计与装配说明</a><a href="reports/head_axial_retention_validation.json">最终模型检查</a><a href="animation/index.html">更新后的装配视频</a></div></section>'''
old=(R/'index.html').read_text();page=old
page=re.sub(r'<section id="head-retention">.*?</section>','',page,flags=re.S)
page=page.replace('<title>MORI V1.2-M1.43</title>',f'<title>MORI {rev}</title>').replace('<b>MORI V1.2-M1.43</b>',f'<b>MORI {rev}</b><a href="#head-retention">头身防脱</a>')
page=page.replace('<a href="reports/接口复核_M1_43.md">详细报告</a>','<a href="reports/头身防脱_M1_44.md">本次结构报告</a><a href="reports/接口复核_M1_43.md">此前六项修正</a>')
page=page.replace('<h1>六项机械问题已应用。</h1>','<h1>头身防脱压板已并入主模型。</h1>').replace('15件本体候选打印件 · 不新增零件 · 孔槽、五金和轴向堆叠配套更新','16件本体候选打印件 · PA12首轮结构验证 · 新增一片防脱压板')
page=page.replace('<section id="interface">',summary+'<section id="interface">',1).replace('renders/head_section.png?revision=V1.2-M1.43','renders/head_section.png?revision='+rev).replace('renders/internal.png?revision=V1.2-M1.43','renders/internal.png?revision='+rev).replace('renders/exploded.png?revision=V1.2-M1.43','renders/exploded.png?revision='+rev).replace('renders/45_assembled.png?revision=V1.2-M1.43','renders/45_assembled.png?revision='+rev)
page=re.sub(r'<section id="animation">.*?</section>',lambda _:animation,page,flags=re.S)
checks=f'''<section id="checks"><h2>当前检查</h2><p>当前{v['counts']['PASS']} PASS / {v['counts']['FAIL']} FAIL / {v['counts']['BLOCKED']} BLOCKED / {v['counts']['NOT_TESTED']} NOT_TESTED。防脱专项：130个头部姿态、121个侧套位置、181个组合装入位置、两枚螺钉和工具通道均通过名义几何检查。原上壳／桥配合的407个位置重新检查通过。重复生成、候选STL回读及动画源模型一致性已检查。</p><p>采购件精确配合仍受资料缺项限制；有限采样不代表打印强度、完整线束或整机打样放行。</p><div class="links"><a href="reports/head_axial_retention_validation.json">防脱专项</a><a href="reports/validation.json">全部检查</a><a href="reports/head_retention_body_sequence.json">身体装配顺序</a><a href="reports/interface_printability.json">打印件壁厚采样</a><a href="reports/export_manifest.json">STL清单</a><a href="reports/head_retention_delivery_commands.json">生成命令</a></div></section>'''
checks=checks.replace('重复生成、候选STL回读及动画源模型一致性已检查。',f'重复生成及动画源模型一致性已检查；STL {ex["exported_count"]}/{ex["candidate_count"]}通过（含托架及试片），本次三件打印件全部通过。</p><p class="notice">{stl_notice}')
page=re.sub(r'<section id="checks">.*?</section>',lambda _:checks,page,flags=re.S);(R/'index.html').write_text(page)
manufacturing=parts_view(R,rev,bom,previews,ex)
(R/'manufacturing.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html#head-retention">返回主模型</a><h1>{rev} 零件与候选打印文件</h1><p class="notice">本体16件选用PA12。新增压板是打印件；两枚M3×8及两个SL-M3×4为采购五金。{stl_notice}未下打印或采购订单；强度与实际配合待验证。</p>'+manufacturing+'</main></html>')
(R/'parts.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8">{style}<main><a href="index.html">当前总装</a><h1>{rev}部件预览</h1><div class="grid">'+''.join(f'<figure><img loading="lazy" src="{r["file"]}?revision={rev}"><figcaption>{html.escape(r["id"]+" · "+r["name"])}</figcaption></figure>' for r in previews)+'</div></main></html>')
md=f'''# MORI {rev} 头身独立防脱

已按用户确认采用A5，主模型、候选STL和完整装配动画已同步。本体打印件由15变16。

- 新增：1片PA12 `Yaw_Anti_Lift_Keeper`，2枚M3×8圆头内六角螺钉，2个FINE SL-M3×4嵌件。
- 修改：`Yaw_Base`、`Pitch_Yoke`；Yaw轴承及限位下移4.5mm，轴承中心Z152.5mm。保持其余头壳、光学、舵机和电子板基准。
- 轴承参考NSK6804ZZ：20×32×7mm，轴肩Ø22、壳肩孔最大Ø30来自[官方边界/挡肩尺寸]({q['bearing']['source_url']})。模型是边界包络，不是完整原厂CAD或实测。
- 试配：轴颈Ø19.9、壳孔Ø32.1；C压板厚4、外径60；螺钉轴X±26/Y0；正常上下间隙0.4mm。不是零间隙或轴承预紧。

## 装配与维修

'''+ '\n'.join(f'{i}. {s}' for i,s in enumerate(seq,1))+f'''

压板螺钉用2AF长柄；测试包络为70mm长端、20mm横柄。名义工具可达不包含人手、紧固扭矩、具体扳手弯曲和软线束。

## 实际检查

当前主模型：`{source}`。
防脱专项、两次重复生成、来源/渲染一致性均PASS。STL精确回读{ex['exported_count']}/{ex['candidate_count']}通过（含托架与试片），本次三件全部通过。{stl_notice}旧导出读取程序按小数点后5位合并顶点，会产生额外退化面，已改为保持STL原始float32坐标并用Blender独立导入核对；没有改动后壳形状或将其缺陷豁免。

新增接口周围130个头部姿态无新增碰撞；121个侧套位置、181个下放位置、螺钉装入和工具抽样通过。原身体／桥407个装配位置和工具复核通过。

两嵌件试孔最薄径向采样壁厚约{min(r['minimum_wall_mm'] for r in a['pilots']):.3f}mm，螺钉尖端对孔底间隙约0.30mm；新增孔的壁厚、盲孔底与名义旋合量见专项记录。布尔浮点退化三角面已清理；最终实体与批准A5每件对称差低于0.002mm³，功能尺寸保持。

动画 {am['animation_revision']}，{am['duration_seconds']:g}秒，{am['stage_count']}章。第16章展示转60°锁压板；固定压板不随头座转动。保存后的动画矩阵另做半帧几何抽查；不是全片连续扫掠证明。

## 未完成项

舵盘、中心螺钉、俯仰短轴及最终传动轴向叠层仍待厂家资料；不能由防脱压板推断舵机轴已完全卸载。完整线束／应力释放／联合运动仍待完成。P5R7保持独立候选，未混入当前主模型。PA12收缩补偿、嵌件安装及抗拔、蠕变／冲击、轴承实配和真实装配仍为NOT_TESTED。

此前PA12 C02嵌件、C04轴承孔、C05轴颈试片可筛查材料配合；既有试片覆盖相邻尺寸，不等同于最终19.9mm轴颈的实配证明。请结合实物和打印批次测量再选补偿。

PROTOTYPE / UNVALIDATED；未进行采购、打印、机加工或通电放行。
'''
(R/'reports/头身防脱_M1_44.md').write_text(md);(R/'reports/REPORT.md').write_text(md)
(R/'README.md').write_text(f'# MORI {rev}\n\n已采用头身独立防脱压板，16件PA12本体候选打印件。[当前模型](mori_v1_2.blend) · [结构说明](reports/头身防脱_M1_44.md) · [装配动画](animation/index.html)。\n\n舵盘资料、完整线束和实物验证仍待完成。P5R7独立候选未并入。\n')
(R/'reports/组装与打印.md').write_text(md)
study=R/'studies/head_axial_retention';page=(study/'index.html').read_text();page=page.replace('独立候选 A5 · 待确认 · 主模型仍为 M1.43','A5已采用 · 当前主模型 M1.44').replace('先把头身的独立防脱做好','头身独立防脱已应用到主模型').replace('src="section.png"','src="adopted/section.png?revision='+rev+'"')
if '../../index.html#head-retention' not in page:
 page=page.replace('<h1>头身独立防脱已应用到主模型</h1>','<h1>头身独立防脱已应用到主模型</h1><p><a href="../../index.html#head-retention">当前主模型与最终检查</a> · <a href="../../animation/index.html">更新后的完整装配动画</a></p>')
page=page.replace('打开可编辑候选 Blender','历史A5候选 Blender').replace('仅当前候选名义几何检查通过','最终主模型的本接口名义几何检查通过').replace('<title>MORI · 头身独立防脱候选</title>','<title>MORI M1.44 · 头身独立防脱</title>').replace('alt="当前与候选的真实网格剖面对比"','alt="M1.43与已采用A5的历史剖面对比"').replace('alt="候选实际网格局部剖面，显示两枚螺钉和被压板挡住的轴肩"','alt="M1.44主模型实际网格剖面，显示防脱压板和轴肩"')
(study/'index.html').write_text(page)
candidate_readme=(study/'README.md').read_text()
candidate_readme=candidate_readme.replace('# 头身独立防脱候选 A5 — 待用户确认','# 头身独立防脱 A5 — 已应用于 M1.44').replace('当前候选没有应用到主模型。','A5已获用户确认并应用于M1.44。当前检查见[最终结构报告](../../reports/头身防脱_M1_44.md)，下文候选数据作为设计来源保留。').replace('主模型、config、STL和装配视频均未替换。','主模型、config、候选STL和完整装配视频已同步；当前输出见[主页面](../../index.html#head-retention)。本目录manifest.json与candidate.blend仍记录批准前的A5候选，adopted/记录最终主模型视图。')
(study/'README.md').write_text(candidate_readme)
(R/'animation/CHANGELOG_M1.44_A1.md').write_text('# M1.44-A1\n\n完整动画同步采用A5防脱压板。增加压板侧套及随转动座下放，转动座60°时两枚M3下锁，再回零安装俯仰头部。固定压板／反力连接不随Yaw转动。原机身上壳／桥独立支承序列保留。主模型旧板来源保留，P5R7未应用。\n')
for name in ['interface_completion_status.json','assembly_completion_progress.json']:
 d=read('reports/'+name);d.update(revision=rev,source_blend_sha256=source,part_count=16,part_count_change=1,head_axial_retention={'status':'PASS','scope':'Nominal geometry only; vendor transmission stack pending','evidence':'head_axial_retention_validation.json'},manufacturing_release=False)
 for item in d.get('pending',[]):
  if item.get('item')=='7':item['detail']='P5R7已正式交接并接收为独立候选；原厂WeAct STEP的E针/孔存在内部尺寸不一致，最终配合资料仍待硬件任务确认。P5R7尚未应用到主模型。'
  if item.get('item')=='完整线束':item['detail']='已有M1.43局部路径筛查；完整线束、弯曲半径、应力释放及联合运动仍未闭合。新防脱环占用局部空间，旧路径不能直接视为M1.44通过。'
 (R/'reports'/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
cpath=PROJECT/'contracts/mechanical_interfaces.json'
# Do not mutate dimensions/contracts after generation: status lives in reports.
report=dict(revision=rev,status='PASS',status_scope='Approved head-retention integration only',approval='A5 explicitly approved by user',source_blend_sha256=source,robot_print_count=16,added_prints=1,added_standard_fasteners=4,hardware_adoption='P5R6 + IMU P5R4 retained; P5R7 not adopted',geometry_evidence='head_axial_retention_validation.json',body_sequence='head_retention_body_sequence.json',animation_revision=am['animation_revision'],stl_topology_failed_ids=stl_failed,physical_validation='NOT_TESTED',manufacturing_release=False)
(R/'reports/head_axial_retention_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('RETENTION_REPORT_PUBLISHED',rev,flush=True)
