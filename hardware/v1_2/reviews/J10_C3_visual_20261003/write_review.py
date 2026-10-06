"""Publish explicit visual-review dispositions; never writes a native PCB."""
from pathlib import Path
import json,csv,hashlib,collections,html
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];R=HERE/'reports'
SRC=ROOT/'hardware/v1_2/j10_routing_C3_20261002'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,j:p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
flags=json.loads((SRC/'reports/changed_route_flags.json').read_text())['flags']
atlas=json.loads((HERE/'atlas_index.json').read_text())
inv=json.loads((R/'invariants.json').read_text());assert inv['status']=='PASS'
answers={}
def note(ids,decision,reason,change=''):
    for ident in ids.split():answers[ident]=(decision,reason,change)
note('C0020','FIXED','原 CHG_N 峰谷折返和近水平尾段改为单一横向通道，保持两端过孔。','V01')
note('C0021','JUSTIFIED_EXCEPTION','0.8128 mm 长线仅有 0.0088 mm 横向差，直接连通实际过孔/既有端点；没有来回折返。')
note('C0022','FIXED','原两段末端相差 0.0571 mm，铜虽相连但外缘有小凸出；已改成同一精确端点。','V08')
note('C0032','JUSTIFIED_EXCEPTION','+5V_CAM 这段直接接入 (31.5976,41.4528) 过孔，未跨器件本体；保留锚点，不增添折点。')
note('C0040 C0041 C0046 C0047','JUSTIFIED_EXCEPTION','同一个 0.1×0.1 mm 单向转角被重复提示。位于 Q11 投影左上外缘；放大倒角的 V02 侵入 Q11 禁布区已撤回。它是一次转弯，不是往返抖动。')
note('C0042 C0043 C0044','FALSE_POSITIVE','R50.2 焊盘内的 0.125 mm 接入线，完全被焊盘铜覆盖；不形成焊盘外抖动或悬空。')
note('C0045','JUSTIFIED_EXCEPTION','直接接入 BAT_ADC 真实过孔 (39.8272,20.9296)，线段微偏离 45°；不新增折点，不改过孔。')
note('C0048','FIXED','Q11/R11 之间原 0.2 mm 偏移改成明确的 0.8 mm 竖向通道，绕开两个本体；V03 直接斜穿方案被禁布规则拒绝。','V11')
note('C0049','JUSTIFIED_EXCEPTION','短末端直接接入过孔 (46.7,21.975)，偏角位于过孔接入处；无局部往返。')
note('C0051','JUSTIFIED_EXCEPTION','F60 电池采样分支从焊盘向外引出，0.2 mm 是采样支路；负载主路径另由粗铜承担。')
note('C0055','JUSTIFIED_EXCEPTION','F70.1 的接入段由真实焊盘中心 (30.5,34.545) 向外接功率线，1.0 mm 宽保持；不是为过 DRC 缩窄主路。')
note('C0056','JUSTIFIED_EXCEPTION','BAT_MON 主干到分支的连续宽铜，网格差使斜率稍偏离 45°；连接角和本体净空经原生规则检查，未额外绕行。')
note('C0057','JUSTIFIED_EXCEPTION','J4.2 的宽铜末端接入实际连接器位置，微偏离 45°，连贯无折回；保留原连接器与支路宽度。')
note('C0058 C0059','FALSE_POSITIVE','0.1414 mm 小段及相邻端点均被 (13,33.4) 同网过孔铜覆盖；没有裸露的细颈或小绕路。')
note('C0060','JUSTIFIED_EXCEPTION','R50.1 从真实焊盘向外接 BAT_MON，0.025 mm 横向差来自焊盘中心；保留直接落点。')
note('C0062 C0063','FALSE_POSITIVE','宽铜分支附近相距 0.1016 mm 的同网端点重复命中筛查；原生铜连续，未形成外缘折返或开路。')
note('C0066','JUSTIFIED_EXCEPTION','R54.1 右侧到 (48,44.8) 的线仍为单一直达过孔的微偏斜段；R54 下方真正的 V 形凹口已另由 V12 消除。','V12')
note('C0067 C0068','FIXED','R54 旁 0.0266 mm 错位接头和 V 形凹口一并移除，支路改在 R54.1 焊盘内汇合，避免在板外铜线形成 45°锐角三叉。','V12')
note('C0069 C0070','FALSE_POSITIVE','0.1414 mm 接入段在 (20.3,46.8) 同网过孔范围内；不是元件间可见折返。')
note('C0071','JUSTIFIED_EXCEPTION','测试点间一条连续的近竖直线，2.9 mm 长仅偏移 0.1 mm，沿空闲通道且无中间折点。')
note('C0072','JUSTIFIED_EXCEPTION','3.6752 mm 长直线的两端纵向差 0.0152 mm；没有抖动，不为对齐截图增添新接点。')
note('C0073','JUSTIFIED_EXCEPTION','直接接入 (12.801599,28.448) 的实际过孔，不改孔位；与邻近器件投影保持分离。')
note('C0074','JUSTIFIED_EXCEPTION','5.1×5.2 mm 单一直线连两端锚点，约 45.56°；偏斜不等于折返。')
note('C0111','FALSE_POSITIVE','C5_VIN 的两个同网端点在宽铜/过孔落区内重叠，原生铜连续；不是不同网间距或开路。')
note('C0136','JUSTIFIED_EXCEPTION','FAULT_N 直接接入 (66.6242,18.2626) 过孔，斜率由真实锚点决定；无 S 形补偿或穿本体。')
note('C0150 C0151 C0152 C0153','JUSTIFIED_EXCEPTION','同一个 M5_EN 单向 0.1×0.1 mm 转角的重复提示。它沿 R60 右下边缘通过；V05 放大转角会切进 R60 投影，已撤回。保持安静反馈电阻位置，未加往返绕路。')
note('C0154','JUSTIFIED_EXCEPTION','R53.1 向右上方外侧直接引出到固定端点，0.025 mm 斜率差来自真实焊盘；未向电阻内部折回。')
assert set(answers)=={f['id']for f in flags} and len(flags)==39
rows=[]
for f in flags:
    d,why,change=answers[f['id']]
    group=next(g for g in atlas['groups']if any(x['id']==f['id']for x in g['flags']))
    rows.append(dict(source_id=f['id'],type=f['type'],net=f['net'],layer=f['layer'],x_mm=f['xy'][0],y_mm=f['xy'][1],decision=d,reason=why,change_id=change,before_image='images/'+group['image'],after_image='images/'+change+'_before_after.png'if change else'UNCHANGED_NATIVE_GEOMETRY',track_uuids=';'.join(f['uuids']),record_status='PASS'))
