# -*- coding: utf-8 -*-
"""Generate a local review index and blank test records from final evidence."""
from pathlib import Path
import json,csv,html,hashlib,re
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'hardware/v1_2';O=H/'layout_P5R5'
load=lambda p:json.loads(p.read_text())
def csvout(path,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)
notes={'/M5_FB':'反馈电阻/电容靠近U60，节点无过孔。','/C5_FB':'反馈组靠近U70，C75摆位消除出口短台阶。','/GND':'两路输入电容负端明确F.Cu连接；In1安静地为R13局部偏离。','/M5_SW':'芯片外侧F→B→F到电感；bootstrap也走外侧。','/C5_SW':'芯片外侧F→B→F到电感；无IC下方SW穿越。','/M5_VIN':'F60至U60，0.6mm最小显式通道；顶层输入电容连接。','/C5_VIN':'F70至U70，0.6mm最小显式通道；顶层输入电容连接。','/M5_EN':'为降压重排重新组织；R60旁两处严格0.5mm倒角例外。','/C5_EN':'U70外侧到JP70，保留与FB/功率节点隔离。','/WHEEL_ADC':'重排跨区域采样路径，不走被移动元件本体下；纹波耦合需实测。','/CHG_N':'受EN路径影响的局部信号重连；联锁拓扑不变。','/+5V_MOTION':'负载宽铜不变，反馈取样单独细线；不把细线当载流主干。','/+5V_CAM':'负载宽铜不变，取样与测试点支路局部整理。'}
rows=[];candidates=[];panels=[]
for kind,title in [('motion','运动承载板'),('power','电源板')]:
 a=load(O/f'reports/{kind}/before_inventory.json');z=load(O/f'reports/{kind}/after_inventory.json')
 for net in sorted({x['net']for x in z['tracks']}):
  aa=[x for x in a['tracks']if x['net']==net];zz=[x for x in z['tracks']if x['net']==net]
  rows.append(dict(board=kind,net=net,source_sha256=z['sha256'],segments=len(zz),before_mm=round(sum(x['length']for x in aa),4),after_mm=round(sum(x['length']for x in zz),4),widths_mm=sorted({x['width']for x in zz}),note='铜线与过孔不变；本轮仅标记和原理图T接点。'if kind=='motion'else notes.get(net,'原电气通道保留；少数可行自由转角处理，见UUID差异。'),diagnostic_view=f'net_review/{kind}/'+net.strip('/').replace('+','PLUS')+'.svg',native_DRC='PASS',physical_tests='NOT_TESTED'))
 for c in z['candidates']:candidates.append(dict(board=kind,**c,meaning='Geometric hint only; trace UUID and native DRC/body/corner reports govern. Not an automatic clearance waiver.'))
 views=[('combined','双面走线'),('front','F.Cu'),('back','B.Cu'),('silk_front','正面丝印'),('silk_back','背面丝印')]
 if kind=='power':views += [('ground_front','实际顶层填铜'),('ground_inner1','实际In1填铜'),('ground_inner2','实际In2填铜')]
 buttons=''.join(f'<button data-view="{v}" aria-pressed="{str(v=="combined").lower()}">{label}</button>'for v,label in views)
 panels.append(f'''<section class="board" data-kind="{kind}"><h2>{title} · P5R3 → P5R5</h2><div class="tools">{buttons}<a href="../kicad/MORI_{kind}_P5R5/MORI_{kind}_P5R5.kicad_pro">原生工程</a><a href="previews/{kind}/schematic/MORI_{kind}_P5R5.svg">原理图</a></div><div class="compare"><figure><figcaption>修改前 P5R3</figcaption><a class="oldlink" href="previews/{kind}/before/combined.svg"><img class="old" src="previews/{kind}/before/combined.png" alt="{title} 修改前"></a></figure><figure><figcaption>修改后 P5R5</figcaption><a class="newlink" href="previews/{kind}/after/combined.svg"><img class="new" src="previews/{kind}/after/combined.png" alt="{title} 修改后"></a></figure></div></section>''')
csvout(O/'net_review.csv',rows);csvout(O/'screening_inventory.csv',candidates)
tests=[dict(test_id=f'T{i:02}',status='NOT_TESTED',board_revision='P5R5',sample_serial='',pcb_sha256='',sch_sha256='',date='',operator='',equipment_ids='',calibration='',ambient_C='',supply_V='',limit_A='',load_A='',duration_s='',observed_V='',temperature_C='',firmware_hash='',raw_log='',observations='',stop_reason='',reviewer='')for i in range(1,10)]
if not(O/'test_records.csv').exists():csvout(O/'test_records.csv',tests)
sources=[]
for file,url,section in [('sources/parts/TI_TPS54302_RevC.pdf','https://www.ti.com/lit/ds/symlink/tps54302.pdf','7.4, pages 21-22'),('layout_P5R5/sources/TI_TPS54302EVM_SLVUAP9B.pdf','https://www.ti.com/lit/ug/slvuap9b/slvuap9b.pdf','pages 13-15')]:
 p=H/file;sources.append(dict(path=str(p.relative_to(ROOT)),url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),read_date='2026-09-24',section=section,status='VENDOR_DOCUMENTED',measurements=False))
