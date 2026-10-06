#!/usr/bin/env python3
"""Same-scale views of the seven marked regions, sourced only from native SVG."""
from pathlib import Path
import json,re,base64,subprocess
H=Path(__file__).resolve().parents[1];o=H/'layout_P5R1'
regions=[
 ('A','U5.1 / ARM_CLK',(7,4.5,12.5,10.8),'back','引脚改为先向外引出，在上方分支；不再贴着芯片边沿横接。'),
 ('B','J1/J2/J7 / 5V、FAULT_N、CHG_N',(38,1,62,8.5),'combined','5V 端点对齐；两条状态线整段重画，去掉短错位和绕 C8 的局部凸起。'),
 ('C','U3.3 → U2.1 / HEAD_OE_N',(17.3,12.5,20.3,18.4),'back','合并 0.0556 mm 错位的竖线，使用同一中心线。'),
 ('D','U2.5 / HEAD_BUS',(19,16.0,22.1,22.6),'back','移动过孔，使用一条竖直通道和一次引脚入口转向，删除连续小台阶。'),
 ('E','U2.8 / C2 去耦供电',(20.0,19.3,27.2,25.0),'back','C2 向 U2 移动 0.25 mm；电源先向外走，供电过孔放在明确的转角，地线对齐。旋转方案未采用。'),
 ('F','U2.3 → U100.A14 / HEAD_RX',(18,24.5,24.5,31.2),'combined','换层点移近 U2，正面直接以 45° 连到 A14，去掉底部横向绕行。'),
 ('G','J4.3/J4.4 / IMU_SCK、IMU_MOSI',(46.7,20.7,58,25.8),'combined','从通孔端子直接走背面，删除重叠折返、两颗过孔及多余短线。')]
(o/'marked_regions.json').write_text(json.dumps([dict(mark=a,title=b,window_mm=c,preferred_layer=d,change=e)for a,b,c,d,e in regions],ensure_ascii=False,indent=2)+'\n')
for rev in ['before','after']:
 for label,title,(x1,y1,x2,y2),layer,note in regions:
  for side in ['combined','front','back']:
   svg=(o/'previews'/rev/(side+'.svg')).read_text()
   svg=re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',f'width="{x2-x1}mm" height="{y2-y1}mm" viewBox="{x1} {y1} {x2-x1} {y2-y1}"',svg,count=1)
   (o/'previews'/rev/f'{label}_{side}.svg').write_text(svg)
