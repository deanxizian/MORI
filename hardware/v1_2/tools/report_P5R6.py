# -*- coding: utf-8 -*-
"""Local browsable P5R6 evidence index; no external upload."""
from pathlib import Path
import json,csv,html,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'hardware/v1_2';O=H/'layout_P5R6'
load=lambda p:json.loads(p.read_text())
def csvout(p,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
rows=[];panels=[];hints=[]
notes={'/M5_SW':'两端主路径双孔；bootstrap支路缩短。','/C5_SW':'两端主路径双孔；bootstrap支路缩短。','/M5_BOOT':'C62横放，检查BOOT与SW完整两端。','/C5_BOOT':'C72横放，BOOT线从焊盘内有效接触点直出。','/M5_EN':'消除原R60旁两个自由直角，保留反馈回路。'}
for kind,title,rev in [('motion','运动承载板','P5R5'),('power','电源板','P5R5'),('rear','后接口／开关板','P5R4')]:
    a,z=[load(O/f'reports/{kind}/{phase}_inventory.json') for phase in ['before','after']]
    for net in sorted({x['net'] for x in z['tracks']}):
        aa=[x for x in a['tracks'] if x['net']==net];zz=[x for x in z['tracks'] if x['net']==net]
        note='铜线/过孔几何不变；仅焊盘或实际标识修正。' if kind in ['motion','rear'] else notes.get(net,'铜线保留；与源版逐线比较。')
        rows.append({'board':kind,'net':net,'pcb_sha256':z['sha256'],'segments':len(zz),'before_mm':round(sum(x['length'] for x in aa),4),'after_mm':round(sum(x['length'] for x in zz),4),'widths_mm':sorted({x['width'] for x in zz}),'note':note,'diagnostic_view':f'net_review/{kind}/'+net.strip('/').replace('+','PLUS')+'.svg','native_DRC':'PASS','physical_tests':'NOT_TESTED'})
    hints += [dict(board=kind,**c,meaning='Geometry hint, not an automatic defect/waiver; inspect native body/corner reports.') for c in z['candidates']]
    views=[('combined','双面走线'),('front','F.Cu'),('back','B.Cu'),('silk_front','正面丝印'),('silk_back','背面丝印')]
    if kind=='power':views += [('ground_front','顶层地铜'),('ground_inner1','In1填铜'),('ground_inner2','In2填铜')]
    buttons=''.join(f'<button data-view="{v}" aria-pressed="{str(v=="combined").lower()}">{label}</button>' for v,label in views)
    panels.append(f'<section class="board" data-kind="{kind}"><h2>{title} · {rev} → P5R6</h2><div class="tools">{buttons}<a href="../kicad/MORI_{kind}_P5R6/MORI_{kind}_P5R6.kicad_pro">原生工程</a><a href="previews/{kind}/schematic/MORI_{kind}_P5R6.svg">原理图</a></div><div class="compare"><figure><figcaption>修改前 {rev}</figcaption><a class="oldlink" href="previews/{kind}/before/combined.svg"><img class="old" src="previews/{kind}/before/combined.png" alt="{title} 修改前"></a></figure><figure><figcaption>修改后 P5R6</figcaption><a class="newlink" href="previews/{kind}/after/combined.svg"><img class="new" src="previews/{kind}/after/combined.png" alt="{title} 修改后"></a></figure></div></section>')
csvout(O/'net_review.csv',rows);csvout(O/'screening_inventory.csv',hints)
if not (O/'test_records.csv').exists():
    csvout(O/'test_records.csv',[dict(test_id=f'T{i:02}',status='BLOCKED' if i==7 else 'NOT_TESTED',board_revision='motion/power/rear:P5R6; imu:P5R4',sample_serial='',pcb_sha256='',sch_sha256='',bom_revision='',firmware_hash='',date='',operator='',equipment_ids='',calibration='',ambient_C='',supply_V='',limit_A='',load_A='',duration_s='',waveform_path='',observed_V='',temperature_C='',raw_log='',observations='',stop_reason='',reviewer='') for i in range(1,9)])
src=H/'reviews/fourboards_P5R5_P5R4_external_20260925';vendor=[];(O/'sources').mkdir(exist_ok=True)
for row in load(src/'vendor_sources.json'):
    row=dict(row);p=ROOT/row['file'];dst=O/'sources'/p.name;shutil.copyfile(p,dst);assert hashlib.sha256(dst.read_bytes()).hexdigest()==row['sha256']
    row.update(file=str(dst.relative_to(ROOT)),measurements=False);vendor.append(row)
p=H/'sources/connectors_P4/SOFNG_MS202V.pdf';dst=O/'sources'/p.name;shutil.copyfile(p,dst)
vendor.append({'file':str(dst.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'manufacturer':'SOFNG','model':'MS-202V-G3','source':'Existing manufacturer drawing sources/connectors_P4/SOFNG_MS202V.pdf','read_date':'2026-09-25','use':'Contact states; lever direction NOT_TESTED','measurements':False})
(O/'reports/vendor_sources.json').write_text(json.dumps(vendor,ensure_ascii=False,indent=2)+'\n')
trs=''.join(f'<tr><td>{r["board"]}</td><td><a href="{r["diagnostic_view"]}">{html.escape(r["net"])}</a></td><td>{r["before_mm"]:.2f} → {r["after_mm"]:.2f}</td><td>{html.escape(r["note"])}</td></tr>' for r in rows)
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI P5R6 · 局部收尾</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#10151c;color:#e5e9ed;max-width:1600px;margin:auto;padding:32px}h1{font-size:32px}h2{margin-top:40px}a{color:#90d6ff}.tools{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0;align-items:center}button{background:#263645;border:1px solid #718190;border-radius:4px;padding:8px 12px;color:white;cursor:pointer}button[aria-pressed=true]{background:#12677e}.compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;min-width:0}figcaption{padding:8px}img{display:block;width:100%;border:1px solid #46505a}aside{background:#352d1c;border-left:4px solid #efbd66;padding:16px 22px}.badge{display:inline-block;border:1px solid #67c6a1;color:#9de2c6;border-radius:20px;padding:3px 12px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border-bottom:1px solid #39414c;text-align:left;vertical-align:top}.scroll{overflow:auto}footer{margin:32px 0;color:#afbbc6}@media(max-width:750px){body{padding:16px}.compare{grid-template-columns:1fr}}</style>
<header><p>MORI V1.2 · 2026-09-25 · PROTOTYPE</p><h1>封装、自举回路与接口标识 · P5R6</h1><p class="badge">四块当前板重跑 KiCad：ERC / DRC / 未连接 / parity 均为 0</p><p>运动板修正 BAT54H 焊盘；电源自举总平面走线13.21/14.21 → 8.75/9.68mm，四处SW换层为实际双孔并联，M5_EN两个直角例外已消除；电源/后板补齐实际丝印。板框、孔位、固定接口和针序不变。IMU保持P5R4。</p><aside><strong>状态边界：</strong>实物NOT_TESTED，未释放制造。保留两条In1安静地的R13偏离、后板CC2严格倒角FAIL和历史IMU短引出例外。外部PD/3S模块与RAW源端保护仍BLOCKED；SW1只印ON触点组合，拨杆方向待万用表确认。完整带器件/插头装配未验收。</aside>
<nav class="tools"><a href="README.md">修改说明</a><a href="review_disposition.md">逐项意见</a><a href="reports/verification.json">原生结果与例外</a><a href="reports/power/bootstrap_and_SW_banks.json">自举与并联孔证据</a><a href="reports/motion/diode_final_native_evidence.json">二极管焊盘证据</a><a href="reports/power/DC_model.json">DC敏感性</a><a href="test_plan.md">实测计划</a><a href="../handoff/mechanical_P5R6.json">机械交接</a><a href="../kicad/MORI_imu_P5R4/MORI_imu_P5R4.kicad_pro">保留的IMU工程</a></nav></header>
<p>点击图可查看可缩放原生SVG。走线图临时省略铺铜；地铜图来自实际保存填充。只有背面丝印视图按背面阅读镜像，其他视图保持统一PCB坐标。Fab/编辑器网名不算实际印刷。</p>'''+''.join(panels)+'''<section><h2>逐网复核</h2><p>诊断图配合原生DRC、本体/转角/载流路径检查使用；不单凭几何提示豁免规则。</p><div class="scroll"><table><thead><tr><th>板</th><th>网络</th><th>平面线长 mm</th><th>说明</th></tr></thead><tbody>'''+trs+'''</tbody></table></div><p><a href="all_segments.csv">所有线段</a> · <a href="all_vias.csv">所有过孔</a> · <a href="copper_changes.csv">铜线差异</a> · <a href="reports/interface_pairs.json">四板针号</a> · <a href="assembly_parts_with_mpn.csv">装配MPN</a> · <a href="test_records.csv">空白实测记录</a></p></section><footer>旧工程保留；没有采购、制造订单、Gerber或钢网输出。静态检查不证明温升、EMC、电池安全、平衡或60分钟续航。</footer><script>document.querySelectorAll('.board').forEach(p=>p.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{let v=b.dataset.view,k=p.dataset.kind;p.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));for(let[label,phase]of [['old','before'],['new','after']]){p.querySelector('img.'+label).src=`previews/${k}/${phase}/${v}.png`;p.querySelector('a.'+label+'link').href=`previews/${k}/${phase}/${v}.svg`}})));</script></html>'''
(O/'index.html').write_text(page)
links=re.findall(r'(?:href|src)="([^"]+)"',page)
for link in links:
    if not link.startswith(('http','#')):assert (O/link).exists(),link
for kind in ['motion','power','rear']:
    for phase in ['before','after']:
        for view in ['combined','front','back','silk_front','silk_back']+(['ground_front','ground_inner1','ground_inner2'] if kind=='power' else []):
            for ext in ['svg','png']:assert (O/'previews'/kind/phase/(view+'.'+ext)).exists()
(O/'reports/index_links.json').write_text(json.dumps({'status':'PASS','local_href_src_count':len(links),'dynamic_view_targets':'PASS','scope':'File targets checked; no claim of browser/bench testing'},indent=2)+'\n')
print('P5R6 index and evidence links PASS')
