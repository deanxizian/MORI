#!/usr/bin/env python3
"""Create a local P2 native-CAD review PDF, viewer and scoped ZIP.

No manufacturing output, purchase, publication or native CAD mutation.
"""
from pathlib import Path
import json,hashlib,zipfile,re
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from pypdf import PdfReader

H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P2';P=O/'previews'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((O/'reports/verification.json').read_text())
assert report['native_cad_status']=='PASS'
for b in report['boards'].values():
    for f,v in b['input_hashes'].items():assert sha(ROOT/f)==v,'Native report stale: '+f
names=[('motion','运动载板','70 × 35 mm · 35 μm 外层铜'),('imu','身体 IMU','20 × 16 mm · 35 μm 外层铜'),('power','电源调理板','80 × 45 mm · 70 μm 外层铜')]
font=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf');pdfmetrics.registerFont(TTFont('CJK',str(font)))
pdf=P/'MORI_P2_Layout_Review.pdf';c=canvas.Canvas(str(pdf),pagesize=(420*mm,297*mm));c.setTitle('MORI P2 PCB Layout · Prototype Review')
for page,(kind,title,size) in enumerate(names,1):
    n='MORI_'+kind+'_P2';c.setFillColorRGB(.07,.12,.18);c.setFont('CJK',22);c.drawString(14*mm,280*mm,'MORI P2  /  '+title)
    c.setFont('CJK',10);c.drawString(14*mm,272*mm,size+'  ·  2 层 / 1.6 mm  ·  PROTOTYPE')
    c.setFont('CJK',9);c.drawRightString(406*mm,278*mm,'ERC 0   DRC 0   未连接 0   原理图差异 0')
    c.drawRightString(406*mm,271*mm,'KiCad 10.0.6 · 2026-09-22 · 未台架验证')
    for i,(stem,label) in enumerate([('top','正面铜层与器件'),('bottom','背面铜层与器件（已镜像）'),('top_assembly','正面装配图'),('bottom_assembly','背面装配图（已镜像）')]):
        col=i%2;row=i//2;x=(14+col*200)*mm;y=(139 if row==0 else 23)*mm;w=192*mm;h=104*mm
        c.setFillColorRGB(.07,.12,.18);c.setFont('CJK',10);c.drawString(x,y+h+4*mm,label)
        im=ImageReader(str(P/n/(stem+'.png')));iw,ih=im.getSize();s=min(w/iw,h/ih);c.drawImage(im,x+(w-iw*s)/2,y+(h-ih*s)/2,iw*s,ih*s)
    c.setFillColorRGB(.63,.30,.02);c.setFont('CJK',8.4)
    c.drawString(14*mm,13*mm,'规则差异未放行：固定 0.5 mm 转角退让、扇出/测试点、钢网开口。零 DRC 不代表完整规则符合或实机合格。')
    c.setFillColorRGB(.30,.34,.39);c.setFont('CJK',8);c.drawString(14*mm,7*mm,'原生 KiCad 导出图；连接器图为板端视图，对插针序须核对。整机安装净空未闭合。详见 layout_P2/README.md。')
    c.drawRightString(406*mm,7*mm,f'{page} / 3');c.showPage()
c.save();assert len(PdfReader(pdf).pages)==3

cards=[]
for kind,title,size in names:
    n='MORI_'+kind+'_P2'
    cards.append(f'''<article data-board="{n}"><div class="bar"><div><h2>{title}</h2><p>{size} · 2 层 / 1.6 mm</p></div><label>图层 <select aria-label="{title}图层"><option value="">铜层与器件</option><option value="_assembly">装配图</option></select></label></div><div class="views"><figure><figcaption>正面</figcaption><a href="{n}/top.svg"><img loading="lazy" src="{n}/top.png" alt="{title}正面原生KiCad预览"></a></figure><figure><figcaption>背面 · 已镜像</figcaption><a href="{n}/bottom.svg"><img loading="lazy" src="{n}/bottom.png" alt="{title}背面原生KiCad预览"></a></figure></div><p class="links"><a href="../../kicad/{n}/{n}.kicad_pro">KiCad 工程</a><a href="{n}/placement_native.csv">装配坐标</a><a href="../reports/{n}/drc.json">实际 DRC</a></p></article>''')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI P2 · Layout 审阅</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef1f5;color:#182736;font:15px/1.7 system-ui,-apple-system,"PingFang SC",sans-serif}main{max-width:1600px;margin:auto;padding:36px 28px}h1{font-size:34px;margin:0 0 8px}h2{font-size:23px;margin:0}p{margin:5px 0}a{color:#235a90}header{margin-bottom:26px}.notice{margin:18px 0;padding:14px 18px;border-left:4px solid #b07822;background:#fff6e5;color:#69451a}.bar{display:flex;justify-content:space-between;gap:20px;align-items:center}article{background:white;margin:22px 0;padding:22px;border-radius:12px;box-shadow:0 3px 16px #16314a0b}.views{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:16px 0 8px}figcaption{font-size:13px;color:#536573;margin-bottom:7px}img{width:100%;height:auto;display:block;border:1px solid #d8dde2}select{font:inherit;padding:8px;border:1px solid #b7c3ce;border-radius:6px}.links{display:flex;gap:20px;flex-wrap:wrap}.small{font-size:13px;color:#536573}@media(max-width:900px){.views{grid-template-columns:1fr}main{padding:20px 14px}.bar{align-items:flex-start;flex-direction:column}}
