"""Create human-readable P5 review entry points from checked reports."""
import json,csv,html,hashlib
from pathlib import Path
H=Path(__file__).resolve().parents[1];O=H/'layout_P5';ROOT=H.parents[1]
load=lambda p:json.loads(p.read_text())
v=load(O/'reports/verification.json');handoff=load(H/'handoff/mechanical_P5.json')
labels={'motion':'运动承载板','imu':'IMU 板','power':'电源板','rear':'Type-C / 电源开关接口板'}
readme=['# MORI P5 全新布局与布线','',
'本次四块 PCB 已从零铜线重新摆位和布线，P4 源工程保留。电路、器件型号和逐针网络不变；没有沿用 P4 的走线或过孔 UUID。状态为 **PROTOTYPE / 实物 NOT_TESTED**。',
'','先打开 [逐层查看页面](index.html)，或直接打开下列原生 KiCad 工程。PNG/SVG 是原生 PCB 导出；底层视图已镜像。',
'','| 电路板 | 板框 / 厚度 mm | 层数 | ERC / DRC / 未连接 / 一致性问题 | 原生工程 |',
'|---|---|---:|---|---|']
for kind,label in labels.items():
 n='MORI_'+kind+'_P5';b=handoff['boards'][n];w,h=b['outline_mm']
 readme.append(f'| {label} | {w}×{h}×1.6 | {b["copper_layers"]} | 0 / 0 / 0 / 0 | [{n}](../kicad/{n}/{n}.kicad_pro) |')
readme += ['',
'KiCad **10.0.6** 实际运行 ERC、DRC、全走线错误、一致性和重新填充检查。命令、返回码及输入文件 SHA-256 位于每板 `reports/MORI_*_P5/check_commands.json`。没有增加 DRC 忽略项。',
'',
'这次的主要变化：重新分配功能区和连接器朝向；运动板的逻辑器件放在载板背面，按引脚朝外逃线；两组 5V 降压保持就近分区；采样电阻、电容重新对齐；最后逐段去掉短 V 形折返和多余偏移。旧版与新版的逐针网络、零继承铜线及位置差异见 [重建核对](reports/zero_copper_and_pinmap_verification.json)。',
'',
'**电源板改为四层**：外层主电流/信号，内部两层 GND。二层试版的局部地铜分成多个不相通区域，因此增加公共回流平面。内层没有信号走线；电感和降压芯片的限定投影继续留空。名义铜厚70/35/35/70μm，总厚仍1.6mm；板厂叠层、报价及实物温升未确认。',
'',
'169个器件均有本体投影检查记录，双面不相关网络下穿候选为0。**这不等于所有器件投影内完全没有铜线**：架高主控模块U100、连接器端子、LGA焊盘和径向电容引脚有明确局部情况。完整记录见 [布线验收与例外](routing_acceptance.md)，不能用DRC为这些情况自动背书。',
'',
'主电流连接另做了宽度过滤后的真实铜形状连通检查，避免将0.2mm采样线当负载线；结果 [PASS](reports/MORI_power_P5/load_path_audit.json)。此项不证明载流温升、过孔镀铜或制动瞬态通过。',
'',
'交接文件： [连接器逐针表](connector_pinmap.csv) · [全部器件坐标/朝向](placements.csv) · [带型号的装配表](assembly_parts_with_mpn.csv) · [线束](harness.json) · [机械交接](../handoff/mechanical_P5.json) · [检查总表](reports/verification.json)。',
'',
'机械交接保留未知项：完整插合高度、弯线空间、实装质量仍未测。电源板前+16/后-3mm是设计限制；后接口24×25mm及插头外伸仍需机械处理。STEP只导出裸板，不冒充完整装配。没有修改机械模型或机械契约。',
'',
'本次没有重新确认价格/库存。四层电源打样报价、完整成品电池/外部充电方案、插接装配与台架验证仍是制造释放的阻塞项。机械新选扬声器与旧声学BOM的同步单独记入接口冲突，没有在布线任务里静默换件。没有导出Gerber或下单。',
'',
'复核入口：使用KiCad自带Python运行 `hardware/v1_2/tools/run_layout_P5.py <motion|imu|power|rear> check`。它仅运行检查。其他带摆件/布线动作的脚本是有顺序的工程记录，不要无差别批量重放。']
(O/'README.md').write_text('\n'.join(readme)+'\n')
ex=load(O/'reports/body_escape_exceptions.json');rules=load(O/'pcb-rules-source.json')
note=['# P5 布线验收与例外','',
'原生检查 PASS；逐组件双面本体检查没有发现不相关网络下穿。完整47条源规则与布线外观的最终验收没有被自动标为PASS。',
'',
'来源：`/Users/dean/Documents/KiCad/Rules/pcb-rules.json`；GitHub `deanxizian/KiCad`，记录提交`f756532aa67112a9d437c18e8ca00ac8fba2c9b4`。快照SHA-256：`'+hashlib.sha256((O/'pcb-rules-source.json').read_bytes()).hexdigest()+'`。47条中44条启用。',
'',
'## 实际检查边界','',
'线宽、间距、孔径、物理via/pad间距、四辐条热焊盘、最小交汇角和可表达的对象范围由项目原生规则执行；R13限制内层不得走信号。R14编辑倒角、R33–37扇出/布线策略及夹具/装配条件不能仅靠DRC证明，映射见 [逐条源规则](source_rule_matrix.md)。',
'',
'本体规则同时作用于F/B两面，电源/GND没有全局豁免。先扣除真实焊盘和逐针向外通道，本体核心禁止走线；不相关网络即使经过通道也被禁止。填充地平面与信号线分开检查。此几何检查使用原生封装Fab图形和0.025mm采样，仍需结合厂商完整装配包络复核。',
'',
'## 局部情况逐项登记','',
'U100保持原有架高可拆模块架构；载板内的器件/线位于它的投影内。模块完整投影和实际安装净空不同，但没有实物插座高度，不能宣称这个机械间隙已合格。要彻底取消U100投影下的全部器件/走线，需更改承载架构或板框；本次未擅自改变模块。',
'',
'下表为每个例外的精确位号和网络；逐线UUID、坐标和估算投影内长度见 [机器可读记录](reports/body_escape_exceptions.json)。普通SMD器件不授予按电源/GND网名分类的豁免。',
'','| 板 | 位号 | 网络 | 说明 |','|---|---|---|---|']
for x in ex:
 reason='架高模块承载架构，安装净空未验证'if x['reference']=='U100'else'自身焊盘/端子到外沿的限定出口；不允许不相关网络借道'
 note.append('| '+x['board']+' | '+x['reference']+' | '+', '.join(n.replace('/','')for n in x['nets'])+' | '+reason+' |')
