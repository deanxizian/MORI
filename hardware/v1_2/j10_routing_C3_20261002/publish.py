"""Publish review-only C3 artifacts; no formal board or mechanical writes."""
from pathlib import Path
import json,hashlib,datetime,csv,shutil,subprocess,zipfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];R=HERE/'reports';NAME='MORI_power_J10_C3_CANDIDATE';D=HERE/NAME
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
g=json.loads((R/'FINAL_geometry.json').read_text());inv=json.loads((R/'invariants.json').read_text());drc=json.loads((R/'FINAL_drc.json').read_text());erc=json.loads((R/'FINAL_erc_command.json').read_text());load=json.loads((R/'load_path_audit.json').read_text());power=json.loads((R/'power_path_estimates.json').read_text());after=json.loads((R/'after_inventory.json').read_text());flags=json.loads((R/'changed_route_flags.json').read_text());body=json.loads((R/'body_review_final.json').read_text())
assert inv['status']=='PASS'and erc['returncode']==0 and not drc['violations']and not drc['unconnected_items']and load['status']=='PASS'
assert inv['C3_sha256']==sha(D/(NAME+'.kicad_pcb'))==load['pcb_sha256']==power['pcb_sha256']
a3path=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json';a3=json.loads(a3path.read_text())
# Received mechanical studies are copied as evidence only, never adopted geometry.
evidence=HERE/'received_mechanical';evidence.mkdir(exist_ok=True);received=[]
for rel in ['mechanical/studies/prearrival_finish/harness_A2/assembly_safe_review/fourteen_validation.json','mechanical/studies/prearrival_finish/harness_A2/assembly_safe_review/fourteen_body_sequence.json','mechanical/studies/prearrival_finish/harness_A2/delivery.json','mechanical/studies/prearrival_finish/head_harness/HEAD_HARNESS_REQUIREMENTS.md']:
 p=ROOT/rel
 if p.exists():
  q=evidence/p.name;shutil.copy2(p,q);received.append({'source':rel,'sha256':sha(p),'copy':str(q.relative_to(ROOT))})
dump(evidence/'receipt.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':received,'adopted_into_mechanical_main':False,'status':'PASS','scope':'Evidence receipt only. Old A5 failed harness report remains unchanged. Head FPC requirements are recorded for later verification, not resolved by this J10 layout.'})
# Actual connector pin numbering exported directly from FINAL native pads.
with (HERE/'J10_pinout.csv').open('w',newline='')as f:
 w=csv.writer(f);w.writerow(['pin','net','pcb_x_mm','pcb_y_mm','finished_hole_mm','copper_land_mm','wire_direction_native_XY'])
 for p in sorted(g['footprints']['J10']['pads'],key=lambda x:int(x['number'])):w.writerow([p['number'],p['net'],*p['xy'],p['drill'][0],p['size'][0],'-X'])
# Keep the screening records visible. A candidate flag is not automatically a rule violation.
reason={'SHORT_SEGMENT':'Inspect adjacent path: R50 landing or short terminal/corner segment; no new foldback detected. Retained under fixed C2 component positions. See native coordinates and net atlas.','NON_45':'Straight connection to actual pad/via or retained fine-grid copper, with >=60 degree junction checks. Non-45 is a review flag, not a custom-rule violation.','OFFSET_ENDPOINTS':'Nearby same-net endpoints; connection is established by native copper shape, pad/via, or intermediate segment. Not an open net. Inspect inventory UUIDs.'}
with (HERE/'routing_screen_review.csv').open('w',newline='')as f:
 w=csv.writer(f);w.writerow(['screen_id','type','net','layer','x_mm','y_mm','track_UUIDs','disposition','review_note'])
 for x in flags['flags']:w.writerow([x['id'],x['type'],x['net'],x['layer'],*x['xy'],';'.join(x['uuids']),'RETAINED_REVIEW_ITEM',reason.get(x['type'],'Requires review')])