def csv_write(name,rows):
    with (HERE/name).open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
csv_write('39_flag_dispositions.csv',rows)
legacy_reasons={
 'C0005':'GND 端点为平面/支路接点；重叠铜无孤立反向细线。',
 'C0009':'GND 支路/缝合点的同网铜重叠，不是串行路径折返。',
 'C0013':'PACK_FUSED 宽铜连接 Q90 引脚组并分到保护件；分支不能按只有两个端点的线段识别。',
 'C0036':'+5V_MOTION 电容/输出支路的公共落点，焊盘和第三支路构成真实分叉。',
 'C0037':'M5_SW 开关节点过孔阵列的同网连续铜，未改其关键环路。',
 'C0038':'M5_SW 阵列/焊盘铜重叠，非重复反向绕行。',
 'C0039':'M5_SW 阵列/焊盘铜重叠，非独立未连接尾线。',
 'C0065':'M5_VIN 自身输入引脚与去耦支路交会，第三端为器件焊盘。',
 'C0076':'W_SENSE 在 R21.2 外侧分支到过孔和电阻；不是一根导线转头返回。',
 'C0095':'H_VM 在 Q30 同网引脚组汇流，属于并联引脚扇出。',
 'C0105':'C5_VIN 在 U70 输入引脚/电容分支交会，保留短输入环路。',
 'C0108':'C5_VIN 宽铜总线接入同网焊盘，重叠未形成额外外缘绕行。',
 'C0109':'C5_VIN 同一汇流区的重叠提示；与 C0108 同区，记录分别保留。',
 'C0135':'W_REF 在 U21 引脚外分支，真实焊盘为第三接点，未横穿本体。',
 'C0147':'C5_SW 引脚/过孔阵列公共铜；保留受约束开关回路。',
 'C0148':'C5_SW 阵列同网重叠，不是多余串行反向线。',
 'C0149':'C5_SW 阵列同网重叠，不是开路；不为提示数量拆分开关铜。',
}
assert set(legacy_reasons)=={x['id']for x in atlas['legacy_flags']}
csv_write('17_legacy_branch_dispositions.csv',[dict(source_id=x['id'],type=x['type'],net=x['net'],layer=x['layer'],x_mm=x['xy'][0],y_mm=x['xy'][1],decision='RETAINED_FUNCTIONAL_BRANCH_OR_PAD_COPPER',reason=legacy_reasons[x['id']],image='images/legacy_flags_%02d.png'%(n//6+1),track_uuids=';'.join(x['uuids']))for n,x in enumerate(atlas['legacy_flags'])])
body=json.loads((R/'body_review_final.json').read_text())
refs={
 'C10':'径向电容两脚位于圆形罐体投影内；W_VM 向左、GND 向右径向离开，不穿越另一电容或作贯穿捷径。',
 'C30':'径向电容两脚位于罐体投影内；H_VM 向左、GND 向右离开。背面 H_VM 也沿自身左引脚出罐体投影。',
 'D40':'H_BRAKE_GATE 在 D40 自身端头/焊盘肩部短暂进入 Fab 边界；从其端头离开，不沿二极管中心贯穿。',
 'J10':'侧出线 PH 孔排处于外壳投影；信号/3V3 铜从孔排向原生 +X 离开，线束则从 −X 出壳。FAULT_N 分两段引出，均在本引脚外侧。',
 'J1':'GND、PACK_FUSED 分别接本连接器两端焊盘并向各自外侧引出；绝缘壳包围焊脚的投影不可等同穿过另一器件。',
 'J2':'GND 向左、BAT_MON 向右从各自电源焊盘出壳；无折回壳中央。',
 'J3':'W9_IN 从本连接器电源焊盘向右连接外侧通道；仅自身外壳投影。',
 'J4':'GND 向左、BAT_MON 向右从各自焊盘出壳；BAT_MON 最外段仅触及壳缘投影。',
 'J5':'GND 向左、H6_IN 向右从各自电源焊盘离开；保留已交接连接器朝向。',
 'J6':'GND 向左、BAT_MON 向右从自身两端焊盘出壳；无贯穿其他连接器。',
 'J7':'W_VM 从中间电源脚横向引出到近侧壳缘，GND/数据脚从各自端部引出；所有列出段分别核对实际网络。',
 'J8':'W_VM 从自己的中间脚向上离开，W_BUS 从端脚向右上离开；背面并联功率铜仍属同一引脚出口。',
 'J9':'GND/H_BUS 从两端向外，H_VM 中间脚朝上引出后分到左右支路；三段 H_VM 是功率分支而非无限同网穿壳许可。',
 'J11':'W_DUMP_D 向左、W_VM 向右由两端焊脚连接外侧铜路；开关漏极不是 GND。',
 'J12':'H_DUMP_D 向左、H_VM 向右由两端焊脚连接外侧铜路；保持制动端口原针序。',
 'J13':'GND 向上、W_BUS 向下由端脚出壳；数据线末段向右转，未穿过另一器件。',
 'J14':'GND 向左、H_BUS 向下接外侧通道，均从自己的端脚离开。',
 'J15':'GND 向上，CHG_N 由下端脚向下再斜向左出壳；V08 已消除下游偏移接头。',
 'J16':'GND 向上、VBUS_CHARGE 向下从端脚离开，没有以 VBUS 为由横穿壳中央。',
 'J17':'+5V_MOTION 从自身引脚向右引出；宽铜出口由固定接口方向决定。',
 'J18':'+5V_CAM 向左、GND 向右从两端焊脚出壳；保持正负与负载铜宽。',
 'J19':'GND 向上、MASTER_RETURN 向下由端脚出壳，末段斜向右进入外侧通道。',
 'JP60':'M5_EN 从跳线座对应脚向右上方出壳；不是借相同网络横穿其他引脚。',
 'JP70':'C5_EN 从自身跳线引脚向上出壳；未改变维护接口位置。',
}
assert set(refs)=={x['reference']for x in body['body_crossing_inventory']}
own=[]
for x in body['body_crossing_inventory']:
    ref=x['reference'];a=x['start'];b=x['end']
    ts=[t['image']for t in atlas['tiles']if t['layer']==x['layer']and min(a[0],b[0])<=t['bounds'][1]and max(a[0],b[0])>=t['bounds'][0]and min(a[1],b[1])<=t['bounds'][3]and max(a[1],b[1])>=t['bounds'][2]]
    own.append(dict(reference=ref,net=x['net'],layer=x['layer'],track_uuid=x['track_uuid'],start_mm=str(a),end_mm=str(b),inside_length_estimate_mm=x['length_inside_projection_estimate_mm'],decision='JUSTIFIED_OWN_PAD_HOUSING_ESCAPE',specific_reason=refs[ref],visual_evidence=';'.join('images/'+t for t in ts),scope='Drawing review only; not physical/electrical qualification'))
csv_write('70_own_escape_dispositions.csv',own)
components=[]
for ref,x in body['components'].items():
    components.append(dict(reference=ref,layer=x['side'],body_rect_mm=str(x['body_rect_mm']),own_escape_pairs=x['pairs'],review_note=refs.get(ref,'本体投影未命中走线中心线；在分区图核对端头引出，并保留全铜宽 BODY/NETBODY 原生检查。'),geometric_screen='PASS',physical_status='NOT_TESTED'))
csv_write('104_component_coverage.csv',components)
counts=dict(collections.Counter(x['decision']for x in rows))
dump(R/'visual_review_record.json',dict(date='2026-10-03',before_sha256=inv['C3_sha256'],after_sha256=inv['C4_sha256'],scope='Power J10 C3/C4 only; not a new visual signoff of motion/rear/IMU or complete product',review_status='PASS',status_meaning='All stated review records completed; six changes visually rechecked, remaining flags have explicit dispositions',flags_count=39,dispositions=counts,whole_board_tiles_reviewed=atlas['tiles'],flag_groups_reviewed=25,legacy_branch_flags_reviewed=17,own_escape_rows=70,component_coverage=104,final_comparisons_viewed=['V01','V07','V08','V10','V11','V12'],user_aesthetic_approval='NOT_TESTED',physical_tests='NOT_TESTED',manufacturing_release='BLOCKED',correction={'reference':'U41','initial_visual_impression':'Suspected body crossing in overview','corrected_finding':'False impression. Fab x57.85..59.15; trace endpoint x59.4375, width0.2, minimum right-side body gap0.1875 mm for the questioned segment. Native pad/Fab recheck did not support moving U41.'}))
NAME='MORI_power_J10_C4_CANDIDATE';d=HERE/NAME
readme=f'''# J10 C3 视觉复核及 C4 独立候选

2026-10-03。**完成本页定义的绘图复核；C4 是独立 PROTOTYPE，正式四板没有替换。**

[C4 KiCad 工程]({NAME}/{NAME}.kicad_pro) · [PCB]({NAME}/{NAME}.kicad_pcb) · [39 条逐项意见](39_flag_dispositions.csv) · [检查报告](reports/invariants.json)

此前确实查看过 C3 正背面总览，但没有据此完成逐条意见闭合，不能将“看过图”和“逐线复核完”混用。这次复核 C3 全板正背面 12 个重叠放大分区、39 条提示的 25 个局部视图，并对 17 条历史分叉/重叠提示和 70 条自身外壳引出单独留记录。C4 的六处修改又逐张看了前后对比。**此范围只涵盖本次电源候选，不表示运动、后接口和 IMU 三板也在本轮重新复核。**

## 实际修改

| 对比图 | 网络与位置 | 处理 |
|---|---|---|
| [V01](images/V01_before_after.png) | CHG_N / J10 下方 | 去掉峰谷折返，改为平直通道 |
| [V07](images/V07_before_after.png) | CHG_N / 下板边 | 去掉过冲后返回的 V 形折点 |
| [V08](images/V08_before_after.png) | CHG_N / J15 下游 | 两段线改成精确同端点，清理铜边小凸出 |
| [V10](images/V10_before_after.png) | +5V_MOTION / L60 外侧反馈支路 | 消除局部上下折返，保留器件外侧通路 |
| [V11](images/V11_before_after.png) | BAT_ADC / Q11 与 R11 之间 | 以明确竖向段替代 0.2 mm 小偏移，保留跨面本体净空 |
| [V12](images/V12_before_after.png) | ARM_Q / R54 | 去掉 V 形凹口，支路在焊盘内汇合 |

共替换 23 段为 19 段，均是原本 **0.2 mm 的信号/反馈线**。总段数 862→858；147 个过孔、112 个封装、280 个焊盘、板框/孔位/朝向、网络、原理图电路及功率宽铜均不变。没有以细反馈线取代负载通道。另将 PCB 标题、复核链接和背面版本丝印标为 C4，避免与正式 P5R6 混淆。

## 提示逐项判断

39 条原提示：5 条对应已修正问题，24 条有具体几何理由保留，10 条是焊盘/过孔/宽铜内端点被当作外露折点的误报。多个 ID 可能描述同一短段，不能用提示数量充当独立缺陷数量。每条的网络、层、坐标、UUID、理由和图号都在 CSV 中；未按网络类型批量放行。

Q11、R60 邻边的两个 0.1×0.1 mm 转角是一次单向拐弯，仍保留。曾试放大倒角，但分别侵入 Q11/R60 本体投影，已撤回。R54 的直接三叉方案也触发用户规则 R27 的最小 60°接入角；最终改成焊盘内汇合。所有失败试改保留在 `reports/routing_changes.json`，没有增加忽略或改松规则。

摆放复核也考虑了替代朝向：R54 翻转会交换 ARM/GND 出口，当前焊盘内汇合已经清除凹口；R11/Q11 移位或旋转会改变相邻栅极回路；R60/L60 属本地 Buck 反馈与功率组，不为了单个小倒角扩大敏感回路。本轮采用可行的外侧通道，保留已交接的整体摆放。这是本次方案取舍，不能理解为所有摆放都已证明最优。

另更正一次检查中的误判：总览中一度以为 U41 的 H_REF 穿过本体。核对原生 Fab 和线宽后，所指线段最靠近边界的铜仍在右侧，间隔约 0.1875 mm；未据误判移动 U41。

## 可复核证据及边界

- KiCad **10.0.6** 原生 ERC=0、DRC=0、未连接=0、原理图差异=0、忽略项=0，命令与最终 PCB hash 在 `reports/FINAL_*`。
- 沿用用户 KiCad 项目规则的候选 `.kicad_dru` 与 C3 字节一致；R27、BODY/NETBODY 投影等继续生效，来源映射保留在工程目录 `rule_mapping.json`。
- 27 条关键负载路径在剔除细线后连通：PASS。这只检查铜路径，不证明温升或允许持续电流。
- 104 个器件中心线投影筛查未发现跨其他器件本体候选。70 条自身引出在 [逐条表](70_own_escape_dispositions.csv) 解释，包括连接器壳、径向电容和 D40 端部；同网不自动代表可穿本体。全铜宽禁布仍由原生 DRC 检查。
- [858 段原生清单](reports/after_all_segments.csv)、[17 条旧分支提示](17_legacy_branch_dispositions.csv)、[104 器件覆盖](104_component_coverage.csv)、[视觉记录](reports/visual_review_record.json) 都有明确范围。几何图隐藏铺铜，地过孔不因此被判开路。
- 正式工程 249 文件、C3 源均 hash 不变。C4 也没有合并 PHC1 孔径候选，没有生成 Gerber 或下单。

![C4 正面铜线](images/C4_F_Cu.png)
![C4 背面铜线（同顶视坐标）](images/C4_B_Cu.png)

图中的焊盘角部做了显示简化；精确焊盘/丝印另见 KiCad 自身输出 [正面](native_review/front.svg)、[背面](native_review/back.svg)。这些是审阅文件，不是制造文件。

实际接插件、F70 背面高度/温升、线根弯折与带线拆装、JP70/TP71 装机维护路径等沿用 A6 的未闭合项。物理与通电均 **NOT_TESTED**；制造发布 **BLOCKED**。本报告不是用户视觉批准，也不是所有工程资格认证。

最终 PCB SHA-256：`{inv['C4_sha256']}`。

复查命令：KiCad 自带 Python 分别运行 `final_checks.py native`、`audits`、`invariants`；显示图由 `render_review.py` / `render_final.py` 生成。`refine_candidate.py` 是保留试改记录的候选编辑脚本，不能对正式板盲目批量执行。
'''
(HERE/'README.md').write_text(readme)
(d/'README.md').write_text('# J10 C4 独立视觉复核候选\n\nPROTOTYPE / 未台架验证 / 未正式替换。\n\n见 [本次复核](../README.md)。保留同目录 C3 沿用的 BOM/规则映射；只修改走线，不重新批准采购或制造。\n')
dump(R/'disposition_counts.json',counts)
print(counts)

# Lightweight local review page: side-by-side images plus original flag table.
trs=''.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>'for k in ['source_id','net','decision','reason'])+'</tr>'for row in rows)
pics=''.join(f'<figure><figcaption>{label}：左 C3 / 右 C4</figcaption><img src="images/{label}_before_after.png"></figure>'for label in ['V01','V07','V08','V10','V11','V12'])
(HERE/'review.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>MORI J10 C4 视觉复核</title><style>body{font:16px/1.65 system-ui;background:#f4f5f6;color:#222;max-width:1300px;margin:36px auto;padding:0 24px}h1{font-size:28px}img{width:100%;display:block}figure{margin:28px 0;background:#fff;padding:16px}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{padding:9px;border:1px solid #ddd;text-align:left}p{max-width:1000px}.tag{background:#ffe5ad;padding:4px 10px}a{color:#075fba}</style><h1>J10：逐项复核与 C4 候选</h1><p><span class="tag">PROTOTYPE · 正式四板未替换</span></p><p>六处局部修改已逐张复看；39 条提示逐项记录。原生 ERC / DRC / 未连接 / 原理图差异 = 0。器件、板框、针序、过孔及功率线宽保持。几何图隐藏铺铜，焊盘圆角显示简化。</p><p><a href="README.md">完整记录与边界</a> · <a href="39_flag_dispositions.csv">逐项 CSV</a> · <a href="reports/invariants.json">原生检查与范围不变证明</a></p>'''+pics+'<h2>39 条提示</h2><table><tr><th>ID</th><th>网络</th><th>处置</th><th>依据</th></tr>'+trs+'</table><p>自身引出例外见 70 条明细；物理装配、温升和运行 NOT_TESTED，制造 BLOCKED。</p></html>')
