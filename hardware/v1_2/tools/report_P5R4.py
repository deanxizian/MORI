"""Build a portable, local review page and blank physical-test records."""
from pathlib import Path
import json, csv, html, hashlib, re

ROOT=Path(__file__).resolve().parents[3]
H=ROOT/'hardware/v1_2'; O=H/'layout_P5R4'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def csvout(p,rows):
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with p.open('w',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fields);w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)

notes={
 'rear':{'/CC2':'D3.1先保护再输出；专项同网旁路检查PASS；(13.25,8.5)保留R14例外。',
         '/CC1':'D2输出沿左侧/下沿通道到J2.3，为D1/C1重排让出位置；无盲目等长。',
         '/GND':'D3新近端过孔、D2明确地短线、D1外侧倒角和C1地过孔；填铜有效连接已列证据，高频回流未验证。',
         '/VBUS_FUSED':'F1输出逃线简化；D1移位旋转；主路0.6mm与两颗1/.45过孔；C1支路0.3mm。',
         '/VBUS_RAW':'USB右侧汇流过孔上移并重连检测支路；J2.5仍未加源端限流，BLOCKED。',
         '/MASTER_RETURN':'原有SW1→J3.1信号通道保留；非电机电源。',
         '/LOOP_3V3':'原有SW1/J3.3逻辑解锁回路保留。',
         '/CLR_N':'原有SW1/J3.4逻辑回路保留；恢复开关不得自动ARM。'},
 'imu':{'/+3V3':'C1/C2重排，VDD8→C1.1显式路径1.58mm；C3保留。',
        '/GND':'C1地在芯片外侧明确连向GND6；C2加入；原LGA两处短转角保留例外。',
        '/DRDY':'绕至重新摆放C1/C2的外侧；不跨过电容本体。',
        '/MISO_IC':'U1到R1近源33Ω保持原铜线，非新加重复串阻。',
        '/MISO':'串阻外侧原走线/换层保持；按实际线束做时序验证。',
        '/SCK':'原铜线保持；无蛇形等长。',
        '/MOSI':'原铜线保持；无蛇形等长。',
        '/CS_N':'原上拉与铜线保持。'}}
netrows=[];candidate_rows=[]
for kind in ['rear','imu']:
    inv=load(O/f'reports/{kind}/after_inventory.json');before=load(O/f'reports/{kind}/before_inventory.json')
    for net in sorted({t['net']for t in inv['tracks']}):
        ts=[t for t in inv['tracks']if t['net']==net];bs=[t for t in before['tracks']if t['net']==net]
        path=f'net_review/{kind}/'+net.strip('/').replace('+','PLUS')+'.svg'
        netrows.append(dict(board=kind,net=net,source_sha256=inv['sha256'],segments=len(ts),
            length_before_mm=round(sum(t['length']for t in bs),4),length_after_mm=round(sum(t['length']for t in ts),4),
            widths_mm=sorted({t['width']for t in ts}),note=notes[kind][net],diagnostic_view=path,
            native_DRC='PASS',physical_tests='NOT_TESTED',strict_style_equivalence='NOT_TESTED'))
    for c in inv['candidates']:
        candidate_rows.append(dict(board=kind,**c,net_context=notes[kind].get(c['net'],''),
            scope='Geometric hint, not automatically an error or a clearance waiver; see original UUID and native views',
            strict_style_approval='NOT_TESTED'))
csvout(O/'net_review.csv',netrows);csvout(O/'screening_inventory.csv',candidate_rows)

records=[]
for i in range(1,12):
    records.append(dict(test_id=f'T{i:02}',status='NOT_TESTED',pcb_revision='P5R4',sample_serial='',board_sha256='',
        date='',operator='',equipment_ids='',harness_id='',firmware_hash='',module_mpn_revision='',
        supply_voltage_V='',current_limit_A='',measured_current_A='',voltage_points='',ambient_C='',
        measured_temperatures_C='',elapsed_s='',error_counters='',raw_log_path='',observations='',
        stop_reason='',pass_criteria_revision='',reviewer=''))
csvout(O/'test_records.csv',records)
refs=[]
for f in ['TDK_AN000393_v2p4.pdf','TDK_ICM42688P_DS000347_v1p9.pdf']:
    p=H/'sources/parts'/f
    refs.append(dict(file=str(p.relative_to(ROOT)),sha256=sha(p),read_date='2026-09-24',kind='VENDOR_DOCUMENTED',physical_measurement=False))
