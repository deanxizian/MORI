"""Publish documented tooling inputs and bounded local assembly progress."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,re,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_profiled_tool'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=read(OUT/'screen.json');both=read(OUT/'both_anchors.json');sense=read(OUT/'sensitivity.json')
late=read(OUT/'late_servo_sequence.json');render=read(OUT/'render_manifest.json');loose=read(A8/'cam_sequence_loose/screen.json')
source_hash=sha(ROOT/'mechanical/mori_v1_2.blend')
for d in [screen,both,sense,late,render,loose]:assert d['source_main_sha256']==source_hash and not d['main_applied'] and d['whole_harness']=='BLOCKED'
assert screen['status']==render['status']=='PASS'
assert both['status']==sense['status']==late['status']==loose['status']=='BLOCKED'
assert [(r['profile'],r['angle_deg']) for r in screen['rows'] if r['status']=='PASS']==[('photo_profile',30.),('photo_profile',45.)]
chosen=next(r for r in both['rows'] if r['anchor']=='yaw' and r['angle_deg']==30.)
expanded=next(r for r in sense['rows'] if r['case']=='expanded_transition' and r['angle_deg']==30.)
assert chosen['status']==expanded['status']=='PASS'
assert render['physical_parts_restored_unchanged']==209 and render['review_sha256']==sha(OUT/'review.blend')
for r in render['images']:assert sha(OUT/r['file'])==r['sha256']
for r in read(OUT/'sources/receipt.json')['images']:assert sha(OUT/'sources'/r['file'])==r['sha256']

detail='剪尾工具轮廓复核有进展：Yaw侧30°名义检查通过，扩大工作包络后仍保留约0.66mm线间余量；不是工具实测。CAM端直向尾端操作区及后装舵机顺序仍未闭合，完整装配与裁线仍BLOCKED。主模型未改。'
md=f'''# CAM剪尾工具：官方资料与装后操作空间

**Yaw侧找到一个有余量的局部工具方向；完整线束仍为 BLOCKED。主模型 M1.47 未修改。**

供应商按图制作已确定。公开的连接器、端子与压接资料已经有[完整料号查询记录](../TOOLING_DETAILS.md)和[系列压接表](../CRIMP_REFERENCE.md)。MORI自己的路线、装配顺序和裁线长度需要由项目设计完成，不能把它们列成等待厂家提供的资料。

## 本轮找到的工具资料

KNIPEX 79 22 125的[官方产品页](https://www.knipex.de/produkte/elektronikzangen/praezisions-elektronik-seitenschneider-mit-geschraubtem-gelenk/praezisions-elektronik-seitenschneider-mit-geschraubtem-gelenk/7922125)和[官方数据表](https://www.knipex.com/sites/default/files/Product%20data%20sheet%20EN%2079%2022%20125.pdf)给出125×60×19mm、钳头宽A=11mm、刀口长B=10mm、关节厚D=6.5mm。厂家的[扎带应用说明](https://knowledge.knipex.com/en/why-is-the-oil-on-the-pliers-dark-brown)也列出此型号。

![官方正视照片](sources/official_top.png)
![厂家A/B/D尺寸示意](sources/official_head_dimensions.png)

旧检查把62mm宽的手柄工作区直接放在距刀尖10mm处。10mm是厂家标注的刀口长度，不能据此认定宽手柄从这里开始。新包络保留原来扩大的13mm钳头宽度，以官方照片补出细颈和渐宽过渡；完整长宽和厚度没有按机器人空间缩小。

**证据边界：**长宽厚、A/B/D为VENDOR_DOCUMENTED；过渡站点、开口余量和切口工作位置为ASSUMED。不是完整厂家CAD，也没有实际工具测量。图中的实心橙色形状是工作占用区，不是剪钳的精细外观模型。此次没有选定或采购工具。

![旧包络与分段包络](profile_comparison.svg)

## Yaw侧：装好头托后斜向操作的候选

![30度局部工具位置](yaw30_local.png)

在同一套已经落座的CAM/头托、两只舵机及四根规定CAM线路上，对照旧包络和新包络各14个方向。旧包络没有通过；新包络30°、45°通过。两者都检查完整工具及沿其长轴60mm直线进出工作体积。

| 候选 | 原工作包络 | 加宽/加厚、过渡提前后的包络 |
|---|---|---|
| 30° | PASS；线表面间隙保守下界{chosen['wire_minimum']['gap_lower_bound_mm']:.2f}mm，刚性件最小间隙{chosen['rigid_without_ties']['nearest_below_3mm']['gap_mm']:.2f}mm | PASS；线间隙保守下界{expanded['wire_minimum']['gap_lower_bound_mm']:.2f}mm |
| 45° | PASS；仅参考轮廓 | BLOCKED；扩大后的过渡靠近头托 |

这里的扩大为工作包络宽度+2mm、厚度+2mm，中间过渡站点提前3mm；它只是明确给定的敏感性检查，**不是照片测量误差或厂家公差**。因此后续优先考虑30°方向，不把45°也列成稳妥方案。

![旧45度包络](old45.png)
![新45度参考包络](new45.png)

局部图为便于观察，省略Z278mm以上的工具；[全工具图](yaw30_full.png)和实际检查都保留125mm全长。头壳、屏幕支架及未定型传动件尚未装入这一步。手部、刀片开合、夹紧力及真实扎带锁舌未验证；几何通过不能证明实际剪切完成。

## CAM插头侧：工具与尾端操作区分别看

![CAM端工具与直向操作区](connector_work.png)

在已落座头托上，工具本身在-15°、0°、15°三个方向避开刚性件和四根CAM线。但原先6×110×2.7mm的直向自由尾端操作区与Pitch_Servo相交，因此整步仍BLOCKED。红线表示这个操作区，**不表示真实柔软扎带一定沿这条长直线，也不表示实际扎带必须相交**。

暂缓安装两只舵机后，操作区避开刚性件，但仍进入规定的颈部引线余量。回放此前两条裸舵机装入路径，也先后遇到引线和Yaw扎带头；它们是具体路径失败，不是所有装法都被排除。

本轮前段另试的[保持线长、侧向展开的头托下放曲线](../cam_sequence_loose/screen.json)仍有引线余量或弯曲约束失败，没有采用。旧的42mm固定两端下放仍不能直接使用。

## 接下来还需完成

- 把CAM端预绑扎、Yaw端暂不锁紧、身体端松线暂存放入同一条可检查的装配路径；避免用固定两端的42mm抬升来替代真实工序。
- 补齐真实自由扎带尾端的操作形态和手部空间，再决定是否需要调整工序。当前没有新增孔、打印件或改变支架。
- 七根其余头部线、FPC、身体侧固定和完整插合视角针序仍待完成；四线模型长度不作为下料长度。

## 文件与复现

[独立Blender](review.blend) · [28组轮廓对照](screen.json) · [两处固定点26组检查](both_anchors.json) · [4组敏感性检查](sensitivity.json) · [后装舵机路径](late_servo_sequence.json) · [来源收据](sources/receipt.json) · [复现命令](commands.json) · [交付记录](review_manifest.json)。

主模型、STL、正式装配动画与硬件文件未修改。未发布制造图，未联系供应商或下单。
'''
(OUT/'README.md').write_text(md)

# Explanatory engineering sketch: exactly the tested working envelopes,
# not a traced or purportedly dimensioned manufacturer drawing.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520"><rect width="900" height="520" fill="#f8faf9"/><g font-family="system-ui,PingFang SC,sans-serif" fill="#243b3c"><text x="32" y="38" font-size="22">同一工具尺寸，修正工作包络的过渡位置</text>']
def poly(stations,cx):
    pts=[(cx-w*1.7/2,100+z*2.5) for z,w,d in stations]+[(cx+w*1.7/2,100+z*2.5) for z,w,d in stations[::-1]]
    return ' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
old=[(0,13,7.5),(10,13,7.5),(10,62,20),(125,62,20)]
svg += [f'<polygon points="{poly(old,230)}" fill="#8b99a0" stroke="#415159" stroke-width="2"/>',f'<polygon points="{poly(screen["profile_stations_z_width_depth_mm"],660)}" fill="#edb36b" stroke="#a76218" stroke-width="2"/>']
svg += ['<text x="135" y="77" font-size="18">旧工作包络（假定）</text><text x="517" y="77" font-size="18">按官方照片细化（仍为估算）</text>']
for z in [0,10,20,28,45,72,125]:
    y=100+z*2.5
    svg.append(f'<path d="M350 {y} H525" stroke="#acbdbb" stroke-dasharray="4 5"/><text x="403" y="{y-5}" font-size="13">{z} mm</text>')
svg += ['<text x="32" y="463" font-size="16">厂家尺寸：A = 11 mm，B = 10 mm，D = 6.5 mm；全长 125 mm。</text><text x="32" y="491" font-size="15">两组工作包络均有余量；没有把工具缩放到机器人空间里。中间站点不是厂家标注。</text></g></svg>']
(OUT/'profile_comparison.svg').write_text(''.join(svg))

fig=lambda f,t:f'<figure><a href="{f}"><img src="{f}" alt="{t}"></a><figcaption>{t}</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 剪尾工具与装配顺序</title>
<style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#243b3c;max-width:1080px;margin:32px auto;padding:0 24px 60px}h1{font-size:30px}a{color:#08727b}.note{padding:18px;background:#fff0d9;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccd8d4}table{width:100%;border-collapse:collapse}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前未完成项</a> · <a href="../cam_wired_cradle/index.html">上一步：42mm下放检查</a></p>
<h1>剪尾工具与装配顺序：有了一个局部可行方向</h1>
<p class="note">Yaw侧30°的工具工作区在本次名义几何检查中通过，扩大包络后仍有余量。完整线束仍为BLOCKED；主模型M1.47、正式动画均未修改。</p>
<p>供应商按图制作已确定。<a href="../TOOLING_DETAILS.md">端子完整料号的公开工艺数据</a>已经取得；MORI自己的路线、装配顺序和长度还需要由项目完成。</p>
<h2>厂家资料补齐了什么</h2><p>官方资料给出125×60×19mm、钳头A=11mm、刀口B=10mm、关节D=6.5mm。旧包络把宽手柄放在距刀尖10mm处；这个过渡位置没有厂家依据。</p>
<div class="grid">'''+fig('sources/official_top.png','官方照片：宽手柄前有细颈过渡。图片来自KNIPEX产品页。')+fig('sources/official_head_dimensions.png','厂家A/B/D尺寸示意；未标轮廓不能视为精确尺寸。')+'''
</div><p>新工具形状是参考照片的分段工作包络，仍标为ASSUMED；不是完整厂家CAD或实测工具。</p>'''+fig('profile_comparison.svg','相同尺寸基准，修正过早变宽的简化方式。')+'''
<h2>Yaw侧30°方向有余量</h2><div class="grid">'''+fig('yaw30_local.png','30°局部图。橙色为工作占用区；局部图省略Z278mm以上工具。')+fig('yaw30_full.png','完整125mm工具均参加了检查，另检查沿其长轴60mm的进出体积。')+f'''
</div><table><tr><th>方向</th><th>参考轮廓</th><th>扩大包络复核</th></tr><tr><td>30°</td><td>PASS；线表面余量下界{chosen['wire_minimum']['gap_lower_bound_mm']:.2f}mm</td><td>PASS；余量下界{expanded['wire_minimum']['gap_lower_bound_mm']:.2f}mm</td></tr><tr><td>45°</td><td>PASS</td><td>BLOCKED；过渡靠近头托</td></tr></table>
<p>扩大包络：宽度+2mm、厚度+2mm，中间过渡提前3mm。它是敏感性检查，不是厂家公差。后续优先研究30°。刀片开合、夹紧力、手部和真实工具仍未验证。</p>
<details><summary>查看旧/新45°包络对照</summary><div class="grid">'''+fig('old45.png','旧大盒状包络，45°被结构挡住。')+fig('new45.png','细化参考轮廓45°通过，但扩大后不通过。')+'''
</div></details><h2>CAM端还差尾端操作和完整顺序</h2>'''+fig('connector_work.png','橙色工具在0°可避开结构与四线；红色是旧110mm直向操作区，与Pitch_Servo相交。')+'''
<p>这不证明真实柔软扎带一定相交。即使暂缓两只舵机，旧直向操作区仍靠近颈部引线；随后按既有路径装舵机，也遇到引线或扎带头。不能把局部工具通过当成整段装配通过。</p>
<p>这轮另试的等长侧向展开路径也未通过，<a href="../cam_sequence_loose/screen.json">检查记录</a>保留。下一步需要把CAM端预绑扎、Yaw端暂不锁紧和身体端松线暂存放到同一条装入路径中。当前未新增孔、台阶或零件。</p>
<p>七根其余头部线、FPC及身体侧固定还未完成。图中颜色仅区别几何线路，不是供应商线色或已确认针序。裁线长度仍未放行。</p>
<p><a href="README.md">完整说明及官方来源链接</a> · <a href="review.blend">独立Blender</a> · <a href="screen.json">轮廓对照</a> · <a href="both_anchors.json">两处工具检查</a> · <a href="sensitivity.json">敏感性检查</a> · <a href="late_servo_sequence.json">后装舵机检查</a> · <a href="sources/receipt.json">来源记录</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">交付记录</a></p></html>'''
(OUT/'index.html').write_text(html)

logs=[('/tmp/mori_CAM_profiled_tool.log','screen.log'),('/tmp/mori_CAM_two_anchor_tool.log','both_anchors.log'),('/tmp/mori_CAM_profile_sensitivity.log','sensitivity.log'),('/tmp/mori_CAM_late_servo_sequence.log','late_servo_sequence.log'),('/tmp/mori_CAM_profiled_render.log','render.log'),('/tmp/mori_CAM_loose_assembly.log','loose_assembly.log')]
for src,dest in logs:shutil.copyfile(src,OUT/dest)
blender='/Applications/Blender.app/Contents/MacOS/Blender';base='mechanical/studies/prearrival_finish/harness_A8/'
commands=[blender+' -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base+n for n in ['screen_CAM_loose_assembly.py','check_CAM_profiled_tool.py','check_CAM_two_anchor_tool_access.py','check_CAM_profile_sensitivity.py','check_CAM_late_servo_sequence.py']]
commands += [blender+' -b '+base+'cam_wired_cradle/review.blend -t 4 --python-exit-code 1 --python '+base+'render_CAM_profiled_tool.py']
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+n for n in ['publish_CAM_profiled_tool.py','verify_delivery.py']]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},ensure_ascii=False,indent=2)+'\n')

p=PARENT/'work_status.json';status=read(p);row=next(r for r in status['remaining'] if r['id']=='harness');old=row['detail']
if not (OUT/'previous_work_status.json').exists():shutil.copyfile(p,OUT/'previous_work_status.json')
row.update(detail=detail,evidence='harness_A8/cam_profiled_tool/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_profiled_tool/index.html',
    CAM_profiled_tool_review='harness_A8/cam_profiled_tool/index.html',
    CAM_yaw_profiled_tool_nominal='PASS',CAM_yaw_profiled_tool_preferred_angle_deg=30,
    CAM_yaw_tool_assumed_expansion_gap_bound_mm=expanded['wire_minimum']['gap_lower_bound_mm'],
    CAM_profiled_tool_evidence='ASSUMED from manufacturer photos plus documented dimensions',
    CAM_connector_final_tail_workspace='BLOCKED',CAM_late_servo_paths='BLOCKED',CAM_whole_connected_installation='BLOCKED')
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old in s
s=s.replace(old,detail).replace('harness_A8/cam_wired_cradle/index.html','harness_A8/cam_profiled_tool/index.html').replace('最新：CAM整段装配检查','最新：CAM剪尾工具与工序');p.write_text(s)
for p,link in [(A8/'index.html','cam_profiled_tool/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_profiled_tool/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_profiled_tool/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM剪尾工具与工序</h2><p>{detail}</p><p><a href="{link}">查看官方资料和操作区复核</a>；下方保留历史阶段。</p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM剪尾工具与工序</h2><p>{detail}</p><p><a href="{link}">查看官方资料和操作区复核</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM剪尾工具与工序](cam_profiled_tool/index.html)：补齐官方钳头资料，30°局部工作区通过给定包络检查；完整带线装配仍未闭合，主模型M1.47未改。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
manifest={'status':'PASS','scope':'Documented tool inputs plus conditional local work-volume result; no full assembly or manufacturing approval',
    'script_sha256':sha(SCRIPT),'source_main_sha256':source_hash,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},
    'images_visually_reviewed':True,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==source_hash
print('CAM_PROFILED_TOOL_PUBLISHED',len(files),'files',flush=True)
