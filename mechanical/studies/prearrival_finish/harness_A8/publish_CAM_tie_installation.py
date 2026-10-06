"""Publish catalogue receipts and bounded bench checks, without adopting CAD."""
from pathlib import Path
from datetime import datetime, timezone
from html import escape
import hashlib, json, re

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3]
OUT=A8/'cam_tie_install'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=read(OUT/'oriented_tie_screen.json');bench=read(OUT/'bench_access.json')
render=read(OUT/'render_manifest.json');receipt=read(OUT/'sources/receipt.json')
dims=read(OUT/'sources/dimensions.json')
assert screen['status']==bench['status']==render['status']=='PASS'
assert screen['source_main_sha256']==bench['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assert bench['closed_ring_slide_from_below']['status']=='BLOCKED'
assert bench['closed_ring_before_servo']['status']==bench['servo_with_preplaced_tie']['status']=='PASS'
assert bench['same_tool_with_final_pitch_loops']['status']=='BLOCKED'
assert not bench['main_applied'] and bench['whole_harness']=='BLOCKED'
selected=next(r for r in screen['trials'] if r['rear_centreline_y_mm']==-6.5)
assert selected['strap_components']==1 and selected['strap_volume_mm3']>90
assert abs(selected['strap_volume_mm3']-selected['analytic_strap_volume_mm3'])<.02
for row in receipt['sources']:
    if 'file' in row:assert sha(OUT/'sources'/row['file'])==row['sha256']
for row in render['images']:assert sha(OUT/row['file'])==row['sha256']
assert sha(OUT/'review.blend')==render['review_sha256']
servo_gap=min(r['continuous_gap_lower_bound_mm'] for r in bench['servo_with_preplaced_tie']['segment_clearances'])
tool_gap=bench['cutter_approach']['clearance_to_bench']['gap_mm']
detail=('已下载三份T18R官方尺寸图，补查有方向的扣头、非空带身和剪尾工具包络。'
        '模型中先预放扎带再装俯仰舵机可行；舵机装好后直接从下套闭环会碰撞。'
        '扎带柔性穿紧、全部固定点、整束安装、其余头部线/FPC和最终下料长度仍未完成。'
        '仅独立候选，主模型保持M1.47。')

md=f'''# CAM 扎带：官方图纸和台面操作空间

**来源和局部几何检查已更新；完整线束仍为 BLOCKED，主模型没有采用候选。**

## 公开资料已补到哪里

已取得三份 HellermannTyton T18R 官方 PDF，逐页看过并记录版本和 SHA256。
原来的直接下载403记录保留；本次通过产品页公开下载链接取得文件。

| 图纸 | 版本 | 日期 | 性质 |
|---|---|---|---|
| [CSC](sources/CAD_10-0585-001-CSC.pdf) | 10.1 | 2025-12-05 | 官方尺寸图 |
| [CSH](sources/CAD_10-0585-001-CSH.pdf) | 01.3 | 2019-11-27 | 官方尺寸图 |
| [CSE](sources/CAD_10-0585-003-CSE.pdf) | 01 | 2008-11-28 | 标有UNCONTROLLED DRAWING，仅作历史对照 |

各图的厚度和扣头公差有差异。当前空间筛查按带宽2.7、厚1.3、扣头长5.3×高4.3×宽5.0mm覆盖所查图纸上界，采购地区/版本尚未冻结。这些尺寸不代表实测。

图中带身从扣头侧面连出，回程带身穿过扣头。内部穿带孔中心、棘爪和安装弯曲形状没有完整标注；暂按图示比例分配孔轴，仍是ASSUMED。碰撞计算保留完整扣头盒，不用一个假孔制造间隙。

![方向和空间](tie_orientation.png)

黄色为带身/扣头空间分配，不是精准成品CAD，也不是新增打印件。四色线为临时直段，起止Z229.9–274.9mm，线色不代表针脚。图中只显示台面子装配。

JST SH/PH胶壳、端子与适用线径资料已经取得；当前舵盘、CAM/FPC、WeAct等具体缺项见[公开资料补查](../../supplier_made_harness/recheck_20261004/README.md)。MORI分支、固定点和最终长度仍需我们完成设计，公开目录不能替代项目加工图。

## 这次核对出的顺序

1. 俯仰舵机未装时先预放扎带。对独立Pitch_Yoke作闭环从下向上的121个位置采样，未检出碰撞。这不是柔性穿带或收紧的证明。
2. 再按已有分步路径装入俯仰舵机。加入实际非空带身/扣头及四根局部直段后，1066个位置检查通过；相对于这些新增障碍的连续平移间隙下界至少{servo_gap:.2f}mm。原框架/轴承的检查仍由前一阶段记录负责。
3. 剪尾时保留前方工具入口，先不形成最终俯仰线环；图示临时直段放在工具后方。既定线环形成后会与这套工具包络相交。

这里是可继续细化的安装顺序，没有证明实际扎带可以按此形状穿紧，也未包含真实舵机尾线、完整CAM线束暂存和手部操作。

![工具局部](tool_detail.png)

绿色线框是计算使用的实体工具包络边缘。参考KNIPEX79 22 125目录长125×宽60×厚19mm及钳头A11/B10/D6.5mm，额外留了开口余量；它是ASSUMED工具空间，不是厂家CAD或采购选型。工具从上方直线接近60mm的连续扫掠与台面子装配名义间距{tool_gap:.2f}mm，与临时线段1.56mm。手指、剪切力、真实铰链及钳口运动未验证。

![完整工具包络](tool_overview.png)

不能把这几项局部通过合并成“扎带安装完成”。尤其不能沿用“先装舵机、再从下套闭环”的直观做法：该路线121个位置中93处与Pitch_Servo相交。

![错误顺序的碰撞](ring_below.png)

## 检查边界

| 项目 | 当前结果 |
|---|---|
| 带身非空且连续 | PASS，单实体，体积{selected['strap_volume_mm3']:.5f}mm³，与解析截面×弧长差小于0.02mm³ |
| 有方向的扎带与源件 | PASS，每种后侧位置2653次相对位置；有限Yaw/Pitch样本 |
| 既有CAM线路 | PASS，44条路线和4个夹持直段；不等于压紧后绝缘不受损 |
| 舵机装好后从下套闭环 | BLOCKED，93个碰撞位置 |
| 先预放，再装舵机 | 局部刚性包络PASS；柔性穿带/尾线暂存NOT_TESTED |
| 剪尾工具与自由尾端空间 | 局部包络PASS；手部、钳口运动与实际切断NOT_TESTED |
| 既定最终线环与同一工具 | BLOCKED，四条线均有相交样本，要求先剪尾后整理线环 |
| 其余固定点、整束安装、七根其他头部导线/FPC | NOT_TESTED；完整线束仍BLOCKED |
| 最终下料长度、供应商加工放行 | BLOCKED |

本轮不改打印件和正式CAD。已形成的带身长度约{selected['strap_centreline_length_to_head_exit_mm']:.2f}mm仅用于空间分配，不是扎带或线束下料尺寸。T18R80N是环拉断指标，不能当作对细导线的安装拉紧力。

首轮脚本因多边形方向错误输出空带身，检查被作废并保存在[无效记录](invalid_empty_band/README.md)。已修正方向，增加非空/单体/体积核对后，全部重跑；正文仅引用新报告，保留原始失败用于追溯。

## 来源与复查

- [扎带官方产品页](https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01712)、[钳子官方尺寸](https://www.knipex.com/en-uk/products/electronics-pliers/precision-electronics-diagonal-cutters-with-bolted-joint/precision-electronics-diagonal-cutters-bolted-joint/7922125)。
- [下载回执](sources/receipt.json)、[逐项尺寸/假设](sources/dimensions.json)、[有方向的实体检查](oriented_tie_screen.json)、[台面顺序和工具](bench_access.json)。
- [独立Blender](review.blend)、[图像清单](render_manifest.json)、[复现命令](commands.json)、[交付清单](review_manifest.json)。
- [前一阶段压线座](../cam_anchors/index.html)。上一阶段的无扎带舵机路径仍保留；安装扎带时以本页追加的先后约束为准。

所有装配仍为PROTOTYPE / UNVALIDATED；打印强度、PA12蠕变、实际抓持、绝缘压伤与弯折寿命没有资格结论。
'''
(OUT/'README.md').write_text(md)
fig=lambda file,label:f'<figure><a href="{file}.png"><img src="{file}.png" alt="{escape(label)}"></a><figcaption>{escape(label)}</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · 扎带图纸与安装顺序</title>
<style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1080px;margin:32px auto;padding:0 24px 60px;background:#f3f6f5;color:#263d3d}a{color:#086f78}h1{font-size:30px}h2{margin-top:32px}.note{background:#fff0d9;padding:18px;border-radius:8px}.done{background:#e0efe8;padding:18px;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #c9d9d4;vertical-align:top}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前剩余项目</a></p>
<h1>图纸已补到，安装顺序也要对上</h1>
<p class="done">三份T18R官方尺寸图已取得。补查了带身与扣头的方向、局部装入和剪尾工具空间；支持“先预放扎带，再装俯仰舵机”继续细化。</p>
<p class="note">独立候选，主模型仍为M1.47。柔性穿紧、全部固定点、整束装入和最终线长尚未完成，完整线束仍BLOCKED。</p>
<h2>公开资料</h2><p>扎带图纸：<a href="sources/CAD_10-0585-001-CSC.pdf">CSC · 2025版</a>、<a href="sources/CAD_10-0585-001-CSH.pdf">CSH · 2019版</a>、<a href="sources/CAD_10-0585-003-CSE.pdf">CSE · 2008非受控对照</a>。采购版本未冻结，带身/扣头内部安装形态仍有假设。<a href="sources/dimensions.json">逐项尺寸及证据等级</a>。</p>
<p>JST连接器和端子的目录已经取得。舵盘、相机完整排线等仍缺的字段列在<a href="../../supplier_made_harness/recheck_20261004/README.md">公开资料补查</a>；项目分支、固定点和长度由我们继续设计。</p>
<h2>扣头方向与局部操作</h2><div class="grid">'''+fig('tie_orientation','黄色是外购扎带空间分配；四色只是临时直段，不定义针脚')+fig('tool_detail','绿色线框为实体工具包络的边缘；不是厂家钳子CAD')+f'''</div>
<p>带宽按2.7mm、厚1.3mm、扣头按5.3×4.3×5.0mm分配。未标的扣头孔轴和弯曲形态注明ASSUMED。工具参考79 22 125的厂家尺寸，包含开口余量；图中省略尚未安装的Yaw舵机、俯仰头框、CAM和外壳。</p>
<h2>安装先后不能反过来</h2><ol><li>在裸Pitch_Yoke上预放扎带；已做121个刚性位置检查，柔性穿入仍待完成。</li><li>按已有分步路线装俯仰舵机；加入新扎带和局部直线后，1066个位置检查通过，相对这些新增障碍的平移间隙下界≥{servo_gap:.2f}mm。</li><li>先保留工具入口，剪尾后再整理最终俯仰线环。手部、真实钳口运动和实际线束暂存未验证。</li></ol>
<div class="grid">'''+fig('ring_below','错误顺序：舵机已装时，闭环从下面套入会相交')+fig('tool_overview','台面子装配上的完整工具包络；前方及上方必须保持开放')+f'''</div>
<table><tr><th>检查</th><th>结果与范围</th></tr><tr><td>带身实体</td><td>非空单体，{selected['strap_volume_mm3']:.2f}mm³；解析体积校核通过</td></tr><tr><td>有方向扎带 / 既有线路</td><td>2653次相对位置，44条路线和4个局部直段通过；有限姿态</td></tr><tr><td>剪尾空间</td><td>工具从上接近60mm的包络通过，台面子装配间隙{tool_gap:.2f}mm</td></tr><tr><td>既定最终线环与工具</td><td>有碰撞，要求先剪尾后整理线环；不代表所有工具/方向均不可用</td></tr><tr><td>柔性穿紧、其余固定与整束装入</td><td>NOT_TESTED；没有把局部通过算成完整安装通过</td></tr></table>
<p class="note">没有发布下料长度或安装拉紧力。80N是产品环拉断指标；压伤、拉脱、PA12蠕变、疲劳与打印强度均未验证。</p>
<details><summary>计算修正记录</summary><p>首轮带身多边形方向错误，输出空实体；原报告已作废。修正后加入非空/单体/解析体积检查，再完整重跑。<a href="invalid_empty_band/README.md">无效记录</a>。</p></details>
<p><a href="README.md">完整说明</a> · <a href="review.blend">独立Blender</a> · <a href="oriented_tie_screen.json">带身检查</a> · <a href="bench_access.json">安装与工具检查</a> · <a href="sources/receipt.json">来源回执</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">交付清单</a> · <a href="../cam_anchors/index.html">前一阶段压线座</a></p></html>'''
(OUT/'index.html').write_text(html)

status_path=PARENT/'work_status.json';status=read(status_path)
row=next(r for r in status['remaining'] if r['id']=='harness');old_detail=row['detail']
row.update(detail=detail,evidence='harness_A8/cam_tie_install/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_tie_install/index.html',
    CAM_tie_catalogue_receipt='PASS',CAM_tie_oriented_allocation='PASS',CAM_tie_bench_working_volumes='PASS',
    CAM_tie_bench_scope='Preplaced closed-ring allocation plus incremental servo and cutter checks only',
    CAM_tie_full_installation='NOT_TESTED',CAM_tie_review='harness_A8/cam_tie_install/index.html',
    CAM_tie_main_applied=False)
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';text=p.read_text();assert old_detail in text
text=text.replace(old_detail,detail).replace('harness_A8/cam_anchors/index.html','harness_A8/cam_tie_install/index.html')
text=text.replace('最新：CAM四线压线座候选','最新：CAM扎带资料与安装顺序')
p.write_text(text)
for p,link in [(A8/'index.html','cam_tie_install/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_tie_install/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_tie_install/index.html')]:
    text=p.read_text()
    if p==A8/'index.html':
        pattern=r'<section id="threading-update">.*?</section>'
        block=f'<section id="threading-update"><h2>最新：CAM扎带资料与安装顺序</h2><p>{detail}</p><p><a href="{link}">官方尺寸图、局部顺序与剩余项</a>；下方保留历史阶段。</p></section>'
    else:
        start='<!-- A8_PITCH_FLEX_UPDATE -->';end='<!-- /A8_PITCH_FLEX_UPDATE -->'
        pattern=re.escape(start)+'.*?'+re.escape(end)
        block=f'{start}<section><h2>CAM扎带资料与安装顺序</h2><p>{detail}</p><p><a href="{link}">来源和局部检查</a></p></section>{end}'
    text,n=re.subn(pattern,block,text,flags=re.S);assert n==1;p.write_text(text)
p=A8/'README.md';text=p.read_text()
text,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->',
    '<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM扎带图纸与安装顺序](cam_tie_install/index.html)：三份官方图纸和局部台面操作检查已补。柔性穿紧和整束安装未完成，主模型未采用。\n<!-- /A8_PITCH_FLEX_LATEST -->',text,flags=re.S)
