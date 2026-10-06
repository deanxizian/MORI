"""Publish installation failures as failures, preserving prior local passes."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,platform,shutil
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3];OUT=A8/'cam_wired_cradle'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=read(OUT/'screen.json');tools=read(OUT/'sequence_tools.json');witness=read(OUT/'witnesses.json');render=read(OUT/'render_manifest.json')
assert screen['status']==tools['status']=='BLOCKED'
assert witness['status']==render['status']=='PASS'
for r in [screen,tools,witness,render]:assert r['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend') and not r['main_applied']
assert len(screen['rows'])==15 and all(r['geometry']['status']=='PASS' for r in screen['rows'])
assert [r['lift_mm'] for r in screen['rows'] if r['status']=='PASS']==[0.,3.,6.]
assert 'CAM_without_own_UART' in screen['moving_ids']
assert len(tools['rows'])==48 and all(r['status']=='BLOCKED' for r in tools['rows'])
assert render['screen_sha256']==sha(OUT/'screen.json') and render['witnesses_sha256']==sha(OUT/'witnesses.json')
assert render['physical_parts_restored_unchanged']==209
assert render['review_sha256']==sha(OUT/'review.blend')
for r in render['images']:assert r['sha256']==sha(OUT/r['file'])
collision=next(r for r in witness['rows'] if r['lift_mm']==42.)
assert collision['physical_envelope_overlap_demonstrated'] and collision['surface_gap_upper_bound_mm']<0
detail='CAM整段装入检查发现顺序卡点：两处先固定后按旧动画抬高42mm，所设线形会自相交；0、3、6mm三个位置通过，9mm起该路径已有线间间隙不足。同一剪尾工具48组位置/方向均未闭合，需调整松线暂存和工序。主模型未改，完整线束及裁线仍未完成。'
md=f'''# CAM整段装配：下放路径与工序检查

**这轮排除了一个不能直接采用的装配组合。完整线束仍为 BLOCKED，主模型保持 M1.47。**

此前已分别检查颈部穿装、两个固定点、离机剪尾和装好后的线环。本轮将它们放在同一组装入位置检查，确认局部通过不等于能直接按原动画串起来安装。

## 头托抬高42mm时会发生什么

![零位：局部装好后的候选](seated.png)
![抬高42mm：失败的规定线形](raised42.png)

保持身体端和yaw侧导线不动，CAM板、插头、头托和插头侧扎带一起上移。每根线的活动段维持72.610689mm，四根CAM相邻尾段随板移动；没有把导线拉长来制造装配空间。

| 检查 | 结果 | 范围 |
|---|---|---|
| 15个位置的刚性零件检查 | PASS | 从0到42mm、间隔3mm；包含完整CAM板（UART单独计算）、插头、头托、两处扎带、现有固定件/候选结构 |
| 0、3、6mm的四线检查 | PASS | 仅这三个离散位置；不是0–6mm连续运动证明 |
| 9mm位置 | BLOCKED | CAM导线与另一条颈部引线的名义余量低于本研究要求的0.3mm |
| 12–27mm位置 | BLOCKED | 先发现与自身颈部过渡段的间隙不足；检查遇到首个失败后停止该位置的后续项目 |
| 30、33mm位置 | BLOCKED | 先发现CAM尾线与Pitch_Yoke间隙不足 |
| 36、39、42mm位置 | BLOCKED | 先发现非相邻线段回碰；42mm另做了明确相交见证 |

![42mm抬高时的回碰位置](wire_conflict42.png)

42mm处，同一根线相隔约{collision['separated_arclength_mm']:.1f}mm的两段在红点交叉。名义线径0.6604mm；这不是只差一个采样误差的情况，而是**当前规定线形的实体包络确有交叠**。图中没有模拟真实软线自然弯曲，不能据此断言所有装配方法都不可行。

![9mm处的间隙不足](neck_gap9.png)

9mm图中的红点表示低于0.3mm设计余量；它与42mm的实际包络相交是两个不同结论。局部图为看清线环隐藏了舵机、头托和CAM板；它们仍包含在相应检查中。

## 能否改变剪钳方向

沿用之前已记录尺寸的同一把剪钳工作包络，以自由尾端为轴试了8个方向、CAM组件0/6/12mm三种高度，以及yaw舵机已装/暂缓两种状态，共48组。

没有一组同时通过零件、既定线路和自由尾端工作区检查。向上工具在这些开敞工序中可避开刚性结构，但仍被已整理的线环挡住；其他方向多与侧壁、舵机或下方结构冲突。因此仅仅“晚装yaw舵机”尚未解决问题。

这排除的是**本次工具包络与规定线形的组合**，不是所有钳子、真实手部动作或可调整的松线位置。

## 对下一步装配设计的约束

1. 不能先锁紧两端、维持当前尾线形状，再把头托按旧动画抬高42mm。
2. 先剪尾、后理线的要求仍成立；两个局部离机步骤之间，必须补上整段松线如何暂存和转移。
3. 下一步先比较整体离机预装、身体端暂不固定及CAM板分步就位的顺序；有可检查的完整路径后再选用。当前没有为绕过冲突增设孔、凸台或零件。
4. 七根其余头部导线、FPC、身体侧固定和完整针腔视图仍待完成。当前四根路线的模型长度可继续参考，但不放行裁线。

原动画没有包含完整线束，本页不会把它标成已通过带线装配，也未替换正式动画。

## 文件与检查边界

- [独立Blender](review.blend)、[15个装入位置](screen.json)、[48组工具检查](sequence_tools.json)、[相交与间隙见证](witnesses.json)。
- [前一步：离机剪尾与模型长度基准](../cam_connector_install/index.html)。
- [复现命令](commands.json)、[图像来源](render_manifest.json)、[交付清单](review_manifest.json)。

主模型、正式STL、正式动画和硬件文件未修改。实体夹持、扎带穿紧、手部、制造公差和自然线形仍未验证。供应商按图制作已确定；当前资料不能用于生产下单。
'''
(OUT/'README.md').write_text(md)
fig=lambda f,t:f'<figure><a href="{f}.png"><img src="{f}.png" alt="{t}"></a><figcaption>{t}</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM整段装配检查</title>
<style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#243b3c;max-width:1080px;margin:32px auto;padding:0 24px 60px}h1{font-size:30px}a{color:#08727b}.note{padding:18px;background:#fff0d9;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccd8d4}table{width:100%;border-collapse:collapse}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前未完成项</a> · <a href="../cam_connector_install/index.html">上一步：工具与长度</a></p>
<h1>CAM整段装配：下放路径与工序检查</h1><p class="note">查出一处装配顺序卡点：当前规定线形不能随头托从42mm高度直接下放。完整线束仍为BLOCKED；主模型M1.47、正式动画均未修改。</p>
<p>CAM板、插头、头托与插头侧扎带一起移动，身体端和yaw侧保持不动。每根线的活动段始终为72.610689mm，没有人为拉长导线。</p>
<div class="grid">'''+fig('seated','零位：本次候选局部线路检查通过。屏幕、头壳及短轴尚未装入本工序。')+fig('raised42','抬高42mm：同一根线在红点处自相交，不能直接套用原来的无完整线束动画。')+'''
</div><h2>刚性零件能动，带上线以后有阻碍</h2>
<table><tr><th>检查</th><th>结果</th><th>结论范围</th></tr>
<tr><td>0–42mm，15个刚性位置</td><td>PASS</td><td>间隔3mm，包含完整CAM板和候选固定结构</td></tr>
<tr><td>四线在0、3、6mm</td><td>PASS</td><td>只限三个离散位置，连续运动未验证</td></tr>
<tr><td>9mm起的该组带线位置</td><td>BLOCKED</td><td>先后出现线间余量不足、靠近头座及回碰</td></tr>
<tr><td>42mm交叠见证</td><td>BLOCKED</td><td>规定曲线的两段实体包络确实交叠</td></tr></table>
<div class="grid">'''+fig('wire_conflict42','42mm：红点为同一根线的两段交叉。局部图隐藏舵机、头托和CAM板以看清线路。')+fig('neck_gap9','9mm：CAM尾线靠近另一根颈部引线，低于0.3mm设计余量；此图不代表两线已相交。')+'''
</div><p>图中为规定曲线，不是软线自然弯曲仿真。不能据此判断所有安装方式都不可行，也不能将离散位置的PASS称为完整装配通过。</p>
<h2>工具方向也已对照检查</h2><p>同一剪钳包络检查了8个方向×3个高度×2种舵机工序，共48组。没有一组同时避开结构、既定线路和尾端工作区。只晚装yaw舵机还不够；“先剪尾、后理线”的顺序仍需完整的松线暂存方案。</p>
<h2>下一步调整装配顺序</h2><p>比较整体离机预装、身体端暂不固定和CAM板分步就位，先得到可检查的完整路径，再选用。当前未为避让冲突增加孔、凸台或零件。其余七根头部导线、FPC和身体侧固定仍未闭合。</p>
<p>供应商按图制作已经确定。四根线的<a href="../cam_connector_install/length_datums_REFERENCE_ONLY.csv">模型长度表</a>仍仅供参考，裁线列未放行。</p>
<p><a href="README.md">完整说明</a> · <a href="review.blend">独立Blender</a> · <a href="screen.json">装入位置检查</a> · <a href="sequence_tools.json">工具检查</a> · <a href="witnesses.json">相交见证</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">交付记录</a></p></html>'''
(OUT/'index.html').write_text(html)
logs=[('/tmp/mori_CAM_wired_cradle_spectrum.log','screen.log'),('/tmp/mori_CAM_sequence_tools.log','sequence_tools.log'),('/tmp/mori_CAM_cradle_witnesses.log','witnesses.log'),('/tmp/mori_CAM_wired_render.log','render.log')]
for src,dest in logs:shutil.copyfile(src,OUT/dest)
base='mechanical/studies/prearrival_finish/harness_A8/'
blender='/Applications/Blender.app/Contents/MacOS/Blender'
commands=[blender+' -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base+n for n in ['check_CAM_wired_cradle_insertion.py','check_CAM_sequence_tools.py','prepare_CAM_cradle_witnesses.py']]
commands += [blender+' -b '+base+'cam_pitch_anchor/connector_anchor/review.blend -t 4 --python-exit-code 1 --python '+base+'render_CAM_wired_cradle.py']
commands += ['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+n for n in ['publish_CAM_wired_cradle.py','verify_delivery.py']]
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':platform.python_version()},'main_applied':False},indent=2)+'\n')
p=PARENT/'work_status.json';status=read(p);row=next(r for r in status['remaining'] if r['id']=='harness');old=row['detail']
row.update(detail=detail,evidence='harness_A8/cam_wired_cradle/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_wired_cradle/index.html',
    CAM_whole_connected_installation='BLOCKED',CAM_tested_42mm_insertion='BLOCKED',
    CAM_rigid_cradle_positions=15,CAM_discrete_clear_wire_lifts_mm=[0,3,6],
    CAM_sequence_tool_cases=48,CAM_sequence_working_tool_cases=0,
    CAM_wired_cradle_review='harness_A8/cam_wired_cradle/index.html')
p.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old in s
s=s.replace(old,detail).replace('harness_A8/cam_connector_install/index.html','harness_A8/cam_wired_cradle/index.html').replace('最新：CAM操作空间与长度基准','最新：CAM整段装配检查');p.write_text(s)
for p,link in [(A8/'index.html','cam_wired_cradle/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_wired_cradle/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_wired_cradle/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM整段装配检查</h2><p>{detail}</p><p><a href="{link}">查看下放与工具检查</a>；下方保留历史阶段。</p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM整段装配检查</h2><p>{detail}</p><p><a href="{link}">查看下放与工具检查</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM整段装配检查](cam_wired_cradle/index.html)：旧42mm下放与已固定线环的组合失败，需要调整松线暂存和装配顺序；主模型保持M1.47。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
files=[p for p in OUT.iterdir() if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
manifest={'status':'PASS','scope':'Publication of bounded assembly failures; not assembly approval',
    'script_sha256':sha(SCRIPT),'source_main_sha256':screen['source_main_sha256'],
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_WIRED_CRADLE_PUBLISHED',len(files),'files',flush=True)
