# -*- coding: utf-8 -*-
"""Publish approved M1.47 edits only after current geometry/video readback passes."""
from pathlib import Path
import datetime
import hashlib
import html
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
M = HERE.parents[1]
PROJECT = M.parent


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


revision = read(PROJECT/'config/geometry.json')['revision']
assert revision == 'V1.2-M1.47'
sha = digest(M/'mori_v1_2.blend')
audit = read(M/'reports/approved_thin_cleanup_validation.json')
validation = read(M/'reports/validation.json')
exports = read(M/'reports/export_manifest.json')
animation = read(M/'animation/manifest.json')
av = read(M/'animation/validation.json')
delivery = read(M/'reports/delivery_consistency.json')
eng = read(HERE/'engineering_current.json')
reaction = read(HERE/'reaction_service_sections_M1_47.json')
assert audit['status'] == eng['status'] == av['status'] == delivery['status'] == 'PASS'
assert all(d['source_blend_sha256'] == sha for d in [audit, animation, eng, reaction])
assert animation['rendered_video'] and animation['animation_revision'] == revision+'-A1'
assert validation['counts']['FAIL'] == 0
assert exports['exported_count'] == exports['candidate_count'] == 21
assert all(p['status'] == 'PASS' for p in exports['parts'])
assert set(audit['changed_ids']) == {'Pitch_Yoke', 'Motor_Retainer', 'Drive_Bridge'}
assert audit['reaction_link_unchanged'] and not audit['new_ids'] and not audit['retired_ids']
assert reaction['tool_intersection_mm3'] > 0 and reaction['straight_lift_2mm_intersection_mm3'] > 0
assert read(M/'reports/head_retention_body_sequence.json')['status'] == 'PASS'

history = HERE/'history_M1_46_publication'
history.mkdir(exist_ok=True)
for filename in ['work_status.json', 'index.html', 'thin_candidate.html', 'ENGINEERING.md']:
    if not (history/filename).exists():
        shutil.copy2(HERE/filename, history/filename)

work = read(history/'work_status.json')
remaining = [row for row in work['remaining'] if row['id'] != 'thin_features']
for row in remaining:
    if row['id'] == 'reaction_assembly':
        row['detail'] = '反力夹口局部薄边及初装仍未修复。M1.47当前实体复核：直柄工具与头座相交约9.26mm³，反力件上移2mm与头座相交约18.13mm³；只是两条具体路线失败，不表示不存在其他方案。未采用失败的夹口候选；最终舵盘资料仍缺。'
    elif row['id'] == 'hardware_selection':
        row['owner'] = '机械＋硬件对话；现成软轮胎路线已确认'
        row['detail'] = '厂家目录筛选已完成：BaneBots101.6×20.32mm外形接近，但金属转接/定位接口、重量范围及国内交付未定，尚未替换105×18mm占位轮。扩展电气问题单已发送，并收到A2分项资料；J10侧出候选电气FAIL、机械包络也有阻挡，未替换正式板卡。'
        row['evidence'] = 'tyre_selection/index.html'
    elif row['id'] == 'load_budget':
        row['detail'] = f'当前名义估算{eng["totals"]["whole"]["mass_g"]/1000:.3f}kg，超过1.0–1.2kg工程目标，尚缺未选模块及完整线束。已按M1.47重算390姿态和载荷情景；S288在9V连续能力仍缺资料。'
    elif row['id'] == 'harness':
        row['detail'] = '完整线束尚未闭合。A2已补线规和外径/弯曲参考；旧R6分束搜索不代表新线材符合。J10侧出插合、12mm直拔及5mm出线分配扫到板上器件；还需联合布置。头部FFC厚度、弯曲和应力释放待完成。'
        row['evidence'] = 'J10_A2_REVIEW.md'

work.pop('geometry_equivalence', None)
work.update(revision=revision, source_blend_sha256=sha,
            updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            status='BLOCKED', status_scope='Remaining project design/data gaps; this is not the goal tool status',
            manufacturing_release=False, remaining=remaining,
            approved_scope=dict(local_cleanups='PASS', stock_tyre_screening='PASS',
                                tyre_selection='BLOCKED', hardware_request_sent=True,
                                hardware_thread_id='01a0c24f-ddc2-7f03-a9d4-d09dff26d30f'))