assert n==1;p.write_text(text)

base='mechanical/studies/prearrival_finish/harness_A8/'
blender='/Applications/Blender.app/Contents/MacOS/Blender -b '
suffix=' -t 4 --python-exit-code 1 --python '+base
commands={'cwd':str(ROOT),'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','CAD_Python':'3.12.14'},
 'commands':[blender+'mechanical/mori_v1_2.blend'+suffix+'screen_CAM_tie_installation.py',
             blender+'mechanical/mori_v1_2.blend'+suffix+'check_CAM_tie_bench_access.py',
             blender+base+'cam_anchors/candidate_v3/cleaned/candidate.blend'+suffix+'render_CAM_tie_installation.py',
             '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'publish_CAM_tie_installation.py',
             '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'verify_delivery.py'],
 'notes':['Initial empty-band reports invalidated before publication; signed winding fixed; actual solid and assembly checks rerun.',
          'Render shows cutter solid edges and removes hidden internal head/strap overlap only to prevent coincident display faces.',
          'Published data are source receipts and bounded nominal checks; main/hardware/config unchanged.']}
(OUT/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[OUT/x for x in ['README.md','index.html','commands.json','render_manifest.json','review.blend',
       'oriented_tie_screen.json','bench_access.json','sources/receipt.json','sources/dimensions.json']]
files += [OUT/'sources'/r['file'] for r in receipt['sources'] if 'file' in r]
files += [OUT/r['file'] for r in render['images']]
files += sorted(OUT.glob('*.npz'))
manifest={'status':'PASS','scope':'Verified source receipt and bounded rigid bench allocation, not full tie installation',
 'script_sha256':sha(SCRIPT),'source_main_sha256':screen['source_main_sha256'],
 'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_TIE_INSTALL_PUBLISHED',len(files),'files',flush=True)
