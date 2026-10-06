#!/usr/bin/env python3
"""Readable local review index generated from the checked P5R2 artifacts."""
import json,html,csv
from pathlib import Path
H=Path(__file__).resolve().parents[1];O=H/'layout_P5R2'
load=lambda p:json.loads(p.read_text())
j=load(O/'reports/verification.json');nets=load(O/'reports/net_review.json')
labels={'motion':'运动承载板','imu':'IMU板','power':'电源板','rear':'Type-C / 电源开关板'}
widths={kind:load(O/'reports'/kind/'width_review.json')for kind in labels}
delta=j['deltas'];oldlen=sum(v['before']['track_length_mm']for v in delta.values());newlen=sum(v['after']['track_length_mm']for v in delta.values())
lines=['# MORI P5R2 四板逐线复查','',
'本版复查四块现有PCB的全部网络及每条铜线，修正重叠、冗余、局部折返和摆位造成的小偏移。P5/P5R1工程原样保留；这次是复查修正，没有声称再从零重画。**PROTOTYPE / 实物 NOT_TESTED；不是制造释放版。**','',
'打开 [前后对照与逐网查看](index.html)。页面可切换四块板、正反面，并逐个选择网络。全板图由原生KiCad临时副本导出，隐藏覆铜以看清走线；原生工程保留填充。逐网图是根据实际坐标绘制的诊断图，焊盘形状作了简化，精确铜形状以原生工程为准。底层视图保持顶视坐标，未镜像。','',
'| 电路板 | PCB mm / 层数 | 铜线段：前→后 | ERC / DRC / 未连接 / 一致性 | 原生工程 |','|---|---|---:|---|---|']
for kind in labels:
 name='MORI_'+kind+'_P5R2';size={'motion':'70×35 / 4','imu':'20×16 / 2','power':'80×55 / 4','rear':'24×25 / 2'}[kind];d=delta[kind]
 lines.append(f'| {labels[kind]} | {size} | {d["before"]["tracks"]}→{d["after"]["tracks"]} | 0 / 0 / 0 / 0 | [{name}](../kicad/{name}/{name}.kicad_pro) |')