</style><main><header><p class="small">MORI · V1.2-H0.2-P2 · 2026-09-22</p><h1>三块载板，重新布局与布线</h1><p>每块板：ERC 0 / DRC 0 / 未连接 0 / 原理图差异 0。图像来自本版原生 KiCad 输出。</p><div class="notice">PROTOTYPE · 未制造放行。固定 0.5 mm 转角退让、扇出/测试点和钢网规则仍有差异；电源板安装、完整接口净空及台架测试未闭合。详情见规则说明。</div><p class="links"><a href="MORI_P2_Layout_Review.pdf">3 页 Layout PDF</a><a href="MORI_P2_Schematic_Review.pdf">20 页功能原理图</a><a href="../README.md">变更与规则说明</a><a href="../reports/verification.json">本版核验</a></p></header>'''+''.join(cards)+'''<p class="small">背面图已经镜像；放置坐标保留 KiCad 原生约定。裸板 STEP 不代表完整装配。没有采购、制造下单或远程发布。</p></main><script>document.querySelectorAll('article').forEach(card=>card.querySelector('select').addEventListener('change',e=>{const n=card.dataset.board;card.querySelectorAll('figure').forEach((f,i)=>{const stem=(i?'bottom':'top')+e.target.value;f.querySelector('img').src=n+'/'+stem+'.png';f.querySelector('a').href=n+'/'+stem+'.svg'})}));</script></html>'''
(P/'index.html').write_text(html)

# Limit the ZIP to this review revision. No P1 archives, router caches,
# negative-rule test PCB, tools runtimes or manufacturing files.
files=set([O/'README.md',O/'pcb-rules-source.json',O/'probe_map.csv',O/'reports/verification.json',O/'reports/copper_estimate.json',H/'handoff/mechanical_P2.json',H/'calculations/layout_P2_power.py'])
files.update(p for p in P.rglob('*') if p.is_file())
for kind,_,_ in names:
    n='MORI_'+kind+'_P2';d=H/'kicad'/n
    files.update(p for p in d.rglob('*') if p.is_file() and p.suffix not in ['.dsn','.ses','.kicad_prl','.pyc','.lck'] and not p.name.startswith('.'))
    files.update(p for p in (O/'reports'/n).iterdir() if p.is_file() and (p.name in ['drc.json','erc.json','netlist.xml','check_commands.json','exports.json'] or p.name.startswith('check_') and p.suffix=='.log'))
    files.add(H/'mechanical'/(n+'_BARE_BOARD.step'))
files.add(O/'reports/rule_probe/verification.json')
files.update(H/'sources/parts'/f for f in ['TDK_ICM42688P_DS000347_v1p9.pdf','TDK_AN000393_v2p4.pdf'])
out=H/'releases/assets/P2';out.mkdir(parents=True,exist_ok=True);archive=out/'MORI_V1.2-H0.2-P2_PROTOTYPE_REVIEW.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
    z.writestr('START_HERE.txt','MORI P2 PROTOTYPE REVIEW ONLY\nOpen hardware/v1_2/layout_P2/README.md or previews/index.html.\nNative ERC/DRC/connectivity/parity pass. Full source-rule conformance and mechanical/bench qualification remain open. No Gerber, drill or manufacturing authorization. P1 comparison baselines and full toolchain stay in the original MORI workspace. Generic optional 3D previews require the standard KiCad10 model library; exported STEP is BARE BOARD ONLY.\n')
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print('3-page native layout PDF; HTML viewer;',len(files),'review files;',archive.stat().st_size,'byte ZIP:',archive)