work['completed'] = [
    dict(id='approved_cleanup', status='PASS', detail='取消废弃转台孔槽；轮驱底盖轴承座18→19.2mm且上座同步。3件与审核候选完全一致，206件其余实体几何和位置保持，零件数量不变。'),
    dict(id='geometry_delivery', status='PASS', detail='主模型、STL、当前全部渲染及电子细模同步；主检查124 PASS / 0 FAIL，17 BLOCKED / 19 NOT_TESTED仍保留。21/21候选STL拓扑通过。'),
    dict(id='animation', status='PASS', detail='M1.47-A1，82.5秒、1980帧、22章，源模型及路径回读通过；反力夹按预装总成演示的限制保留。'),
    dict(id='engineering', status='PASS', detail='209实体质量覆盖及390姿态计算已基于M1.47重算；质量目标与执行器资格未获放行。'),
    dict(id='tyre_research', status='PASS', detail='4类具名厂家产品已比对，尺寸及未知接口分开记录；没有套用其他产品尺寸或改变主轮径。'),
    dict(id='hardware_handoff', status='PASS', detail='扩展电气输入清单已发送到既有硬件对话，并收到A2分项资料；16个正式原生PCB文件哈希保持。J10失败候选的独立机械包络筛查已完成，未应用。'),
]
work['additional_checks']['current_main_recheck'] = 'reaction_service_sections_M1_47.json'
work['additional_checks']['scope'] = 'Historical isolated candidate service checks retained; two explicit failed reaction approaches rechecked on M1.47, not included in general validation count.'
write(HERE/'work_status.json', work)

execution = read(HERE/'approval_execution.json')
execution.update(status='PASS', phase='approved_edits_delivered_and_checked',
                 source_blend_sha256=sha, geometry_validation='../../reports/approved_thin_cleanup_validation.json',
                 final_utc=work['updated_utc'], animation_revision=animation['animation_revision'],
                 tyre_screening='tyre_selection/REVIEW.md', tyre_selection_status='BLOCKED',
                 scope='PASS concerns two approved geometry edits and their delivery, stock-product screening and hardware message dispatch; not complete project readiness')
write(HERE/'approval_execution.json', execution)

status_path = M/'reports/interface_completion_status.json'
status = read(status_path)
status.update(revision=revision, source_blend_sha256=sha, project_digital_release='BLOCKED')
status['pending'] = [dict(item='7', status='BLOCKED', detail='P5R7已应用；E方针/原厂STEP孔矛盾与真实啮合仍待厂家资料。')] + remaining
status['current_work_status'] = '../studies/prearrival_finish/work_status.json'
write(status_path, status)