lines += ['',f'覆盖 **{j["reviewed_nets"]}个网络**（包括后接口板只由铜区连接的GND）、原始{j["source_segments"]}条线段；最终{j["final_segments"]}条线段、{j["final_vias"]}个过孔都有UUID记录。铜线中心线总长由{oldlen:.3f}mm降至{newlen:.3f}mm，减少{oldlen-newlen:.3f}mm。线段变少不等于性能已验证。','',
'检查清单： [逐条铜线](all_segments_review.csv) · [全部过孔](all_vias_review.csv) · [逐网络结论](net_review.csv) · [几何筛查提示及落点](screening_disposition.csv) · [本体投影记录](reports/body_escape_inventory.json) · [原生检查总表](reports/verification.json)。每条铜线可以追溯到板、网络、层、宽度、端点、UUID和对应逐网图。筛查提示未被悄悄清零，也不被自动等同缺陷。','',
'本次明确改动包括：运动板 R13 旋转并移位，IMU片选线改为干线加分支；R9 下移0.25mm，为CAM供电让出通道；BAT_ADC改成直通竖线；S288使能重叠并线。IMU板 R1 旋转并移位，重排MISO与3.3V的外侧路径。电源板去掉CHG_N约13mm重叠、H_SENSE的小V形偏移及H_GATE的竖线抖动。Type-C板删除VBUS等重复铜段。其余已接受的合并和局部优化、失败后回退的试验都在每板 `*_transactions.json` 中。','',
'**板框、安装孔、连接器及主控模块位置、层数、器件型号、逐针网络均未改变。** 只有运动板R9/R13和IMU板R1位置/朝向改变；机械侧采用新交接前仍不能称整机实装已适配。 [器件坐标](placements.csv) · [连接器逐针](connector_pinmap.csv) · [机械交接](../handoff/mechanical_P5R2.json)。','',
'## 线宽结论','',
'图中较粗的线有供电用途，不能统一改细。运动板右上供电线为 **0.5mm的+5V_MOTION**，普通数字/采样线主要0.2mm。该供电路径按约21.3mΩ估算，0.75A场景压降约16mV、铜损约12mW，未计焊盘、插座及地回流；这是计算结果，不是温升或额定载流实测。','',
'| 用途 | 当前实际线宽 | 复查结论 |','|---|---|---|',
'| 运动板5V | 0.5mm | 全路径连续，无串联换层；保留 |',
'| 电源板电池主干 | 2.0mm | 承担多路负载；名义外层70µm，板厂铜厚/过孔电镀未确认 |',
'| 轮驱主路线 | 1.5mm；J8完整路径含0.8mm段 | 不能把整条轮驱路线写成全程1.5mm；峰值/温升仍待验证 |',
'| 头部路线 | 1.0mm；J9完整路径含0.8mm段 | 细分支与主负载路径分开检查；并发2A仅为估算场景 |',
'| 两路5V转换器 | 0.8mm主线；SW局部0.6mm收口 | 按引脚尺寸及局部回路保留；纹波RMS/温升未验证 |',
'| Type-C充电主线 | 0.6mm，USB局部0.5mm | 1A设计场景；J2.5的0.2mm VBUS_RAW是检测支路 |',
'| IMU及普通信号 | 0.2mm为主 | 不承担电机负载；信号完整性仍待板级测试 |','',
'[完整电流路径与电阻计算](width_review.md)列出实铜连接、最宽完整路径的最小线宽、过孔及压降。当前2mm主干存在单个换层过孔的路径，不能凭主干宽度保证6.48A长期工作；6.48A是已有并发功耗预算，不是允许连续电流。回流铜区、过孔均流、MOSFET温升、保险协调及制动回灌仍需验证。**DRC不检查温升，也不能证明全部线宽额定正确。**','',
'## 对用户KiCad规则的核对','',
'实际读取 `/Users/dean/Documents/KiCad/Rules/pcb-rules.json`；SHA-256 `5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0`。共47条、44条启用，快照为 [pcb-rules-source.json](pcb-rules-source.json)。沿用间距、过孔/焊盘、孔铜、环宽及内层禁信号的原生规则；没有新增DRC忽略项。四板内层信号走线为0。','',
'KiCad10.0.6实际执行 `pcb drc --severity-all --all-track-errors --schematic-parity --refill-zones --exit-code-violations` 以及 `sch erc --severity-all --exit-code-violations`。命令、返回码、输入文件哈希和原始报告均在各板 `reports/<kind>/`。交易试验的候选报告可能记录拒绝项；最终依据固定名称 `drc.json` / `erc.json` 和 `check_commands.json`。','',
'**47条编辑器策略完全等价：NOT_TESTED。严格“每个器件投影内都没有走线”：不成立，不能用原生DRC为此背书。** 剩余局部情况逐条保留：','',
'- 运动板U100是既有架高可拆模块，承载板元件/铜线在其投影内；插座高度和完整底面净空仍未实测。','- 连接器、跳帽和径向电容的端子位于本体投影内，保留本器件逐针向外出口；IMU的LGA焊盘也有局部出口。这不是允许其他网络从器件底下穿过；双面本体核心及不相关网络均有原生禁布规则。','- IMU U1.9/U1.11 的两处短GND转角未满足R14的精确0.499999mm setback，状态 **FAIL**；U1.8使用0.2mm局部倒角，也按局部例外记录。扩大至0.5mm会碰密脚/本体限制，试验未被强行接受。','- 电源板W_BRAKE_GATE靠R24.2的弯角实际上用铜宽与焊盘搭接。中心线筛查漏掉这个落点；0.5mm倒角试验导致R24.2断开，已回退。','- Type-C板USB1.SH保留已有实连GND的R25局部例外，ESD性能和焊接尚未测试。','',
'不相关网络本体下穿筛查为0；逐项出口、本体例外及所有短段/错位端点仍在清单，未声明“全部没有例外”或用户视觉验收PASS。','',
'## 复核与后续测试','',
'使用KiCad自带Python运行 `hardware/v1_2/tools/check_review_P5R2.py check` 可重跑四板原生检查；`audit` 重跑本体/接口/几何检查；`width_review_P5R2.py` 重算线宽路径。其余编辑脚本是有顺序的工程记录，包含特定UUID，不要无差别重放。','',
'全板实物仍NOT_TESTED。先托架断电检查、限流供电，再分轨和单负载验证；按既有测试顺序执行电机悬空、并发负载、制动回灌、平衡和续航。现有万用表/限流电源可做初级检查；纹波、瞬态、温升和信号时序需要相应测量设备。没有采购、下单、Gerber或制造释放。价格、完整电池/外部充电方案、插合包络和扬声器合同冲突沿用现有阻塞记录，本次不冒充已解决。','']
(O/'README.md').write_text('\n'.join(lines))
w=['# P5R2 实际线宽与供电路径复查','','各路径使用原生铜形状连通图；过滤掉不能承担主负载的细信号铜后计算。正向路径电阻为20°C铜电阻率假设1.724×10⁻⁵Ω·mm；外层铜厚电源70µm/其余35µm，孔壁电镀20µm均为设计假设，未向板厂确认。按整段长度求和，未模拟回流、焊盘、接触、电感、MOSFET、电流均分或铜区，不能用作载流额定值。','','低电阻单路径可能偏爱短窄支路，另列“最宽完整路径的最小宽度”，避免把候选路径当成唯一瓶颈。电机回灌及转换器SW纹波不由DC模型证明。','','| 板 / 网络 / 起止 | 场景A | 选定路径最小宽mm | 最宽完整路径最小宽mm | 换层过孔数 | 路径估算mΩ | 压降mV | 铜损W |','|---|---:|---:|---:|---:|---:|---:|---:|']
for kind,v in widths.items():
 for r in v['paths']:
  w.append(f'| {kind} {r["net"]} {r["source"]}→{r["destination"]} | {r["design_scenario_A"]} | {r["minimum_path_width_mm"]} | {r["widest_complete_path_minimum_width_mm"]} | {len(r["single_path_vias"])} | {r["conservative_complete_segment_path_R20_mohm"]:.2f} | {r["drop20_mV"]:.2f} | {r["loss20_W"]:.4f} |')