# Native SVG comparisons, no external fonts, tracking, or network requests.
data=json.dumps([dict(mark=a,title=b,layer=d,note=e)for a,b,c,d,e in regions],ensure_ascii=False)
(o/'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 运动板 P5R1 · 七处圈选对比</title><style>
:root{font:16px/1.6 system-ui,sans-serif;color:#172633;background:#f0f3f5}body{max-width:1400px;margin:0 auto;padding:28px}h1{font-size:28px;margin-bottom:8px}h2{font-size:20px}p{max-width:1000px}a{color:#165e83}button{font:inherit;border:1px solid #bdcdd6;border-radius:8px;padding:7px 14px;cursor:pointer;background:white}button[aria-pressed=true]{background:#183e53;color:white}nav{position:sticky;top:0;background:#f0f3f5ed;padding:12px 0;z-index:2;display:flex;gap:8px;flex-wrap:wrap}section{background:white;border:1px solid #d6dfe5;border-radius:14px;margin:20px 0;padding:20px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;min-width:0}figcaption{font-weight:650;margin:4px 0}img{width:100%;display:block;background:#10151c;border-radius:8px;min-height:140px;max-height:660px;object-fit:contain}small{color:#4b6370}.links{display:flex;flex-wrap:wrap;gap:18px}.tag{color:#8b562b;font-weight:650}@media(max-width:760px){body{padding:12px}.pair{grid-template-columns:1fr}}
</style><body><h1>MORI 运动板 P5R1：七处圈选对比</h1><p>两列为相同位置、相同尺度的 KiCad 原生导出，底层保持正面坐标方向，方便与圈选截图逐一对应。覆铜只在临时查看副本中隐藏；工程中的覆铜与规则完整保留。</p><p class="tag">PROTOTYPE · 未台架验证。DRC 通过与布线外观验收分别记录。</p><div class="links"><a href="../kicad/MORI_motion_P5R1/MORI_motion_P5R1.kicad_pro">原生 KiCad 工程</a><a href="../kicad/MORI_motion_P5R1/MORI_motion_P5R1.kicad_pcb">原生 PCB</a><a href="README.md">修改说明与检查</a><a href="previews/MORI_motion_P5R1.pdf">原理图 PDF</a></div><nav><button data-layer="auto">按圈选重点显示</button><button data-layer="combined">正反面叠加</button><button data-layer="front">仅正面铜</button><button data-layer="back">仅背面铜</button></nav><main id="panels"></main><section><h2>全板查看</h2><div class="pair"><figure><figcaption>P5</figcaption><a href="previews/before/combined.svg"><img src="previews/before/combined.png"></a></figure><figure><figcaption>P5R1</figcaption><a href="previews/after/combined.svg"><img src="previews/after/combined.png"></a></figure></div></section><script>const regions='''+data+''';const main=document.getElementById('panels');for(const r of regions){const sec=document.createElement('section');sec.innerHTML='<h2>'+r.mark+' · '+r.title+'</h2><p>'+r.note+'</p><div class="pair">'+['before','after'].map(v=>'<figure><figcaption>'+(v==='before'?'修改前 P5':'修改后 P5R1')+'</figcaption><a id="a-'+r.mark+'-'+v+'"><img id="i-'+r.mark+'-'+v+'" alt="'+r.mark+' '+v+'"></a></figure>').join('')+'</div>';main.append(sec)}function showLayer(layer){for(const r of regions){const l=layer==='auto'?r.layer:layer;for(const v of ['before','after']){const src='previews/'+v+'/'+r.mark+'_'+l+'.svg';document.getElementById('i-'+r.mark+'-'+v).src=src;document.getElementById('a-'+r.mark+'-'+v).href=src}}for(const b of document.querySelectorAll('nav button'))b.setAttribute('aria-pressed',b.dataset.layer===layer)}for(const b of document.querySelectorAll('nav button'))b.onclick=()=>showLayer(b.dataset.layer);showLayer('auto');</script></body></html>''')
# A compact raster review sheet with native crops. SVG is the zoomable authority.
rows=[];y=50
for label,title,rect,side,note in regions:
 h=min(320,max(150,580*(rect[3]-rect[1])/(rect[2]-rect[0])))
 rows.append(f'<text x="24" y="{y+20}" fill="#24333d" font-size="20" font-family="Arial">{label} · '+title.replace('去耦供电','Decoupling').replace('、',', ').replace('→','to')+'</text>')
 for i,rev in enumerate(['before','after']):
  encoded=base64.b64encode((o/'previews'/rev/f'{label}_{side}.svg').read_bytes()).decode()
  x=24+i*610
  rows.append(f'<rect x="{x}" y="{y+35}" width="580" height="{h}" fill="#10151c"/><image x="{x}" y="{y+35}" width="580" height="{h}" href="data:image/svg+xml;base64,{encoded}"/>')
 y+=h+70
sheet='<svg xmlns="http://www.w3.org/2000/svg" width="1238" height="'+str(y)+'"><rect width="100%" height="100%" fill="#f0f3f5"/><text x="24" y="30" fill="#24333d" font-family="Arial" font-size="24">P5  (BEFORE)</text><text x="634" y="30" fill="#24333d" font-family="Arial" font-size="24">P5R1  (AFTER)</text>'+''.join(rows)+'</svg>'
(o/'previews/marked_comparison.svg').write_text(sheet)
node='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';sharp='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
subprocess.run([node,'-e','const sharp=require('+json.dumps(sharp)+');sharp(process.argv[1]).png().toFile(process.argv[2]);',str(o/'previews/marked_comparison.svg'),str(o/'previews/marked_comparison.png')],check=True)
print('Seven same-scale comparisons and offline HTML written')