(O/'reports/vendor_sources.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2)+'\n')

panels=[]
for kind,title in [('rear','Type-C／电源开关板'),('imu','IMU 板')]:
    options=''.join(f'<button data-view="{v}" aria-pressed="{str(v=="combined").lower()}">{label}</button>'for v,label in [('combined','双面走线'),('front','F.Cu'),('back','B.Cu')])
    panels.append(f'''<section class="board" data-kind="{kind}"><h2>{title}</h2>
    <div class="tools">{options}<a href="../kicad/MORI_{kind}_P5R4/MORI_{kind}_P5R4.kicad_pro">KiCad P5R4</a>
    <a href="previews/{kind}/schematic/MORI_{kind}_P5R4.svg">原理图</a><a href="previews/{kind}/after/ground.svg">B.Cu 实际填铜</a></div>
    <div class="compare"><figure><figcaption>P5R3 修改前</figcaption><a class="oldlink" href="previews/{kind}/before/combined.svg"><img class="old" src="previews/{kind}/before/combined.png" alt="{title}修改前"></a></figure>
    <figure><figcaption>P5R4 修改后</figcaption><a class="newlink" href="previews/{kind}/after/combined.svg"><img class="new" src="previews/{kind}/after/combined.png" alt="{title}修改后"></a></figure></div></section>''')
links=''.join(f'<tr><td>{r["board"]}</td><td><a href="{r["diagnostic_view"]}">{html.escape(r["net"])}</a></td><td>{r["length_before_mm"]:.2f} → {r["length_after_mm"]:.2f}</td><td>{html.escape(r["note"])}</td></tr>'for r in netrows)
paste=''.join(f'<figure><figcaption>{label}</figcaption><a href="previews/imu/{phase}/paste.svg"><img src="previews/imu/{phase}/paste.png" alt="{label}锡膏开口"></a></figure>'for phase,label in [('P5R2','P5R2：全局 +0.05mm'),('before','P5R3：全局 0'),('after','P5R4：U1 专用 90%线性')])
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI P5R4 · 后接口与IMU审查</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#10151c;color:#e5e9ed;margin:0;padding:32px;max-width:1500px;margin:auto}h1{font-size:32px;line-height:1.3}h2{font-size:24px;margin-top:44px}a{color:#90d6ff}button{background:#263645;color:#fff;border:1px solid #718190;padding:8px 14px;border-radius:5px;cursor:pointer}button[aria-pressed=true]{background:#12677e;border-color:#64e0fc}.tools{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:16px 0}.compare,.paste{display:grid;grid-template-columns:1fr 1fr;gap:20px}.paste{grid-template-columns:repeat(3,1fr)}figure{margin:0;min-width:0}figcaption{padding:10px 0;color:#bbc9d7}img{display:block;width:100%;height:auto;border:1px solid #46505a}aside{background:#352d1c;border-left:4px solid #efbd66;padding:15px 22px}.badge{display:inline-block;border:1px solid #67c6a1;color:#9de2c6;padding:2px 12px;border-radius:20px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;border-bottom:1px solid #39414c;text-align:left;vertical-align:top}td:nth-child(2){white-space:nowrap}code{font-size:14px}footer{margin:40px 0;color:#a6b6c3}@media(max-width:760px){body{padding:18px}.compare,.paste{grid-template-columns:1fr}.tablewrap{overflow:auto}}
</style><header><p>MORI V1.2 · 2026-09-24 · PROTOTYPE</p><h1>后接口与 IMU · P5R4 审查修改</h1>
<p class="badge">两板原生 ERC / DRC / 未连接 / 原理图差异：全部 0</p>
<p>后板修正 CC2 保护顺序与 D3 接地，重排 D1/C1；IMU 重排 VDD 去耦到 GND6，并增加专用 Paste 和传感器轴标。运动与电源板保持 P5R3；板框、安装孔、连接器针序不变。</p>
<aside><strong>尚未释放制造：</strong>外接 PD／3S 充电模块未选定；J2.5 RAW 检测线源端限流尚未完成。100µm 钢网为待工艺确认方案。实物、温升、ESD、SPI 和完整装配均未验证。</aside>
<nav class="tools"><a href="README.md">修改说明</a><a href="review_disposition.md">逐项审查</a><a href="reports/verification.json">真实检查</a><a href="test_plan.md">实测计划</a><a href="test_records.csv">空白记录</a><a href="../handoff/mechanical_P5R4.json">机械交接</a></nav></header>
<p>点击视图切换；点击图打开可缩放原生 SVG。背面视图保持 PCB 坐标、未镜像。走线对照临时省略填铜，独立地铜图来自实际保存的填充；不把示意图当原生工程。</p>
'''+''.join(panels)+'''
<section><h2>IMU 锡膏开口</h2><p>铜焊盘仍 0.475×0.250mm；最终有效开口 0.4275×0.225mm。KiCad 局部 -5% 每边比例实现 90% 线性尺寸。100µm 厚度的保守矩形释放面积比约0.737，需贴片厂确认；Mask 未改。</p><div class="paste">'''+paste+'''</div><p><a href="reports/imu/stencil_design.json">逐焊盘开口／面积比</a></p></section>
<section><h2>逐网检查入口</h2><p>下表链接为诊断图；原生图与实际 ERC/DRC 报告在上方。三处严格 R14 倒角例外保留为实际 FAIL；不是所有布线偏好自动通过。</p><div class="tablewrap"><table><thead><tr><th>板</th><th>网络</th><th>总铜线长度 mm</th><th>处理与限制</th></tr></thead><tbody>'''+links+'''</tbody></table></div>
<p><a href="all_segments.csv">全部线段／UUID</a> · <a href="all_vias.csv">全部过孔</a> · <a href="screening_inventory.csv">几何提示清单</a> · <a href="reports/rear/CC2_flowthrough.json">CC2无旁路专项检查</a></p></section>
<footer>KiCad 10.0.6。原 P5R2/P5R3 保留；没有采购或制造订单，没有 Gerber 或钢网制造文件。ERC/DRC 不证明电池安全、EMC、载流能力或平衡性能。</footer>
<script>
document.querySelectorAll('.board').forEach(panel=>{
panel.querySelectorAll('button[data-view]').forEach(btn=>btn.addEventListener('click',()=>{
 const v=btn.dataset.view,k=panel.dataset.kind;
 panel.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===btn)));
 for(const [label,phase]of [['old','before'],['new','after']]){
 panel.querySelector('img.'+label).src=`previews/${k}/${phase}/${v}.png`;
 panel.querySelector('a.'+label+'link').href=`previews/${k}/${phase}/${v}.svg`;
 }
}));});
</script></html>'''
(O/'index.html').write_text(page)
# Check every static local page link/image, excluding future zip links.
for link in re.findall(r'(?:href|src)="([^"]+)"',page):
    if not link.startswith(('http','#')):assert (O/link).exists(),link
print('Review page, test templates, source hashes and net inventories generated.')
