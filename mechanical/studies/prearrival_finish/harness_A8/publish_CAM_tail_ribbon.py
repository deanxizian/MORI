"""Publish the temporary-tail result without changing geometry or release gates."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,re,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_tail_ribbon'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
outer=read(OUT/'screen.json');inner=read(OUT/'inner_corridor.json');verify=read(OUT/'verification.json');render=read(OUT/'render_manifest.json')
source_hash=sha(ROOT/'mechanical/mori_v1_2.blend')
assert outer['status']=='BLOCKED' and inner['status']==verify['status']==render['status']=='PASS'
assert len(inner['rows'])==36 and len(verify['sensitivity_rows'])==9
assert render['physical_parts_preserved_unchanged']==209
for r in [outer,inner,verify,render]:assert r['source_main_sha256']==source_hash and not r['main_applied']
nom=verify['nominal'];rigid=nom['rigid_excluding_start_contact']['nearest_below_3mm']['gap_mm'];wire=nom['wire_gap']['gap_lower_bound_mm']
robust=min(r['rigid_excluding_start_contact']['nearest_below_3mm']['gap_mm'] for r in verify['sensitivity_rows'])
robust_wire=min(r['wire_gap']['gap_lower_bound_mm'] for r in verify['sensitivity_rows'])
detail=f'CAM端临时扎带尾端找到侧绕通道，36个形态及9个扩大/偏移复核通过；名义刚性间距约{rigid:.2f}mm，扩大后约{robust:.2f}mm。仍需完整穿带、收紧和带线装配顺序；最终裁线仍BLOCKED，主模型未改。'
md=f'''# CAM端扎带尾端：保留结构，利用现有侧向间隙

本轮局部临时尾端路径通过。完整线束、裁线图和整段带线装配仍为 **BLOCKED**。

## 公开资料和项目设计的边界

用户已确定供应商按图制作。公开的连接器、端子、适用线径和工具资料由项目检索；MORI的路线、固定点、端部直段、逐芯长度和安装顺序也由项目完成。

已取得的[JST完整料号压接参考](../TOOLING_DETAILS.md)保留原始查询和来源版本限制。当前可访问[JST SH目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)及[PH目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)。它们不等于已确认CAM板实际采购插座的完整型号和配对针腔视角。

[HellermannTyton T18R产品页](https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01712)允许手工或工具安装；既有[三份官方尺寸图](../cam_tie_install/README.md)提供尺寸来源。厂家给出的最小束径不是本研究自由尾端的弯曲寿命或拉紧力证明。

## 这次修正了什么判断

旧6×110×2.7mm直线操作区穿过Pitch_Servo。它是人为预留的空间，不是柔软扎带实际必须占据的形状。按图纸带宽、厚度上界2.7×1.3mm，把临时尾端先向侧面绕，再从小舵机与座壁之间通过，局部可以避开零件和四根CAM导线。

![同一剖面对比](tail_section_comparison.png)

右图橙色是安装时尚未剪掉的扎带尾端；**不是新增打印件、永久横梁或最终保留的凸出物**。全长110mm仍作为偏长的检查分配；真正成环后可用自由长度更短，不能把110mm当成采购或剪切尺寸。检查了整个带宽和厚度，剖面只用于说明路径。

## 实体检查

| 范围 | 结果 |
|---|---|
| 原先48个靠外侧的绕行形态 | BLOCKED，碰到座壁/头托；记录保留 |
| 位于舵机与座壁之间的36个形态 | PASS，刚性件和四根已规定CAM线路均无相交 |
| 选定例：先直行4mm、两处R5转弯、侧向列X=-34mm | 最近刚性间距{rigid:.2f}mm；导线表面间距下界{wire:.2f}mm |
| 9个扩大/偏移检查：截面增加0.2mm，起弯和侧向列各偏移±0.5mm | PASS；最小刚性间距{robust:.2f}mm，导线间距下界{robust_wire:.2f}mm |
| 保存后实体回读 | 单实体、闭合、体积与110mm带段核对通过 |
| 主模型/正式硬件/打印件 | 未修改；独立预览保留209件原有几何 |

上述R5及形状属于ASSUMED设计假设；偏移复核也不是厂家公差。扣头内孔、材料弯曲力和实际拉紧力没有被此检查认证。零件间距列排除了起点与本身扣头/已成环带身的预期接触。

![临时尾端总览](tail_overview.png)
![俯视路径](tail_top.png)

## 完整工序仍需继续

局部尾端检查让“必须给110mm直尾再开孔或拆掉舵机”不再成为本阶段的依据。它没有证明初次穿带、手指/拉紧工具操作、剪钳真实刀口开合或整段导线的形成顺序。之前固定两端后抬升头托42mm的路线仍失败，不将该失败改为通过。

继续完成的设计工作包括：让CAM端预绑扎、Yaw端暂不锁紧、身体端松线暂存和最后定长进入同一装配顺序；补其余头部导线、FPC和身体固定。最终下料长度仍空缺，不能交供应商直接加工。

[独立Blender](review.blend) · [36个局部形态](inner_corridor.json) · [回读与扩大检查](verification.json) · [先前48个失败形态](screen.json) · [完整说明](README.md) · [命令](commands.json) · [交付记录](review_manifest.json)。
'''
(OUT/'README.md').write_text(md)
figure=lambda file,caption:f'<figure><a href="{file}"><img src="{file}" alt="{caption}"></a><figcaption>{caption}</figcaption></figure>'
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM临时扎带尾端</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f4f6f5;color:#253b3d;max-width:1080px;margin:30px auto;padding:0 24px 60px}}a{{color:#096a74}}h1{{font-size:30px}}.note{{background:#fff0d9;padding:18px;border-radius:10px}}figure{{margin:22px 0}}img{{width:100%;border-radius:8px}}figcaption{{font-size:14px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #cad7d2}}table{{border-collapse:collapse;width:100%}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前未完成项</a> · <a href="../cam_profiled_tool/index.html">上一轮：剪尾工具</a></p>
<h1>CAM临时扎带尾端可以从现有间隙侧绕</h1>
<p class="note">局部尾端形态检查PASS；完整穿带、收紧和整段带线装配仍未闭合。主模型M1.47、STL、正式动画和硬件均未修改。</p>
<p>供应商按图制作已经确定。<a href="../TOOLING_DETAILS.md">JST完整端子压接参考</a>、<a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">SH目录</a>、<a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">PH目录</a>已经找到；线长、分支、固定位置和整机安装顺序仍由项目完成。</p>
<h2>原直线操作区过于局限</h2>
<p>旧检查把尾端固定为6mm宽、110mm长的直线操作区，因此穿过小舵机。改用官方尺寸图中带宽/厚度上界2.7×1.3mm的带段，沿小舵机和座壁之间的现有间隙绕行，局部可以通过。</p>
{figure('tail_section_comparison.png','左：旧直线工作空间与舵机相交。右：同一高度的临时柔性尾端路径。检查使用完整3D带段；剖面仅用来解释。')}
<p><strong>橙色是最后会剪掉的扎带尾端，不是新增打印横梁或保留凸起。</strong>110mm只是偏长的检查分配，实际成环后的自由长度更短；没有发布剪切尺寸。</p>
<h2>有多少空间</h2>
<table><tr><th>检查</th><th>结果</th></tr><tr><td>36个内部侧绕形态</td><td>均避开刚性件与四根CAM线</td></tr><tr><td>选定R5例</td><td>刚性间距{rigid:.2f}mm；导线表面间距下界{wire:.2f}mm</td></tr><tr><td>截面加0.2mm，路线偏移±0.5mm的9组检查</td><td>均通过；刚性间距至少{robust:.2f}mm，导线间距下界{robust_wire:.2f}mm</td></tr><tr><td>保存的带段实体</td><td>单个闭合实体，回读检查通过</td></tr></table>
<p>R5与绕行形态仍为设计假设，扩大检查不是供应商公差或材料弯曲认证。起点与自身扣头、成环带身的接触不计入刚性件间距。</p>
<div class="grid">{figure('tail_overview.png','完整临时尾端分配。两只舵机保留在位，屏幕支架与头壳尚未安装。')}{figure('tail_top.png','尾端先侧绕再向前伸出；尾端在安装完成后剪除。')}</div>
<h2>还有哪些设计工作</h2>
<p>还需把初次穿带、拉紧操作、真实刀口开合及松线暂存放进完整装配顺序。旧的固定两端再抬升头托42mm路径仍失败；本次局部通过不代替它。</p>
<p>其余头部导线、FPC、身体侧固定以及实际插合面针序仍待完成。最终下料长度未放行。三份<a href="../cam_tie_install/README.md">官方扎带尺寸图</a>已留存；<a href="https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01712">T18R官方页</a>允许手工或工具安装，但没有替本项目验证R5弯曲和拉紧力。</p>
<p><a href="README.md">完整记录</a> · <a href="review.blend">独立Blender</a> · <a href="inner_corridor.json">36组结果</a> · <a href="verification.json">实体回读与扩大检查</a> · <a href="screen.json">48个失败外侧路线</a> · <a href="commands.json">命令</a> · <a href="review_manifest.json">交付记录</a></p></html>'''
(OUT/'index.html').write_text(html)
for src,dest in [('ribbon','screen'),('plane','sections'),('inner','inner'),('verify','verification'),('render','render'),('plot','plot')]:
    shutil.copyfile('/tmp/mori_CAM_tail_'+src+'.log',OUT/(dest+'.log'))
blender='/Applications/Blender.app/Contents/MacOS/Blender';base='mechanical/studies/prearrival_finish/harness_A8/'
commands=[blender+' -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base+n for n in ['check_CAM_tail_ribbon_access.py','inspect_CAM_tail_plane.py','check_CAM_tail_inner_corridor.py','verify_CAM_tail_ribbon.py']]
commands += [blender+' -b '+base+'cam_wired_cradle/review.blend -t 4 --python-exit-code 1 --python '+base+'render_CAM_tail_ribbon.py']
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+n for n in ['plot_CAM_tail_sections.py','publish_CAM_tail_ribbon.py','verify_delivery.py']]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},indent=2)+'\n')
p=PARENT/'work_status.json';status=read(p);row=next(r for r in status['remaining'] if r['id']=='harness');old=row['detail']
if not (OUT/'previous_work_status.json').exists():shutil.copyfile(p,OUT/'previous_work_status.json')
row.update(detail=detail,evidence='harness_A8/cam_tail_ribbon/index.html');status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_tail_ribbon/index.html',
    CAM_connector_temporary_tail_route='PASS',CAM_connector_tail_route_review='harness_A8/cam_tail_ribbon/index.html',
    CAM_connector_tail_rigid_gap_mm=rigid,CAM_connector_tail_expanded_rigid_gap_mm=robust,
    CAM_connector_tail_route_evidence='ASSUMED easy-axis shape with sourced upper cross-section',
    CAM_connector_full_threading_tightening='NOT_TESTED',CAM_whole_connected_installation='BLOCKED')
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old in s
s=s.replace(old,detail).replace('harness_A8/cam_profiled_tool/index.html','harness_A8/cam_tail_ribbon/index.html').replace('最新：CAM剪尾工具与工序','最新：CAM临时扎带尾端');p.write_text(s)
for p,link in [(A8/'index.html','cam_tail_ribbon/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_tail_ribbon/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_tail_ribbon/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM临时扎带尾端</h2><p>{detail}</p><p><a href="{link}">查看临时尾端侧绕及剖面对比</a>；下方保留历史阶段。</p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM临时扎带尾端</h2><p>{detail}</p><p><a href="{link}">查看临时尾端侧绕及剖面对比</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM临时扎带尾端](cam_tail_ribbon/index.html)：利用现有间隙侧绕，36个形态和9组扩大检查通过；完整穿带、拉紧及整段安装仍待完成，主模型M1.47未改。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
(OUT/'review_manifest.json').write_text(json.dumps({'status':'PASS','scope':'Temporary tail geometry and delivery only, not complete assembly or manufacturing release',
    'script_sha256':sha(SCRIPT),'source_main_sha256':source_hash,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},
    'images_visually_reviewed':True,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==source_hash
print('CAM_TAIL_PUBLISHED',len(files),'files',flush=True)