style = '''*{box-sizing:border-box}body{margin:0;background:#edf1f0;color:#243a33;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1120px;margin:auto;padding:32px 22px 70px}h1{font-size:32px}h2{margin-top:32px}a{color:#146c53}.notice{padding:18px;background:#fff1d5;border:1px solid #dec59d;border-radius:10px}.done{background:#dcece3;border-color:#a5c6b1}.links{display:flex;flex-wrap:wrap;gap:16px}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #c4d1c9;text-align:left;vertical-align:top}td:first-child{min-width:140px}img{width:100%;background:white;border:1px solid #c5d2ca;border-radius:8px}details{background:#fff;padding:16px;margin:14px 0;border-radius:9px}summary{cursor:pointer;font-weight:600}code{word-break:break-all}@media(max-width:750px){table,tbody,tr,td{display:block}th{display:none}td{padding:8px;border:0}tr{border-bottom:1px solid #c4d1c9;padding:10px 0}h1{font-size:26px}}'''
rows = ''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{r["status"]}<br>{html.escape(r["owner"])}</td><td>{html.escape(r["detail"])} <a href="{r["evidence"]}">依据</a></td></tr>' for r in remaining)
completed = ''.join('<li>'+html.escape(row['detail'])+'</li>' for row in work['completed'])
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI M1.47 · 已确认的两处修正</title><style>{style}</style><main>
<a href="../../index.html?revision={revision}">返回主模型</a><h1>两处修正已应用</h1>
<p>M1.47 · 本体16件打印件 · 运动/后接口P5R7，电源P5R6，IMU P5R4</p>
<p class="notice done">已按确认的推荐执行：应用两处局部修正、先筛选现成软轮胎、将扩展电气要求发送给硬件对话。Blender、STL、预览及装配视频已同步。</p>
<h2>1. 取消废弃孔槽</h2><p>转台与U托合并后，旧连接孔和螺母通道已无用途。本次从生成源头取消，消除约0.04mm的残边；轴颈、轴承和限位保持。以下右图就是已采用的实体，当前模型与候选的实体差为0。</p><img src="approved_M1_47_yoke.png" alt="废弃孔槽修正对比，右侧方案已应用">
<h2>2. 加宽轮驱底盖轴承座</h2><p>轴承座深度18→19.2mm，两侧各增加0.6mm，对应上座调整装入间隙。保持原轮轴及紧固件，未增加打印件或凸耳。底盖拆卸、轮驱拆装和工具路径检查通过。</p><img src="approved_M1_47_cap.png" alt="轴承座加宽剖面对比，右側方案已应用">
<p><a href="../../reports/approved_thin_cleanup_validation.json">改动范围与候选实体对比</a> · <a href="../../mori_v1_2.blend">当前Blender</a> · <a href="../../animation/index.html?revision={revision}-A1">更新后的装配视频</a></p>
<h2>3. 轮胎与电气输入</h2><p>现成轮胎已完成首轮厂家筛选，尚未找到尺寸与接口均可直接沿用的型号。最接近的BaneBots成品轮仍需中心接口、重量范围和国内采购资料；<a href="tyre_selection/index.html">查看产品对比</a>。主模型轮径仍为105mm。</p><p>充电、电阻、保险、断电/物理急停、维护托架联锁、线材端子及FFC要求已发给“建立 MORI 硬件开发项目”对话，<a href="HARDWARE_INPUT_REQUEST.md">清单与发送状态</a>已记录。现已收到<a href="hardware_A2_receipt.json">A2增补</a>，<a href="J10_A2_REVIEW.md">J10独立空间筛查</a>仍发现板上阻挡，正式板卡保持不变。</p>
<h2>仍需完成</h2><p class="notice">反力夹口的薄边与初次装入问题仍未关闭，本次没有采用失败的夹口候选。其余线束、未选元件、厂家传动/插接资料和质量预算仍需完成，不能表述为“只等实物”。</p><table><tr><th>项目</th><th>状态／责任</th><th>具体缺口</th></tr>{rows}</table>
<details><summary>本轮检查与生成依据</summary><ul>{completed}</ul><p>当前模型SHA256：<code>{sha}</code></p><div class="links"><a href="../../reports/validation.json">主检查集</a><a href="../../reports/export_manifest.json">STL清单</a><a href="../../reports/delivery_consistency.json">交付一致性</a><a href="../../animation/validation.json">动画回读</a><a href="reaction_service_sections_M1_47.json">当前反力夹阻挡</a><a href="geometry_commands.json">实际命令</a><a href="work_status.json">结构化状态</a><a href="ENGINEERING.md">当前载荷计算</a></div></details>
<p>PROTOTYPE / UNVALIDATED · 几何检查不等于PA12强度、实际配合或整机能力放行。</p></main></html>'''
(HERE/'index.html').write_text(page)

# Keep the original combined proposal as historical comparison, visibly mark partial adoption.
old = (history/'thin_candidate.html').read_text()
old = old.replace('三处局部修正 · 尚未应用', '历史三处候选 · 第1、3项已应用')
old = old.replace('候选在独立目录生成，主模型仍是 M1.46。', '这是M1.46时的完整独立候选。当前M1.47仅采用下述第1、3项，反力夹第2项未采用。')
old = old.replace('此前三处一起应用的待确认方案，请结合此项新结果审阅。', '用户已确认只先采用第1、3项；<a href="index.html">查看当前交付</a>。')
old = old.replace('接受后还需纳入完整装配、导出和动画复核', '第1、3项已纳入M1.47检查和交付，夹口仍未闭合')
(HERE/'thin_candidate.html').write_text(old)

index = M/'index.html'
t = index.read_text()
t = t.replace('V1.2-M1.46', revision)
t = t.replace('MORI M1.46', 'MORI M1.47').replace('MORI V1.2-M1.46', revision)
t = re.sub(r'<h1>.*?</h1>', '<h1>两处薄边已修正，P5R7保持。</h1>', t, count=1, flags=re.S)
t = t.replace('M1.46仅修复Head_Rear历史接缝残面，保留全部名义接口与硬件位置。', 'M1.46修复Head_Rear历史接缝残面；M1.47取消废弃转台孔槽并加宽轮驱轴承座，保留硬件位置与零件数量。')
main_rows = ''.join(f'<tr><td>{html.escape(r["item"])}</td><td>{r["status"]}</td><td>{html.escape(r["detail"])}</td></tr>' for r in remaining)
remaining_html = '<section id="remaining"><h2>仍需完成</h2><p class="notice">两处已确认修正完成，电气要求已发送。反力夹初装、线束、最终轮胎选型、厂家接口资料与质量预算仍待完成。<a href="studies/prearrival_finish/index.html">本轮交付与剩余工作</a>。</p><table>'+main_rows+'</table></section>'
t, n = re.subn(r'<section id="remaining">.*?</section>', lambda _:remaining_html, t, flags=re.S)
assert n == 1
checks_html = f'''<section id="checks"><h2>当前检查</h2><p>M1.47主检查集：124 PASS / 0 FAIL / 17 BLOCKED / 19 NOT_TESTED。3件修改与审核候选一致，其余206件实体几何和位置保持。21/21候选STL拓扑通过。</p><p>装配视频{revision}-A1已同步。反力夹口仍按预装总成展示；专项复核的工具及装入阻挡保留，不包含在上述通用检查计数中。</p><p class="notice">当前仍有设计/资料缺口，未制造放行。<a href="studies/prearrival_finish/index.html">查看两处修正与全部剩余项</a>。</p><div class="links"><a href="reports/approved_thin_cleanup_validation.json">修改范围</a><a href="reports/validation.json">主检查集</a><a href="reports/delivery_consistency.json">交付一致性</a><a href="studies/prearrival_finish/tyre_selection/index.html">轮胎筛选</a></div></section>'''
t, n = re.subn(r'<section id="checks">.*?</section>', lambda _:checks_html, t, flags=re.S)
assert n == 1
index.write_text(t)

(M/'README.md').write_text(f'''# MORI {revision}