note += ['',
'## 转角与平滑性','',
'重新对齐采样RC、移动EN过孔、拉直W_SENSE通道、重新处理CLR_N端子入口，并用KiCad逐次检查整段简化。机械固定接口或紧邻去耦的局部走线不得仅为直线外观而破坏返回路径。',
'',
'针对R14，已将可行的独立直角改为0.499999mm倒角。检测范围为自由90°拐角；不把焊盘落点、过孔落点和真实支路交汇混作普通拐角。它也不能证明所有长对角线都等价于源编辑器的倒角设置。',
'',
'仍保留IMU U1右侧/GND的两处紧凑引出拐角，坐标(11.62,8.85)、(11.62,9.85)mm。局部直段只有0.4575mm；按精确0.499999mm切角会进入LGA本体/焊盘出口，扩大地回路也与紧邻引出的目的冲突。因此精确R14符合性保留为FAIL/局部例外，**没有修改源R14数值或以DRC=0抹去它**。相关记录为 `reports/MORI_imu_P5/R14_corner_review.json` 和 `imu_ground_first.json`。',
'',
'## 热焊盘与回流','',
'后接口USB1的四个SH屏蔽壳焊脚为直接地铜连接，明确覆盖源R25热焊盘连接方式；目的为本地屏蔽/ESD回流，焊接热工艺和ESD仍NOT_TESTED。精确覆盖规则在该原生项目中，未使用隐藏错误列表。',
'',
'运动板U100的C2/C4/C6/D5/D6地脚及C1供电脚使用指定平面/相邻同网针脚连接，外层局部退让铜皮，避免额外的残缺热连接；仍保留所连接平面的四辐条规则。电源JP70.2的附加顶层铜皮退让，实际由通孔连接B/In1/In2地铜；四辐条要求没有降低。',
'',
'## 结论范围','',
'P5是已完成布线并通过原生检查的可编辑原型。完整源规则等价性、用户外观验收、完整机械插合、载流/温升/EMC/电池/动态平衡/续航均不能由上述检查推定通过；无生产/采购释放。']
(O/'routing_acceptance.md').write_text('\n'.join(note)+'\n')
matrix=['# P5 源规则映射','', 'IMPLEMENTED表示规则已在原生项目中实现，不表示物理资格或所有策略等价性通过。DISABLED_IN_SOURCE遵照源文件禁用状态；没有新增DRC忽略项。','', '| 源规则 | 启用 | 运动 / IMU / 电源 / 后接口 |','|---|---|---|']
maps={k:{q['id']:q for q in load(H/'kicad'/f'MORI_{k}_P5/rule_mapping.json')['rules']}for k in labels}
for rr in rules['rules']:
 rid=rr['id'];matrix.append('| '+rid+' | '+str(rr['enabled'])+' | '+' / '.join(maps[k][rid]['implementation']for k in labels)+' |')
matrix += ['', 'R14：全局精确等价NOT_TESTED；IMU两处0.4575mm地引出局部FAIL/已记录例外。R25：后板USB1.SH使用明示直连覆盖。R10/R17：运动、电源为4层，内部平面规则启用。R13：四板内部信号线数量均为0。详细原始范围、优先级和数值以快照及各原生`.kicad_dru`为准。']
(O/'source_rule_matrix.md').write_text('\n'.join(matrix)+'\n')
# Keep project-local copied notes from masquerading as current placement data.
for k in labels:
 d=H/'kicad'/f'MORI_{k}_P5';p=d/'layout_notes.json'
 if p.exists()and not(O/'reports'/f'MORI_{k}_P5'/'inherited_layout_notes.json').exists():(O/'reports'/f'MORI_{k}_P5'/'inherited_layout_notes.json').write_bytes(p.read_bytes())
 p.write_text(json.dumps(dict(revision='P5',current_placements='../../layout_P5/placements.csv',mechanical_handoff='../../handoff/mechanical_P5.json',routing_review='../../layout_P5/routing_acceptance.md',physical_tests='NOT_TESTED'),indent=2)+'\n')
