"""Export exact review SVGs as PNGs and a single numbered review page.

Quick Look crops some non-square SVG previews. Render a square document at
2x and remove only the added margin, preserving every original drawing pixel.
No model geometry or design choice is changed here.
"""
from pathlib import Path
import hashlib,html,json,subprocess,xml.etree.ElementTree as ET
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE/'review_images';TMP=OUT/'render_sources'
OUT.mkdir(exist_ok=True);TMP.mkdir(exist_ok=True)
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ITEMS=[
 ('thin_mount_comparison','items-1-2','1、2 · 相机座与俯仰舵机螺母座','上半部：填平旧相机孔腔。下半部：螺母移入现有耳座，填平原轴承孔上方薄壁；后续经确认，移入后的螺母槽去掉薄底边，上缘加厚0.7mm，顶壁1.2mm。'),
 ('remaining_seats_comparison','items-3-5','3、5 · 水平舵机螺母槽与轮轴承挡边','图的上半部对应第5项轴承挡边；下半部对应第3项水平舵机螺母槽。'),
 ('drive_nut_entry','item-4','4 · 四个轮驱连接螺母','旧封闭槽与已采用短侧入口对比；配套DIN934 M2和M2×8一起采用，孔轴和外轮廓保持。'),
 ('body_seam_comparison','item-6','6 · 机身四处拼缝固定点','上方是孔位对比，下方是上壳取出路径；先卸车轮、下壳、头部及固定桥。'),
 ('weact_E_alignment','item-7','7 · WeAct E 接口','对比官方排针与当前基板孔阵列。直针改版或保留弯针另接复位线，已交硬件对话确认路线并处理J3冲突。'),
]
records=[];commands=[]
def run(cmd):
 p=subprocess.run(cmd,capture_output=True,text=True)
 commands.append({'command':cmd,'returncode':p.returncode,'output':p.stdout+p.stderr})
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
for name,anchor,title,caption in ITEMS:
 source=HERE/(name+'.svg');root=ET.parse(source).getroot()
 w=float(root.get('width'));h=float(root.get('height'));side=max(w,h)
 vb=root.get('viewBox')
 if vb:assert list(map(float,vb.replace(',',' ').split()))==[0,0,w,h],(name,vb)
 paths=list(root.iter('{http://www.w3.org/2000/svg}path'))
 primitives=sum(len(list(root.iter('{http://www.w3.org/2000/svg}'+kind))) for kind in ['circle','line','polygon','polyline'])
 assert (paths or primitives) and all(p.get('d','').strip() for p in paths),(name,'empty drawing geometry')
 root.set('width',str(side));root.set('height',str(side));root.set('viewBox',f'0 0 {side:g} {side:g}')
 root.set('preserveAspectRatio','xMinYMin meet')
 temp=TMP/(name+'.svg');ET.ElementTree(root).write(temp,encoding='utf-8',xml_declaration=True)
 run(['/usr/bin/qlmanage','-t','-s',str(int(side*2)),'-o',str(TMP),str(temp)])
 raster=TMP/(temp.name+'.png')
 with Image.open(raster) as im:
  rw,rh=im.size
 assert rw==rh,(name,rw,rh)
 width=round(w/side*rw);height=round(h/side*rh);dest=OUT/(name+'.png')
 # Finish vector rasterization by removing only our added canvas margin.
 # sips centres its crop on this OS even when the offset is zero.
 with Image.open(raster) as im:im.crop((0,0,width,height)).save(dest)
 with Image.open(dest) as im:
  assert im.size==(width,height)
  assert im.convert('RGB').getextrema()!=((255,255),(255,255),(255,255)),(name,'blank raster')
 records.append({'title':title,'source_svg':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'png':'review_images/'+dest.name,'png_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'pixels':[width,height],'svg_nonempty_paths':len(paths),'design_status':'HARDWARE_HANDOFF' if name=='weact_E_alignment' else 'ADOPTED_M1_43; historical comparison drawing'})

nav=''.join(f'<a href="#{anchor}">{html.escape(title)}</a>' for _,anchor,title,_ in ITEMS)
cards=''.join(f'<section id="{anchor}"><h2>{html.escape(title)}</h2><p>{html.escape(caption)}</p><a href="review_images/{name}.png" target="_blank"><img src="review_images/{name}.png?v={records[i]["png_sha256"][:12]}" alt="{html.escape(title)}"></a><p class="actions"><a href="review_images/{name}.png" target="_blank">打开完整 PNG</a><a href="{name}.svg">原始矢量图</a></p></section>' for i,(name,anchor,title,caption) in enumerate(ITEMS))
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 1–6已应用 / 7交硬件处理</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#edf1f3;color:#243b45;font:17px/1.7 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1250px;margin:auto;padding:28px 20px 64px}}h1{{font-size:30px;line-height:1.4}}h2{{font-size:23px;line-height:1.4}}a{{color:#146b6b}}nav{{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}}nav a{{padding:8px 14px;background:white;border:1px solid #ccd8df;border-radius:8px;text-decoration:none}}section{{background:white;border:1px solid #cbd6dd;border-radius:12px;padding:22px;margin:25px 0;scroll-margin-top:18px}}section img{{display:block;width:100%;height:auto;border:1px solid #e1e6eb}}.note{{padding:14px 18px;background:#fff3db;border-radius:8px}}.actions{{display:flex;gap:24px}}@media(max-width:650px){{main{{padding:18px 10px}}section{{padding:12px}}h1{{font-size:25px}}h2{{font-size:20px}}}}</style><main>
<a href="../../index.html#remaining">返回当前模型与状态</a><h1>1–6 已应用 · 7 已交硬件对话</h1><p>所有图均提供 PNG，可以直接点击放大。编号与聊天中的确认清单一致。</p><p class="note">问题1–6已应用到M1.43。此处保留原方案对比图；最终螺母承压贴合、孔口导入和配套五金以当前主模型及报告为准。第2项追加修正已获确认，可查看<a href="pitch_seat_candidate.png">修正前与采用方案</a>（图制作于确认前，右侧现已采用）。第7项已交硬件对话处理。</p><nav>{nav}</nav>{cards}<p><a href="WEACT_E_HANDOFF.md">第7项接口方案和 J3 干涉说明</a></p></main></html>'''
(HERE/'comparisons.html').write_text(page)
(OUT/'manifest.json').write_text(json.dumps({'status':'PASS','model_geometry_modified':False,'rasterizer':'macOS Quick Look; square canvas2x, Pillow remove only added margin at box(0,0,width,height)','images':records,'commands':commands},ensure_ascii=False,indent=2)+'\n')
print('REVIEW_IMAGES_PUBLISHED',[(r['png'],r['pixels']) for r in records])