w+=['','轮驱单支路3.34A是把30W/9V全部分配给某一输出的保守场景，不能与两路同时3.34A混为一谈。运动/交互5V分别0.75A/2A峰值；持续目标较低。电池总6.48A取既有S3并发预算；主保险6.3A的时间/温度协调仍需核定。','','每板 `reports/<kind>/width_review.json` 内记录过孔位置、孔径、全部路径UUID和源PCB哈希。','']
(O/'width_review.md').write_text('\n'.join(w))
data={'labels':labels,'nets':nets,'native':j['native_checks'],'deltas':delta,'widths':widths}
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI P5R2 逐线复查</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#10161e;color:#e6edf4;font:15px/1.6 system-ui}header,main{max-width:1600px;margin:auto;padding:24px}header{border-bottom:1px solid #384351}h1{font-size:28px;margin:0}h2{font-size:20px}p{color:#b9c6d4}.notice{padding:12px 16px;border-left:4px solid #e6bb66;background:#202932}a{color:#80c7fa}select,input,button{padding:10px;background:#263442;color:inherit;border:1px solid #667789;border-radius:5px;font:inherit}label{display:inline-block;margin:0 16px 12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{padding:16px;background:#19232e;border:1px solid #364251;border-radius:8px;min-width:0}.panel img{width:100%;height:auto;display:block}object{width:100%;height:520px}.stats{display:flex;gap:20px;flex-wrap:wrap}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:8px;text-align:left;border-bottom:1px solid #394959}code{word-break:break-all}.meta{font-size:13px}.tools{position:sticky;top:0;background:#10161e;padding-top:12px;z-index:2}@media(max-width:800px){.grid{grid-template-columns:1fr}object{height:350px}}
</style><header><h1>MORI P5R2 · 四板逐线复查</h1><p>114个网络 · 全部线段和过孔有记录 · 原生工程保留前版</p><div class="notice">PROTOTYPE / 实物 NOT_TESTED。ERC/DRC为0不等于全部布线偏好或载流温升通过。U100架高模块、引脚出口、IMU局部R14例外详见报告。</div><p><a href="README.md">完整说明 / 例外</a> · <a href="width_review.md">线宽与电流路径</a> · <a href="all_segments_review.csv">逐条铜线CSV</a> · <a href="all_vias_review.csv">过孔CSV</a> · <a href="screening_disposition.csv">筛查提示</a></p></header><main>
<div class="tools"><label>电路板 <select id="board"></select></label><label>全板视图 <select id="layer"><option value="combined">双面叠加</option><option value="front">F.Cu</option><option value="back">B.Cu（顶视坐标）</option></select></label></div><div id="stats" class="stats"></div><p id="project"></p>
<div class="grid"><section class="panel"><h2>复查前</h2><a id="fullBeforeLink"><img id="fullBefore" alt="复查前原生PCB图"></a></section><section class="panel"><h2>P5R2</h2><a id="fullAfterLink"><img id="fullAfter" alt="复查后原生PCB图"></a></section></div>
<h2>逐网络追踪</h2><p>红色F.Cu、蓝色B.Cu、金色本网络焊盘、紫色过孔。灰色是其他网络和器件背景。诊断图的焊盘仅为简化形状；点击原生全板图检查实际铜面。过孔和轨迹均取原生PCB。</p><label>搜索 <input id="search" placeholder="例如 GND、CAM、H_SENSE"></label><label>网络 <select id="net"></select></label><button id="prev">上一个</button> <button id="next">下一个</button><p id="note" class="notice"></p><div class="grid"><section class="panel"><h2 id="bn">复查前</h2><object id="before" type="image/svg+xml"></object></section><section class="panel"><h2 id="an">P5R2</h2><object id="after" type="image/svg+xml"></object></section></div><p id="netmeta" class="meta"></p>
<h2>本板供电线宽</h2><p>这里的PASS仅指宽度过滤后的实铜连通；电流值为计算场景，温升和持续载流未验证。细采样支路不按主负载处理。</p><div style="overflow:auto"><table><thead><tr><th>网络/起止</th><th>场景A</th><th>最宽完整路径的最小线宽mm</th><th>计算mΩ</th><th>压降mV</th></tr></thead><tbody id="widths"></tbody></table></div></main><script>const DATA=__DATA__;
const by=id=>document.getElementById(id);let shown=[];
for(const [k,v]of Object.entries(DATA.labels))by('board').add(new Option(v,k));
function netList(){const k=by('board').value,q=by('search').value.toLowerCase();shown=DATA.nets.filter(n=>n.kind===k&&n.net.toLowerCase().includes(q));by('net').replaceChildren();shown.forEach((n,i)=>by('net').add(new Option(n.net,i)));renderNet()}
function renderNet(){const n=shown[+by('net').value];if(!n){by('note').textContent='没有匹配网络';return}by('before').data=n.image_before;by('after').data=n.image_after;by('note').textContent=n.notes;by('bn').textContent=n.net+' · 前版';by('an').textContent=n.net+' · P5R2';by('netmeta').textContent=`线段 ${n.segments_before} → ${n.segments_after}；长度 ${n.length_before_mm} → ${n.length_after_mm} mm；宽度 ${n.widths_mm.join(' / ')} mm。物理状态 NOT_TESTED。`}
function boardView(){const k=by('board').value,l=by('layer').value,n=DATA.native[k],d=DATA.deltas[k];for(const [id,p]of [['Before','before'],['After','after']]){const src=`previews/${k}/${p}/${l}.png`;by('full'+id).src=src;by('full'+id+'Link').href=src}by('stats').textContent=`${DATA.labels[k]}：ERC ${n.ERC} / DRC ${n.DRC} / 未连接 ${n.unconnected} / 一致性 ${n.parity}；线段 ${d.before.tracks} → ${d.after.tracks}，过孔 ${d.after.vias}`;by('project').innerHTML=`<a href="../kicad/${n.board}/${n.board}.kicad_pro">打开原生工程</a> · <a href="reports/${k}/drc.json">最终DRC</a> · <a href="reports/${k}/erc.json">最终ERC</a> · <a href="reports/${k}/check_commands.json">命令和输入哈希</a> · <a href="reports/${k}/body_review_final.json">逐器件本体记录</a>`;by('widths').replaceChildren();for(const r of DATA.widths[k].paths){const tr=document.createElement('tr');for(const s of [`${r.net} ${r.source}→${r.destination}`,r.design_scenario_A,r.widest_complete_path_minimum_width_mm,r.conservative_complete_segment_path_R20_mohm.toFixed(2),r.drop20_mV.toFixed(2)]){const td=document.createElement('td');td.textContent=s;tr.append(td)}by('widths').append(tr)}}
by('board').onchange=()=>{by('search').value='';boardView();netList()};by('layer').onchange=boardView;by('search').oninput=netList;by('net').onchange=renderNet;by('prev').onclick=()=>{if(shown.length){by('net').value=(+by('net').value+shown.length-1)%shown.length;renderNet()}};by('next').onclick=()=>{if(shown.length){by('net').value=(+by('net').value+1)%shown.length;renderNet()}};boardView();netList();
</script></html>'''
(O/'index.html').write_text(page.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')))
print('Review README, width report and offline per-net comparison written')