cards=[]
for kind,label in labels.items():
 n='MORI_'+kind+'_P5';b=handoff['boards'][n]
 cards.append(dict(id=kind,name=n,label=label,size=' × '.join(map(str,b['outline_mm']))+' × 1.6 mm',layers=b['copper_layers']))
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI P5 · 布线复核</title>
<style>body{margin:0;background:#111820;color:#eaf1f6;font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1320px;margin:auto;padding:34px}h1{font-weight:650;letter-spacing:-1px;margin:6px 0}.meta{color:#a9b8c6}a{color:#8dceff}nav,.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}button{border:1px solid #526070;border-radius:8px;padding:10px 15px;background:#1b2633;color:inherit;cursor:pointer}button[aria-pressed=true]{background:#c3f0df;color:#162c28;border-color:#c3f0df}.note{border-left:3px solid #d5ac61;padding:8px 16px;background:#292620}.pass{color:#9fe0c4}figure{margin:20px 0;padding:0;border:1px solid #435467;overflow:auto;border-radius:8px}img{display:block;width:100%;height:auto;cursor:zoom-in}.zoom img{width:2400px;max-width:none;cursor:zoom-out}footer{font-size:14px;color:#a9b8c6;margin-top:24px}.links{display:flex;gap:18px;flex-wrap:wrap}</style>
<main><div class="meta">MORI · V1.2-H0.5-P5 · PROTOTYPE</div><h1>重新摆位，从零布线。</h1><p>四块原生工程，旧版P4保留。所有内层只作平面；不使用内层信号线隐藏元件下穿。</p>
<nav id="boards"></nav><h2 id="name"></h2><div id="spec" class="meta"></div><p class="pass">KiCad 10.0.6　ERC 0 · DRC 0 · 未连接 0 · 原理图一致性问题 0</p>
<div class="toolbar"><button id="top" onclick="side='top';render()">顶层</button><button id="bottom" onclick="side='bottom';render()">底层（镜像）</button><button onclick="document.querySelector('figure').classList.toggle('zoom')">切换原尺寸 / 适应宽度</button></div>
<figure onclick="this.classList.toggle('zoom')"><img id="pcb" alt="原生KiCad走线视图"></figure><div id="files" class="links"></div>
<p class="note">双面不相关网络下穿候选为0；保留U100架高模块和自身焊盘/端子引出等逐项例外。IMU两处紧凑GND拐角没有满足精确0.499999mm倒角。DRC通过不等于全部源规则或实物通过。</p>
<div class="links"><a href="README.md">交付说明</a><a href="routing_acceptance.md">布线要求与具体例外</a><a href="source_rule_matrix.md">47条源规则映射</a><a href="connector_pinmap.csv">逐针表</a><a href="../handoff/mechanical_P5.json">机械交接</a><a href="reports/verification.json">检查总表</a></div>
<footer>图像来自最终原生PCB；临时导出副本省略填充铜皮，以便检查走线，源工程没有删地铜。电源板80×55mm改为四层以提供公共地回流；打样价格未核。后接口板24×25mm及完整插合空间待机械复核。STEP为裸板；全部台架试验NOT_TESTED，没有采购或下单。</footer></main>
<script>const data=__DATA__;let board=data[0],side='top';const nav=document.getElementById('boards');for(const b of data){const el=document.createElement('button');el.textContent=b.label;el.id='nav-'+b.id;el.onclick=()=>{board=b;render()};nav.append(el)}function render(){for(const b of data)document.getElementById('nav-'+b.id).setAttribute('aria-pressed',b.id===board.id);document.getElementById('top').setAttribute('aria-pressed',side==='top');document.getElementById('bottom').setAttribute('aria-pressed',side==='bottom');document.getElementById('name').textContent=board.label;document.getElementById('spec').textContent=board.size+' · '+board.layers+'层 · '+board.name;document.getElementById('pcb').src='previews/'+board.name+'/'+side+'_tracks.png';document.getElementById('files').innerHTML='<a href="../kicad/'+board.name+'/'+board.name+'.kicad_pro">KiCad工程</a><a href="../kicad/'+board.name+'/'+board.name+'.kicad_pcb">原生PCB</a><a href="previews/'+board.name+'/'+board.name+'.pdf">功能块原理图PDF</a><a href="previews/'+board.name+'/'+side+'_tracks.svg">矢量走线图</a>'}render()</script></html>'''.replace('__DATA__',json.dumps(cards,ensure_ascii=False))
(O/'index.html').write_text(page)
print('P5 review notes, source-rule matrix, and offline viewer written')