已应用两处经确认的修正：取消废弃转台连接孔槽，轮驱底盖轴承座深度18→19.2mm且上座配合间隙同步。仅改变Pitch_Yoke、Motor_Retainer、Drive_Bridge；16件本体打印件、P5R7和M1.44防脱方案保持。

[主模型](mori_v1_2.blend) · [本轮交付与剩余项](studies/prearrival_finish/index.html) · [逐元件电子模型](mori_electronics_detail.blend) · [装配动画](animation/index.html) · [轮胎筛选](studies/prearrival_finish/tyre_selection/index.html)

主检查124 PASS / 0 FAIL；17 BLOCKED和19 NOT_TESTED仍保留。21/21候选STL拓扑通过，装配视频{revision}-A1与当前模型同步。独立反力夹口初装/工具检查仍有阻挡，视频预装状态不构成初装证明。最终轮胎、完整线束、传动/插接资料、质量和驱动预算未关闭。扩展电气输入已发送给既有硬件对话。PROTOTYPE / UNVALIDATED；未制造放行。
''')

# Recompute displayed figures from this revision; never relabel old calculation hashes.
whole = eng['totals']['whole']
max_pitch = max(r['pitch_gravity_Nm'] for r in eng['head_poses'])
scenarios = {r['axis']:r for r in eng['head_scenarios'] if r['acceleration_rad_s2'] == 20}
(HERE/'ENGINEERING.md').write_text(f'''# M1.47 当前质量与载荷计算

[原始计算](engineering_current.json)来自当前模型SHA256 `{sha}`；209个实体、390姿态。算术与覆盖检查PASS，质量目标和执行器能力仍BLOCKED。

| 项目 | 名义估算 |
|---|---:|
| 整机已建模质量 | {whole['mass_g']/1000:.3f} kg |
| 本体打印件 | {eng['totals']['prints']['mass_g']:.1f} g |
| 俯仰总成 | {eng['totals']['pitch']['mass_g']:.1f} g |
| Yaw总成（含俯仰） | {eng['totals']['yaw']['mass_g']:.1f} g |
| 零位重心高度 | {whole['COM_mm'][2]:.2f} mm |
| 最大采样俯仰重力矩 | {max_pitch:.5f} N·m |

这是体积、参考密度和估算质量的组合，未称重；PA12按参考实心密度，没有假设FDM低填充率。扬声器31.5g仍是预算分配，并非当前SP3040厂家重量。电池、板卡及线材等需各自校准。

已超出1.0–1.2kg工程目标，且未包括未选充电模块、制动电阻及隔热固定、保险座和完整线束。不能把当前超出的{whole['mass_g']-1200:.1f}g当作完整减重指标或据此推断无法平衡。轮胎仍未选型。

角加速度1/5/10/20rad/s²，另有35%质量偏差、10/15g头部线束、0.01N·m摩擦/线缆阻力、0.5m/s²机身加速度的敏感性情景；20rad/s²时俯仰约{scenarios['pitch']['stress_scenario_Nm']:.5f}N·m、Yaw约{scenarios['yaw']['stress_scenario_Nm']:.5f}N·m。这些不是缺失部件质量或冲击载荷的上界。

SCS0009资料中4.8V、0.65kgf·cm约0.06374N·m只作参考，不能当连续能力或安全系数。轮驱覆盖0.25/0.5/1m/s²、0/5/10°坡度及40g线束情景；S288在9V的连续热/转矩能力、平衡控制余量、真实抓地和动态响应未验证。参见[厂家问题单](SUPPLIER_DATA_REQUEST.md)。
''')

print('M1_47_PUBLISHED', sha, validation['counts'], flush=True)