(O/'reports/vendor_sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
links=''.join(f'<tr><td>{r["board"]}</td><td><a href="{r["diagnostic_view"]}">{html.escape(r["net"])}</a></td><td>{r["before_mm"]:.2f} → {r["after_mm"]:.2f}</td><td>{html.escape(r["note"])}</td></tr>'for r in rows)
page='''<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI P5R5 · 电源／运动板审查</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#10151c;color:#e5e9ed;max-width:1600px;margin:auto;padding:32px}h1{font-size:32px}h2{margin-top:40px}a{color:#90d6ff}.tools{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0;align-items:center}button{background:#263645;border:1px solid #718190;border-radius:4px;padding:8px 12px;color:white;cursor:pointer}button[aria-pressed=true]{background:#12677e}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;min-width:0}figcaption{padding:8px}img{display:block;width:100%;border:1px solid #46505a}aside{background:#352d1c;border-left:4px solid #efbd66;padding:16px 22px}.badge{display:inline-block;border:1px solid #67c6a1;color:#9de2c6;border-radius:20px;padding:3px 12px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #39414c;text-align:left;vertical-align:top}.scroll{overflow:auto}footer{margin:32px 0;color:#afbbc6}@media(max-width:750px){body{padding:16px}.compare{grid-template-columns:1fr}}
</style>
<header>
<p>MORI V1.2 · 2026-09-24 · PROTOTYPE</p>
<h1>两路降压与板面标记 · P5R5</h1>
<p class="badge">修改两板：KiCad ERC / DRC / 未连接 / 原理图差异均 0</p>
<p>输入电容正负端明确连接到芯片；FB分别缩短至6.28/6.86mm；两板新增实际丝印。运动铜不变，后接口和IMU保留P5R4，所有固定板框、孔位与针序不变。</p>
<aside>
<strong>明确例外与未验证项：</strong>两个安静GND回流区域使用In1，偏离源R13；M5_EN保留两个严格0.5mm倒角例外。孔铜、热、开关稳定性及整机装配未验证；外部PD/3S模块仍未选定，后板RAW检测线源端限流仍BLOCKED。</aside>
<nav class="tools">
<a href="README.md">修改说明</a>
<a href="review_disposition.md">逐项意见</a>
<a href="reports/verification.json">原生结果与规则</a>
<a href="reports/power/buck_returns.json">回流几何证据</a>
<a href="reports/power/DC_model.json">DC敏感性模型</a>
<a href="test_plan.md">测试计划</a>
<a href="../handoff/mechanical_P5R5.json">机械交接</a>
</nav>
</header>
<p>切换图层并点击图打开可缩放原生SVG。走线图临时省略铺铜；地铜图使用实际保存的填充。只有“背面丝印”按从背面阅读镜像，其余视图保持统一PCB坐标。图中的Fab文字用于审查，不等同实际印刷。</p>'''+''.join(panels)+'''<section>
<h2>逐网复核入口</h2>
<p>下列为诊断图；本体、转角、载流路径与原生检查分别留证，几何提示不自动等于缺陷。所有实物试验NOT_TESTED。</p>
<div class="scroll">
<table>
<thead>
<tr>
<th>板</th>
<th>网络</th>
<th>线长 mm</th>
<th>说明</th>
</tr>
</thead>
<tbody>'''+links+'''</tbody>
</table>
</div>
<p>
<a href="all_segments.csv">所有线段与UUID</a> · <a href="all_vias.csv">所有过孔</a> · <a href="copper_changes.csv">原生铜线差异</a> · <a href="reports/interface_pairs.json">四板针号复核</a> · <a href="test_records.csv">未填实測记录</a>
</p>
</section>
<footer>原工程保留。没有采购、制造订单、Gerber或钢网输出。静态检查不证明载流温升、EMC、电池安全或平衡性能。</footer>
<script>
document.querySelectorAll('.board').forEach(p=>p.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{let v=b.dataset.view,k=p.dataset.kind;p.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));for(let [label,phase]of [['old','before'],['new','after']]){p.querySelector('img.'+label).src=`previews/${k}/${phase}/${v}.png`;p.querySelector('a.'+label+'link').href=`previews/${k}/${phase}/${v}.svg`}})));
</script>
</html>'''
(O/'index.html').write_text(page)
for link in re.findall(r'(?:href|src)="([^"]+)"',page):
 if not link.startswith(('http','#')):assert(O/link).exists(),link
print('Review index, per-net inventory and blank physical records generated.')