# Review exports from exact checked source; these are not manufacturing data.
review=HERE/'review';review.mkdir(exist_ok=True);cmds=[]
for label,layers in [('front','F.Cu,F.Silkscreen,Edge.Cuts'),('back','B.Cu,B.Silkscreen,Edge.Cuts')]:
 args=['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','export','svg','--mode-single','--page-size-mode','2','--layers',layers,'-o',str(review/(label+'.svg')),str(D/(NAME+'.kicad_pcb'))]
 c=subprocess.run(args,capture_output=True,text=True);assert c.returncode==0;cmds.append({'argv':args,'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr,'pcb_sha256':inv['C3_sha256']})
dump(R/'SVG_commands.json',cmds)
rows=[]
for x in power['rows']:
 s=next(q for q in x['scenarios']if q['assumed_copper_temperature_C']==80 and q['assumed_via_plating_um']==20);p=s['loads'][1]
 rows.append(f"| {x['source']} → {x['destination']} ({x['net']}) | {x['path_min_track_mm']:.1f} | {x['track_length_sum_mm']:.2f} | {s['estimated_path_ohm']*1000:.2f} | {p['drop_V']*1000:.1f} | {p['copper_loss_W']:.3f} |")
width_table='\n'.join(rows)
(HERE/'ROUTING_REVIEW.md').write_text(f'''# C3 布线复核记录

2026-10-03。PROTOTYPE / 未台架验证。本记录针对 C2/A3 固定器件摆放的布线收尾，不是重新批准全部已选器件或生产制造。

## 检查分开记录

- KiCad 10.0.6：0 DRC、0 未连接、0 原理图差异、0 ERC；忽略项为 0。见 `reports/FINAL_*`，全部与最终 PCB hash 绑定。
- 沿用 C2 的自定义规则，`.kicad_dru` 字节完全一致。原规则来自用户 KiCad 项目 `Rules/pcb-rules.json`；源 hash `5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0`。细目继续在候选 `rule_mapping.json` 中。没有调宽间距或删除本体禁布规则。
- 实际 Fab 本体投影筛查：104 个器件，跨其他器件本体的走线候选 0；自身引脚/连接器外壳下的必要引出共 70 条记录。逐条坐标在 `reports/body_review_final.json`。该数值不是 70 条违规，也不是允许任何同网走线穿本体。
- 原生全铜线清单：{after['stats']['segments']} 段、{after['stats']['vias']} 个过孔。每根线 UUID、网络、宽度、坐标均在 `reports/after_all_segments.csv`；前后清单和逐网 SVG 一并保留。
- 新改线的自动筛查仍保留 {len(flags['flags'])} 个提示（非 45°线、相邻端点及短段），详见 `routing_screen_review.csv`。不能将这些提示直接计为 DRC 违规，也不能因 DRC 为零删掉它们。新改线的折返和重叠筛查项已清理为 0；全板保留历史走线的提示可在完整清单中复核。尚不宣称所有布局风格都已得到用户视觉批准。

## 本轮实际处理

1. J10 六路控制/监测线向 PCB +X 逃出引脚，绕行其右侧通道；S8B 外壳和线束仍向 −X 出线。电源与 GND 针未改变。末端折返、重复铜段和孤立旧线已清理。
2. D30 与 F70 的 B.Cu 功率连接按 C2 实际焊盘接回；Q30 源极组在器件外侧汇流，保留各源极引脚 0.6 mm 引出和外侧汇流铜。
3. R51 地端的局部铺铜原先没有接回主地，已增加真实接地走线与 0.50/0.25 mm 过孔，重新安排 BAT_ADC 连接。不能用有一块 GND 铜皮代替连通验证。
4. 8 组信号通道、2 组后续通道及 5 处局部细碎折点按实际 DRC 逐次筛选简化；另清理 +5V_CAM 与 WHEEL_ADC 的末端折返。实际接受与拒绝日志均保留，不把失败试验的结果列入最终 PASS。
5. 新小孔信号过孔采用阻焊盖油；TP61、TP71 只修剪与裸铜冲突的 7 段丝印圆弧，保留标签、焊盘、Fab 和本体，且同步候选局部封装库。TP71 的旧位置文字改到实际测试点附近。

## 新引出经过自身外壳投影的明确例外

| 位置 | 网络/层 | 理由与边界 |
|---|---|---|
| J10 | ARM_Q、CHG_N / B；FAULT_N、BAT_ADC、WHEEL_ADC、CURRENT_ADC / F | 编号孔本来位于绝缘外壳投影内；先向 +X 离开孔排，余下约 0.59 mm 外壳投影不可凭移动铜线消失。没有沿 −X 折回到外壳中央。FAULT_N 的两段短逃线单独列在 JSON。 |
| J15 | CHG_N / B | 从本连接器焊盘越过本外壳到板边通道；不是经过别的器件。保留固定接口方向。 |
| J4 | BAT_MON / B | 负载线接入本连接器电源焊盘；本体投影外缘约 0.052 mm 记录。 |
| J5 | H6_IN / B | 从本连接器电源焊盘向板外侧通道离开；连接器外壳局部约 1.40 mm 投影。 |
| JP60、JP70 | M5_EN / B、C5_EN / F | 跳线座针脚到外侧通道的短引出，不以同网为由贯穿其它本体。 |

这些是具体封装引出说明；未授予整类 GND 或电源网络豁免。D30/F70/R50 原生焊盘与器件几何保持，未扩大焊盘孔来掩盖定位问题。

## 承载电流路径与线宽

27 条关键负载路径都在剔除细信号线后重新连通检查，见 `reports/load_path_audit.json`。这个 PASS 只说明画出了足够宽度门槛的连通路径，不能当作持续载流、散热或安规合格。

本候选外铜仍按源工程名义 70 µm、内铜 35 µm，板厚 1.6 mm。BAT_MON 共用上游仍保留原主干及原 R2 引出处；**到头部 Buck J4 的这条支路改为 1.0 mm**，不是把全部电池主干改为 1.0 mm。D30→Q30 受 R50 背面与信号通道约束，主干为 **0.8 mm**。首批不可据此跳过负载与温升试验。

下表是完整铜路径长度相加的估算；可能重复计算焊盘内部分，也没有计入并联平面好处。计算假定铜温 **80°C**、过孔镀铜 **20 µm**、路径电流 **2 A**，这些都是场景输入，**不是实测或预计温升，也不是允许持续电流**。脚本另列 20°C、15/25 µm 及 1/3.5 A 场景；未计连接器、分流器、二极管和 MOSFET 损耗。

| 路径 | 最窄走线 mm | 铜段长度合计 mm | 估算 mΩ | 2 A 压降 mV | 2 A 铜损 W |
|---|---:|---:|---:|---:|---:|
{width_table}

计算脚本 `power_paths.py`；参数和结果 `reports/power_path_estimates.json`。不声称 IEC/IPC 持续载流认证，仍需实际铜厚/孔铜能力、装配、降压模块与负载确认。

## 后续硬件验证

全部 NOT_TESTED。首先断电逐针核对 J10 1–8（特别是 4=CHG_N、8=GND），检查 R51.2 到系统地；然后按现有电源上电计划，限流、无执行器检查逻辑轨，再验证电压采样比例和故障/使能电平。确认外接 Buck 后逐级加假负载，记录母线/模块端电压、输入电流、这两条新支路与过孔及 D30/F70 温升。最后才能接舵机并做制动回灌及整机试验。

已有万用表和限流电源可做初步极性、电压、连通和限流检查；负载曲线、温升、纹波/瞬态还需要合适负载、温度测量及示波观测条件。测试停止条件沿用现有上电计划：轨电压异常、异常电流/发热、器件极性或针序不符立即断电。没有填写任何实测 PASS。
''')
(HERE/'README.md').write_text(f'''# J10 侧出线 C3：已布通的独立候选

2026-10-03。**完成 C2/A3 候选的电气布线收尾；PROTOTYPE / 物理 NOT_TESTED / 制造 BLOCKED。** 尚未替换正式电源 P5R6，也没有改主机械模型、PHC1 候选或 C2/A3 历史文件。

[KiCad 工程]({NAME}/{NAME}.kicad_pro) · [PCB]({NAME}/{NAME}.kicad_pcb) · [原理图]({NAME}/{NAME}.kicad_sch) · [布线与线宽复核](ROUTING_REVIEW.md) · [J10 针序](J10_pinout.csv)

## 实际交付状态

| 检查 | 结果 |
|---|---|
| KiCad 10.0.6 原生 ERC | PASS，0 条 |
| 原生 DRC / 未连接 / 原理图一致性 | PASS，0 / 0 / 0；忽略项 0 |
| 27 条负载路径的铜线连通筛查 | PASS；不包含载流和温升认证 |
| 112 封装 / 280 焊盘与 C2 几何及网络逐项比对 | PASS；坐标、朝向、面别、尺寸、孔径和针号不变 |
| 板框、安装孔、层数、本体禁布区和自定义规则 | PASS，保持 C2；80×55×1.6 mm、4 层 |
| 正式工程 249 文件、C2 源文件 | PASS，hash 未改变 |
| 本体筛查 | 104 器件，跨其他器件本体走线 0；自身引出例外详见复核记录 |
| 丝印/铜线布局视觉最终批准 | 仍供审查；不把 DRC 当作用户审美批准 |
| 真实端子装配、带线插拔、温升/制动/整机测试 | NOT_TESTED |
| 正式发布、采购和制造 | BLOCKED |

当前 PCB SHA-256：`{inv['C3_sha256']}`。最终原始检查、运行命令/版本和源文件验证在 `reports/FINAL_*`、`reports/invariants.json`，不是截图替代的检查。

![正面原生铜线几何，铺铜隐藏](reports/FINAL_F_Cu.png)
![背面原生铜线几何，使用同一顶视坐标，铺铜隐藏](reports/FINAL_B_Cu.png)

另附 KiCad 自身导出的 [F.Cu/Silk](review/front.svg) 和 [B.Cu/Silk](review/back.svg)，均来自同一受检文件；这些是审阅图，不是制造数据。

## 接口及机械复核边界

J10 使用 **JST S8B-PH-K-S(LF)(SN)**，配 PHR-8 / SPH-002T-P0.5S，向原生 PCB **−X** 出线。1–8 孔中心仍为 X44.5、Y27/29/31/33/35/37/39/41 mm，成品孔候选 Ø0.90、铜盘 1.50 mm。针序严格为 **3V3、ARM_Q、FAULT_N、CHG_N、BAT_ADC、WHEEL_ADC、CURRENT_ADC、GND**。孔成品公差 −0.05/+0 mm 仍待板厂确认。

D30/F70/R50 继续在背面；JP70=(35,44.5)/0°、TP71=(23,35)，全部与 A3 相同。完整本体、插头及背面包络继承 A3，C3 没有添加新的机械尺寸。F70 背面包络 3.09 mm、R50 的 2×1×1 mm 装配包络仍有假定，不能将名义不相交说成实际可装。

仍需机械/供应资料闭合：真实插合后出线高度、端子及线根弯折要求、带线拔出与夹持路径；JP70/TP71 在整机装好后直进服务通道受阻，需要确认维护顺序或另审局部变更。这次没有擅自移动元件来消除这些问题。新的 14 线独立机械研究已接收快照，旧 A5 的失败报告保留，主模型仍未采用那些研究线束。

其他 PH 接口的成品孔统一修正还在 **PHC1 独立候选**；它们没有自动合并到这份 C3。正式四板亦未发布替换，不能混用不同候选的 DRC 或制造状态。

## 使用和复核

打开上述 `.kicad_pro` 即可使用本地封装/符号库。可在 KiCad 中重填铺铜并运行全部 ERC/DRC，或使用 KiCad 自带 Python 运行 `verify.py`、`run_audits.py`、`power_paths.py`。`finalize.py` 会更新本候选元数据、重填并重新生成最终检查，应只在需要更新候选时使用。

本目录的 `route.py`、`prepare/finish/smooth` 等脚本和编号日志是开发过程，不是按文件名批量执行的一键构建流程；它们会改候选。最终权威源是本页 hash 对应的原生 PCB/SCH 和 `FINAL_*` 报告。

没有导出 Gerber/钻孔/制造贴装文件，没有下单。`assembly_bom.csv` 是沿用电路的审查用器件清单。
''')
(D/'README.md').write_text('# MORI power J10-C3 独立候选\n\n已布通，原生 ERC/DRC 为零；未完成真实装配/热/动力测试，未正式发布。\n\n请从 [候选总览](../README.md) 和 [布线复核](../ROUTING_REVIEW.md) 阅读真实检查及阻断项。不要使用 C2 的历史检查来描述 C3。\n')
# Source-specific hardware handoff. Never mutate shared mechanical contracts here.
handoff={'revision':'V1.2-H0.5-P5R7-PREARRIVAL-A6','addendum_id':'A6_J10_C3','date':'2026-10-03','status':'PASS','scope':'Routed electrical candidate and invariant handoff ONLY; not mechanical approval or manufacturing release','base_placement_handoff':str(a3path.relative_to(ROOT)),'base_placement_handoff_sha256':sha(a3path),'candidate':{'project':str((D/(NAME+'.kicad_pro')).relative_to(ROOT)),'pcb':str((D/(NAME+'.kicad_pcb')).relative_to(ROOT)),'pcb_sha256':inv['C3_sha256'],'schematic':str((D/(NAME+'.kicad_sch')).relative_to(ROOT)),'schematic_sha256':sha(D/(NAME+'.kicad_sch')),'outline_mm':[80,55],'thickness_mm':1.6,'copper_layers':4,'placement_source':'C2/A3','all_112_footprints_and_280_pads_unchanged':True},'J10':a3['J10'],'backside_candidates':a3['backside_candidates'],'backside_basis':a3['backside_basis'],'electrical_checks':{'ERC':'PASS','ERC_violations':0,'DRC':'PASS','DRC_violations':0,'unconnected':0,'schematic_parity':0,'ignored':0,'load_path_count':27,'load_path_status':'PASS','thermal_current_qualification':'NOT_TESTED'},'formal_boards_replaced':False,'mechanical_main_modified':False,'PHC1_merged':False,'new_mechanical_datums':[],'invariants_report':str((R/'invariants.json').relative_to(ROOT)),'routing_review':str((HERE/'ROUTING_REVIEW.md').relative_to(ROOT)),'remaining_mechanical_items':['Actual mated wire exit height and terminal straight section unknown','Mated wire/plug removal and grip/tool access need real supplier geometry','JP70 and TP71 service access after full assembly remains blocked under A3','D30/F70 backside thermal and mounting tolerance NOT_TESTED'],'physical_tests':'NOT_TESTED','procurement_release':'BLOCKED','manufacturing_release':'BLOCKED','report':str((HERE/'README.md').relative_to(ROOT)),'received_mechanical_evidence':received}
hp=ROOT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A6_J10_C3.json';assert not hp.exists(),'Do not silently replace a published handoff';dump(hp,handoff)
manifest={str(p.relative_to(ROOT)):sha(p)for p in D.rglob('*')if p.is_file()and p.suffix not in ['.kicad_prl','.lck']}
manifest.update({str(p.relative_to(ROOT)):sha(p)for p in [HERE/'README.md',HERE/'ROUTING_REVIEW.md',HERE/'J10_pinout.csv',HERE/'routing_screen_review.csv',hp,R/'FINAL_drc.json',R/'FINAL_erc.json',R/'invariants.json',R/'power_path_estimates.json',R/'load_path_audit.json']})
dump(HERE/'delivery_manifest.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','scope':'Electrical review package integrity only','files':manifest,'formal_release':False,'PCB_PROTOTYPE':True})
print('PUBLISHED',hp,inv['C3_sha256'])
