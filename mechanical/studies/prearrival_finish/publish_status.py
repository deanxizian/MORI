"""Publish the current M1.46 evidence without adopting unapproved candidates."""
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE.parents[1]
P = M.parent


def readj(path):
    return json.loads(path.read_text())


def writej(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


revision = readj(P / 'config/geometry.json')['revision']
assert revision == 'V1.2-M1.46', revision
source_hash = hashlib.sha256((M / 'mori_v1_2.blend').read_bytes()).hexdigest()
equivalence = readj(HERE / 'interface_sync/source_equivalence.json')
assert equivalence['status'] == 'PASS' and equivalence['current_source_blend_sha256'] == source_hash
assert not equivalence['changed_objects'] and not equivalence['embedded_animation_source_differences']
assert equivalence['original_source_blend_sha256'] == hashlib.sha256((HERE / 'interface_sync/before/mori_v1_2.blend').read_bytes()).hexdigest()
equivalent_sources = {source_hash, equivalence['original_source_blend_sha256']}
eng = readj(HERE / 'engineering_current.json')
audit = readj(HERE / 'rear_repair_audit.json')
thin = readj(HERE / 'thin_candidate_check.json')
service = readj(HERE / 'thin_candidate_service.json')
entry = readj(HERE / 'reaction_link_entry_baseline.json')
imu_routes = readj(HERE / 'imu_joint_routes.json')
animation = readj(M / 'animation/delivery.json')
exports = readj(M / 'reports/export_manifest.json')
counts = readj(M / 'reports/validation.json')['counts']
assert eng['source_blend_sha256'] in equivalent_sources and thin['source_blend_sha256'] in equivalent_sources
assert animation['source_blend_sha256'] == source_hash
assert audit['status'] == 'PASS' and eng['status'] == 'PASS'
assert not thin['applied_to_main']
assert all(x['source_blend_sha256'] in equivalent_sources for x in [service, entry, imu_routes])
assert service['status'] == 'FAIL' and entry['status'] == imu_routes['status'] == 'BLOCKED'
assert not service['applied_to_main'] and not imu_routes['main_applied']
assert exports['exported_count'] == exports['candidate_count'] == 21
assert all(x['status'] == 'PASS' for x in exports['parts'])
assert counts['FAIL'] == 0
assert readj(M / 'reports/delivery_consistency.json')['status'] == 'PASS'

remaining = [
    dict(id='reaction_assembly', item='反力夹口初次装配', status='BLOCKED', owner='机械；依赖舵盘接口定型',
         detail='现有主模型的夹口螺钉装入、直柄工具与预装件直线穿入路线受Pitch_Yoke阻挡。离机组合搜索仍未找到完整路径。局部削平/移孔C1可改善工具路径，但仍撞后侧耳座，未应用；继续削小会切入夹持结构，需结合最终舵盘定型。',
         evidence='reaction_assembly_review.html'),
    dict(id='thin_features', item='三处薄边修正', status='BLOCKED', owner='机械；待用户确认',
         detail='转台旧螺母通道残边约0.04mm、反力夹口约0.4mm、轮驱鞍座约0.8mm。独立候选通过130姿态及轮驱拆装检查，尚未应用；夹口完整装配仍未闭合。',
         evidence='thin_candidate.html'),
    dict(id='harness', item='完整线束', status='BLOCKED', owner='机械＋硬件线材输入',
         detail='IMU两半束各有18条独立可行候选，但324个配对均未满足3.1mm预留间距；完整线束仍未闭合。J10端约5.3mm轴向空间未找到满足预设6mm弯曲半径的路线。头部服务环、FFC、固定点和拆装余量仍缺。',
         evidence='HARDWARE_INPUT_REQUEST.md'),
    dict(id='hardware_selection', item='未定采购件与安装', status='BLOCKED', owner='机械＋硬件；路线/扩展交接待确认',
         detail='轮胎105×18mm仍是占位，商品、胎圈和防滑脱配合未定；采购路线已提问。充电模块、制动电阻、保险及座、断电/物理急停、维护托架联锁、端子和线材仍待硬件确定。',
         evidence='MECHANICAL_PURCHASE_REQUIREMENTS.md'),
    dict(id='supplier_interfaces', item='传动与插接资料', status='BLOCKED', owner='厂家资料＋机械/硬件',
         detail='SCS0009匹配舵盘及短轴/锁紧叠层、S288输出自攻螺钉规格、WeAct E成品孔/针与有效插接长度仍缺。已整理可在到货前询问的清单，尚未联系供应商。',
         evidence='SUPPLIER_DATA_REQUEST.md'),
    dict(id='load_budget', item='质量与驱动预算', status='BLOCKED', owner='机械＋硬件工作点',
         detail='当前名义估算约1.323kg，超过1.0–1.2kg目标，且缺未选模块和完整线束。现有390姿态与载荷情景计算已更新；S288在9V的连续能力仍无资料，不能用堵转转矩放行。',
         evidence='ENGINEERING.md'),
    dict(id='physical_validation', item='实物与打印验证', status='NOT_TESTED', owner='到货/试件后',
         detail='CAM/相机照片估计细节、喇叭安装耳、电池与出线、排针排母实际插接、PA12配合和紧固、承载/蠕变/冲击、声学、温升与平衡需实物。',
         evidence='../../reports/组装与打印.md'),
]
work = dict(objective='在拿到实物之前，先把能做的都做了', revision=revision,
            source_blend_sha256=source_hash, updated_utc=datetime.now(timezone.utc).isoformat(),
            geometry_equivalence='interface_sync/source_equivalence.json',
            status='BLOCKED', status_scope='Remaining design/data decisions; this is not goal status or a claim all digital work is complete',
            manufacturing_release=False, completed=[
                dict(id='rear_mesh', status='PASS', detail='Head_Rear旧接缝残面已修复；21/21候选STL拓扑通过，独立范围审计通过。'),
                dict(id='geometry_delivery', status='PASS', detail='主模型、电子细模、STL与渲染同源；原有检查集123 PASS、0 FAIL、17 BLOCKED、19 NOT_TESTED，不包含新增反力夹口专项失败。'),
                dict(id='animation', status='PASS', detail='M1.46-A1，82.5秒、1980帧、22章；源模型一致，仍是无完整线束的装配示意。'),
                dict(id='engineering_calculation', status='PASS', detail='209个当前实体质量覆盖、390姿态、惯量及载荷情景已计算；目标/能力未获放行。'),
                dict(id='interface_document', status='PASS', detail='轮轴及已完成事项的旧交接信息已修正；两次重建218个零件几何/位置保持，216个源对象及211个动画对象严格对比通过。'),
            ], additional_checks=dict(report='thin_candidate_service.json',
                counts={s: sum(x['status'] == s for x in service['checks']) for s in ['PASS', 'FAIL', 'NOT_TESTED']},
                scope='Independent candidate service checks; main reaction-link failure reproduced in reaction_service_sections.json and reaction_link_entry_baseline.json. Not merged into the earlier general validation count.'), remaining=remaining)
writej(HERE / 'work_status.json', work)

# Keep the six previously accepted fixes and record new unresolved work explicitly.
status_path = M / 'reports/interface_completion_status.json'
status = readj(status_path)
status.update(revision=revision, source_blend_sha256=source_hash, project_digital_release='BLOCKED')
status['pending'] = [dict(item='7', status='BLOCKED', detail='P5R7已应用；E方针/原厂STEP孔矛盾与真实啮合仍待厂家资料。')] + remaining
status['current_work_status'] = '../studies/prearrival_finish/work_status.json'
writej(status_path, status)

whole = eng['totals']['whole']
max_pitch = max(x['pitch_gravity_Nm'] for x in eng['head_poses'])
engineering_md = f'''# M1.46 当前质量与载荷计算

模型：`{source_hash}`。结果由 [engineering_current.py](engineering_current.py) 从当前209个模型实体计算，原始数据见 [engineering_current.json](engineering_current.json)。几何及算术覆盖检查 PASS；整机质量目标和执行器资格仍为 BLOCKED。

| 项目 | 当前名义估算 |
|---|---:|
| 整机已建模质量 | {whole['mass_g']/1000:.3f} kg |
| 其中本体打印件 | {eng['totals']['prints']['mass_g']:.1f} g |
| 俯仰运动总成 | {eng['totals']['pitch']['mass_g']:.1f} g |
| Yaw运动总成（含俯仰总成） | {eng['totals']['yaw']['mass_g']:.1f} g |
| 零位重心高度 | {whole['COM_mm'][2]:.2f} mm |
| 重心高于轮轴 | {whole['COM_mm'][2]-52.5:.2f} mm |
| 390个姿态中最大俯仰重力矩 | {max_pitch:.5f} N·m |

这些是模型体积、参考密度与明确估算质量的组合，未称重。PA12使用参考实心材料密度，没有假定FDM低填充率。扬声器的31.5g沿用为预算估算，不是当前SP3040的厂家重量；电池、核心板、线材等质量也须按记录更新。

原1.0–1.2kg工程目标尚未达成；当前约高于目标区间上沿123g，且尚未计入未定充电模块、制动电阻及隔热固定、保险座和完整线束。MORI_SPEC_V1_2.md第58行要求超出后重做动力预算，并未将1.2kg设为已证实承重上限。应先补齐硬件方案与质量输入，再决定是否减重或调整工作点；不能把123g当成已经确定的减重指标。轮胎仍未选型，当前单只约44.5g也是估算。当前没有擅自削薄零件或改电机。

本次接口文档同步后已重建模型；全部源对象和动画源几何等价，因此原计算结果仍适用于当前模型，见[严格等价记录](interface_sync/source_equivalence.json)。原JSON保留真实计算时的模型哈希，没有改写成重新计算过。

## 已算的载荷情景

组合Yaw/Pitch与机身前后倾角，共390姿态；俯仰和Yaw使用各自工作空间的最大采样轴惯量。角加速度取1、5、10、20rad/s²。敏感性情景加入35%质量偏差、10/15g头部线束、0.01N·m摩擦/线缆阻力及0.5m/s²机身加速度。20rad/s²时，俯仰约0.03236N·m，Yaw约0.03128N·m。

SCS0009原A/0表中4.8V、0.65kgf·cm约0.06374N·m仅作资料比较；持续占空比、传动界面、线缆阻力及控制瞬态未定，不能把比值当作安全系数。轮驱计算覆盖0.25/0.5/1m/s²、0/5/10°坡度，并另列40g线束情景；没有计入已验证的平衡控制余量，S288在9V的连续转矩/热能力仍需厂家资料。

35%和40g只是敏感性假设，不是未选部件质量或冲击载荷的上界。PA12强度、疲劳/蠕变、紧固、温升和动态平衡仍须各自验证。来源记录保存在原始JSON、[供应商问题单](SUPPLIER_DATA_REQUEST.md)及项目原始规格文件。
'''
(HERE / 'ENGINEERING.md').write_text(engineering_md)

rows = ''.join(f'<tr><td>{html.escape(x["item"])}</td><td>{x["status"]}<br>{html.escape(x["owner"])}</td><td>{html.escape(x["detail"])} <a href="{x["evidence"]}">依据／下一步</a></td></tr>' for x in remaining)
style = '''*{box-sizing:border-box}body{margin:0;background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1150px;margin:auto;padding:30px 22px 70px}h1{font-size:32px}h2{margin-top:32px}a{color:#146c53}.notice{padding:18px;background:#fff1d5;border:1px solid #dec59d;border-radius:10px}.links{display:flex;flex-wrap:wrap;gap:16px}table{width:100%;border-collapse:collapse}td,th{padding:14px;border-bottom:1px solid #c4d1c9;text-align:left;vertical-align:top}td:first-child{min-width:135px}img{width:100%}details{background:#fff;padding:16px;margin:14px 0;border-radius:9px}summary{cursor:pointer;font-weight:600}@media(max-width:750px){table,tbody,tr,td{display:block}th{display:none}td{padding:8px;border:0}tr{border-bottom:1px solid #c4d1c9;padding:10px 0}h1{font-size:26px}}'''
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.46 · 到货前剩余工作</title><style>{style}</style><main>
<a href="../../index.html?revision={revision}">返回主模型</a><h1>到货前仍有设计与资料缺项</h1>
<p>M1.46 · 板卡为运动/后接口P5R7、电源P5R6、IMU P5R4 · 本体16件打印件</p>
<p class="notice">还不能表述为“只等实物”。新增反力夹口初装检查发现明确阻挡，原有主模型也已复现。后壳网格已修复，模型、STL和视频已同步，但薄边候选、完整线束、未定采购件、传动资料与质量目标仍未关闭。薄边候选尚未替换主模型；扩展硬件问题单尚未发送。</p>
<h2>剩余项目</h2><table><tr><th>项目</th><th>状态／所需条件</th><th>具体缺口</th></tr>{rows}</table>
<h2>本轮已完成的工作</h2><ul><li>Head_Rear历史接缝处非流形残面修复，名义壳厚、孔轴和硬件位置保持。21/21候选STL拓扑通过。</li><li>原有检查集：123 PASS / 0 FAIL / 17 BLOCKED / 19 NOT_TESTED。新增拆装专项为9 PASS / 3 FAIL / 1 NOT_TESTED，失败集中在反力夹口初装及工具路线；未合入原计数。</li><li>装配视频M1.46-A1更新完成：82.5秒、1980帧、22章，与当前模型一致；夹口仍按已预装总成演示，未证明可初装。</li><li>当前质量、重心、惯量和390姿态载荷情景已重算，明确列出缺失输入。</li><li>机械交接文档的旧轮轴尺寸和已完成事项已校正，改为引用当前唯一参数源。两次重建及216个源对象对比通过；几何、硬件位置和视频内容均保持。</li><li>三处薄边局部修正候选已完成范围、连通性、130姿态及轮驱服务路径检查，等待用户选择；不代表夹口装配通过。</li></ul>
<div class="links"><a href="reaction_assembly_review.html">反力夹口装配阻挡</a><a href="thin_candidate.html">三处薄边对比</a><a href="ENGINEERING.md">质量与载荷说明</a><a href="MECHANICAL_PURCHASE_REQUIREMENTS.md">轮胎等采购接口</a><a href="HARDWARE_INPUT_REQUEST.md">硬件问题单</a><a href="SUPPLIER_DATA_REQUEST.md">供应商资料清单</a><a href="../../animation/index.html?revision=V1.2-M1.46-A1">当前装配视频</a></div>
<details><summary>线束为何还未关闭</summary><p>原有路线分别检查能通过，组合后有四处交叉占位。新的联合路径搜索尚未找到同时满足全部间距与预设弯曲半径的组合；这不是不存在可行路线的证明。</p><p>H05在J10端的出线分区距端面2.4mm处，沿轴再约5.3mm便遇到Yaw_Base。有限搜索找到过约3.56mm最小曲率半径的候选，但没有满足预设6mm；尚未选线材，不能把它当作允许弯曲值。没有为避开此处而移动PCB或切承重桥。</p><p>IMU两半束各搜索4392个方案，各找到18条避开实体的独立路线；324个配对均没有满足3.1mm中心线预留间距。这里的每束直径2.8mm、弯曲半径6mm仍是分配值，未选定实物线材；没有缩小分配值来把失败改为通过。头部服务环、端子后直段、FFC接触面和固定点也还未定。</p><a href="terminal_bend_capacity.json">J10空间数据</a> · <a href="static_route_set.json">联合路线结果</a> · <a href="imu_joint_routes.json">最新IMU双束结果</a></details>
<details><summary>检查证据与命令</summary><p>主模型SHA256：<code style="word-break:break-all">{source_hash}</code></p><div class="links"><a href="rear_repair_audit.json">后壳修复范围</a><a href="../../reports/validation.json">主模型检查</a><a href="../../reports/export_manifest.json">21件STL记录</a><a href="../../reports/delivery_consistency.json">交付一致性</a><a href="../../animation/delivery.json">动画来源</a><a href="geometry_commands.json">实际生成命令</a><a href="interface_sync/source_equivalence.json">文档同步前后几何等价</a><a href="interface_sync/delivery_commands.json">本次复核命令</a><a href="work_status.json">结构化状态</a></div><p>Blender 5.2.2 LTS；候选文件与历史失败尝试单独保留。通用几何检查的0 FAIL不表示薄壁、选型和全部线束完成。</p></details>
<p>PROTOTYPE / UNVALIDATED · 未采购、未下单打印、未制造放行。</p></main></html>'''
(HERE / 'index.html').write_text(page)

# Update current navigation and summaries; retain historical reports as historical evidence.
index = M / 'index.html'
t = index.read_text().replace('V1.2-M1.45', revision)
t = t.replace('M1.45-A1', 'M1.46-A1')
t = t.replace('<h1>P5R7 已应用到主模型。</h1>', '<h1>P5R7已应用，后壳网格已修复。</h1>')
t = t.replace('studies/prearrival_closure/index.html', 'studies/prearrival_finish/index.html')
t = t.replace('本次板卡报告', '此前P5R7板卡报告')
t = t.replace('三个原对象更新，新增四个采购参考对象；全部打印件的网格与位置均保持。', 'M1.45板卡应用更新三个原对象并新增四个采购参考对象；M1.46仅修复Head_Rear历史接缝残面，保留全部名义接口与硬件位置。')
remaining_main = '<section id="remaining"><h2>仍需完成</h2><p class="notice">除了实物验证，还有反力夹口初装阻挡、薄边候选待确认、线束、未定采购件、厂家接口资料及质量/驱动预算。<a href="studies/prearrival_finish/index.html">查看到货前剩余工作与依据</a>。</p><table>'
for x in remaining:
    remaining_main += f'<tr><td>{html.escape(x["item"])}</td><td>{x["status"]}</td><td>{html.escape(x["detail"])}</td></tr>'
remaining_main += '</table></section>'
t, n = re.subn(r'<section id="remaining">.*?</section>', remaining_main, t, flags=re.S)
assert n == 1
checks = '''<section id="checks"><h2>当前检查</h2><p>原有检查集：123 PASS / 0 FAIL / 17 BLOCKED / 19 NOT_TESTED。新增候选拆装专项：9 PASS / 3 FAIL / 1 NOT_TESTED；反力夹口的螺钉、工具与预装穿入未通过，主模型也已复现，尚未合入原计数。P5R7应用范围及原厂坐标复核通过，E孔针资料矛盾仍为BLOCKED。</p><p>装配视频V1.2-M1.46-A1已同步，82.5秒、22章；保留上壳与桥独立运动及转60°锁防脱压板的步骤。夹口按已预装总成展示，不能作为初装证明。</p><p class="notice">21/21候选STL拓扑通过（含托架与试片）。三处薄边候选尚未应用；夹口初装、完整线束、未选采购件、传动资料与质量目标仍未关闭。以上几何检查不等于打印、采购或整机能力放行。</p><div class="links"><a href="reports/validation.json">原有主检查集</a><a href="studies/prearrival_finish/reaction_assembly_review.html">新增装配阻挡</a><a href="studies/prearrival_finish/rear_repair_audit.json">后壳修复审计</a><a href="studies/prearrival_finish/index.html">本轮剩余工作</a><a href="reports/export_manifest.json">STL清单</a><a href="studies/prearrival_finish/geometry_commands.json">生成命令</a></div></section>'''
t, n = re.subn(r'<section id="checks">.*?</section>', checks, t, flags=re.S)
assert n == 1
index.write_text(t)

p = M / 'manufacturing.html'
t = p.read_text().replace('V1.2-M1.45', revision)
t = t.replace('打印件保持M1.44的16件，首轮PA12。新增排母和E排针是采购参考件。Head_Rear原有6条非流形边仍待处理，STL已隔离；本次未改变打印件。未进行采购或打印下单。', '本体仍为16件打印件，首轮PA12。M1.46修复Head_Rear历史接缝残面；含托架/试片的21件STL拓扑均通过。三处薄边修正候选尚未应用，完整线束与若干接口仍未关闭；没有进行采购或打印下单。<a href="studies/prearrival_finish/index.html">查看当前剩余工作</a>。')
t = t.replace('FAIL：STL拓扑未通过，已隔离', '<a href="exports/stl/Head_Rear.stl">候选 STL（M1.46拓扑通过）</a>')
t = t.replace('exports/printable/Head_Rear.stl', 'exports/stl/Head_Rear.stl')
p.write_text(t)
p = M / 'parts.html'
p.write_text(p.read_text().replace('V1.2-M1.45', revision))

(M / 'README.md').write_text(f'''# MORI {revision}

P5R7已应用；16件本体打印件和M1.44防脱方案保持。M1.46修复Head_Rear历史接缝网格，21/21候选STL拓扑通过；装配视频已更新为M1.46-A1。

[主模型](mori_v1_2.blend) · [到货前剩余工作](studies/prearrival_finish/index.html) · [逐元件电子模型](mori_electronics_detail.blend) · [装配动画](animation/index.html) · [打印说明](reports/组装与打印.md)

新增反力夹口初装检查发现阻挡，主模型也已复现；视频中的预装状态不能证明此处可装入。三处薄边候选尚待确认；完整线束、轮胎等未定采购件安装、舵盘/E针孔资料、质量及驱动预算尚未关闭。当前不能描述为只剩实物验证。PROTOTYPE / UNVALIDATED；未制造放行。
''')

report = f'''# MORI {revision} · 组装与候选打印文件

主模型SHA256：`{source_hash}`。当前板卡：运动及后接口P5R7、电源P5R6、IMU P5R4（20×16mm、两孔）。WeAct元件面朝上、四组排针朝下；11.04mm是候选叠层，E针孔资料矛盾未获豁免。历史应用细节见[P5R7报告](P5R7应用_M1_45.md)。

## 本轮变化与交付

- 修复Head_Rear历史接缝处的非流形残面。名义母壳、孔轴、壳厚及硬件位置保持；改动范围由[独立几何审计](../studies/prearrival_finish/rear_repair_audit.json)记录。
- 16件本体打印件保持；含维护托架和试片，共21件候选STL拓扑通过。[实际导出记录](export_manifest.json)包含文件hash与重导入检查。
- 原有主检查集123 PASS / 0 FAIL / 17 BLOCKED / 19 NOT_TESTED；新增候选拆装专项9 PASS / 3 FAIL / 1 NOT_TESTED，尚未合入原计数。夹口初装阻挡在主模型中也已复现。完整模型、电子细模、渲染及导出一致性通过，仅代表同源交付。
- 装配视频[ M1.46-A1 ](../animation/index.html)已同步：82.5秒、1980帧、22章。保持上壳与承重桥独立支承、转60°安装防脱压板和小舵机离机预装的步骤。
- 质量/惯量/载荷按当前模型更新；说明见[工程估算](../studies/prearrival_finish/ENGINEERING.md)。
- 本次机械接口文档同步后两次重建通过，216个源对象、211个动画对象几何严格等价；沿用原渲染和计算，原始报告保留真实来源。见[等价证明](../studies/prearrival_finish/interface_sync/source_equivalence.json)。

## 打样前仍未关闭

1. 反力夹口的螺钉装入、直柄工具与预装穿入路线受头座阻挡，有限倾斜搜索也未找到完整路径。需结合最终舵盘接口解决；[具体剖面与检查](../studies/prearrival_finish/reaction_assembly_review.html)。当前动画仍按已预装总成演示。
2. 三处薄边修正候选待用户确认；目前没有写入主模型或打印文件。详见[剖面对比](../studies/prearrival_finish/thin_candidate.html)。候选不解决上一项初装问题。
3. 完整线束尚未布通并联合验证；IMU两分束各18条独立路线的324个配对均未满足预留间距。固定点、弯曲、头部服务环和插拔余量仍缺；不要据视频中的示意线下单线束。
4. 轮胎105×18mm仍是占位，须确定采购路线、胎圈及防滑脱配合；[机械采购接口](../studies/prearrival_finish/MECHANICAL_PURCHASE_REQUIREMENTS.md)已列出。充电模块、制动电阻、保险座、断电/物理急停及托架联锁须由硬件确定，再完成对应安装；扩展问题单尚未发送。
5. SCS0009舵盘/短轴/锁紧、S288自攻输出螺钉、WeAct E孔针与接触长度缺完整资料。厂家问题单可以在到货前处理。
6. 当前估算约1.323kg已超过1.0–1.2kg目标，且不含全部未选部件；驱动连续能力不能以堵转数据代替。

完整状态与证据见[到货前收尾页](../studies/prearrival_finish/index.html)。PA12试配、嵌件/螺母装入、实际耳厚和线头、强度/蠕变、热与动态平衡仍需实物。拓扑通过只证明相应网格检查通过；当前仍为PROTOTYPE / UNVALIDATED，不是完整装配或制造放行。
'''
(M / 'reports/组装与打印.md').write_text(report)
(M / 'reports/到货前收尾_M1_46.md').write_text(report)
print(json.dumps(dict(revision=revision, source_hash=source_hash, pages_updated=True, candidate_applied=False), ensure_ascii=False))
