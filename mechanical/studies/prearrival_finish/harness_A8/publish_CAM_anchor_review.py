"""Publish one checked anchor candidate without adopting it into main CAD."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3]
OUT=A8/'cam_anchors';C=OUT/'candidate_v3/cleaned'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
screen=read(C.parent/'screen.json');store=read(C/'storage_verification.json')
install=read(C/'servo_installation_replay.json');tool=read(C/'tool_replay.json')
render=read(OUT/'render_manifest.json')
assert all(x['status']=='PASS' for x in [screen,store,install,tool,render])
assert not screen['main_applied'] and not store['main_applied']
assert sha(ROOT/'mechanical/mori_v1_2.blend')==screen['source_main_sha256']
assert tool['sampled_span_deg']==240 and not tool['hits']
chosen=next(r for r in install['accepted'] if r['waypoints_mm'][2][1]==6.5)
offaxis=min(r['continuous_gap_lower_bound_mm'] for r in chosen['segment_clearances'][1:])
assert offaxis>.39
detail=('CAM四线新增一处并入Pitch_Yoke的压线座候选，配1根目录尺寸占位扎带，不增加打印件或螺钉。'
        '源实体/线形检查、舵机分步装入、工具转动采样及保存后网格检查已完成；'
        '其余固定点、扎带穿紧与整束装入、另外七根头部导线、FPC和真实插合件仍未完成。'
        '主模型保持M1.47，候选未采用，供应商下料长度仍不能发布。')

md=f'''# CAM 四线：一处压线座候选

**独立结构候选，主模型未采用。完整线束仍为 BLOCKED。**

这次补了俯仰线环靠近 Yaw 一侧的固定座。小横臂与 Pitch_Yoke 一体打印，端部四条浅槽定位导线，外侧用一根扎带压住。增加 0 个打印件、0 枚螺钉，提出 1 根外购扎带；颜色仅用于说明。

![压线座局部](anchor_detail.png)

青色为本次新增的压线座与横臂，灰色为原支架。黄色扎带及方块是保守尺寸占位：方块包住扣头各方向，**不是实际产品外形，也不是新增打印件**。线色只区分几何槽位。局部图隐藏其他支架、插头和外壳，避免遮挡；完整源实体仍参与相对姿态筛查。

| 检查 | 结果和范围 |
|---|---|
| 压线座与原支架连接 | 一个连续实体；梁截面4.5×3.0mm，根部较初稿扩大；未证明打印强度 |
| 压线座/扎带与源实体 | 每项2653次相对位置检查通过，覆盖13个Yaw与10个Pitch取值；有限姿态，不是连续碰撞证明 |
| 与四条已有线路 | 44条路线及4根夹持段实体扫掠检查通过；形状与前版相同 |
| 舵机装入 | 选择前移方案：按拆卸方向先+X6mm，再+Y6.5mm，再+X至35mm，最后上提；安装反向进行 |
| 舵机路径间隙 | 后三段存储实体的平移距离下界至少{offaxis:.3f}mm；起始定位面的接触单独保留，不宣称全程正间隙 |
| 螺钉操作 | L形内六角钥匙−120°到+120°共121个样本无碰撞，角度跨度240°；手部空间尚未验证 |
| 保存后实体 | 两个候选打印件均封闭、单体，无退化三角面；207个其他源件保持 |

## 舵机如何放进去

不能沿原路径一直横推，压线座会挡住上安装耳。候选采用下面的台面装配顺序：先安装俯仰舵机，随后再装Yaw舵机、俯仰头框及线束。图按拆卸方向排列，安装反向进行。

| 步骤 | 相对安装位的平移（mm） | 图 |
|---|---|---|
| 0 就位 | (0,0,0) | [查看](removal_0.png) |
| 1 退出轴承与安装座 | (+6,0,0) | [查看](removal_1.png) |
| 2 向前让开压线座 | (+6,+6.5,0) | [查看](removal_2.png) |
| 3 移到开口中央 | (+35,+6.5,0) | [查看](removal_3.png) |
| 4 向上取出 | (+35,+6.5,+65) | [查看](removal_4.png) |

这是刚性零件路径，不包括手、舵机真实尾线、扎带尾端的穿入与剪切工具。另一条下移3mm路线也没有名义碰撞，但间隙只有约0.05mm下界，因此不选用。原直线失败和各次修复记录均保留。

## 扎带依据

已取得[HellermannTyton T18R官方产品数据](https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01712)及两份官方图纸的网页提取数据：[CSC图](https://www.hellermanntyton.com/shared/assets/CAD_10-0585-001-CSC.pdf)、[CSH图](https://www.hellermanntyton.com/shared/assets/CAD_10-0585-001-CSH.pdf)。各地区版尺寸有差别，本候选按宽2.7mm、厚1.3mm、扣头5.3mm立方体上界预留；供应版次未冻结，安装状态为 ASSUMED。

直接下载返回403，记录在[下载回执](sources/receipt.json)。本轮使用的是官方网页工具读取的[逐项尺寸记录](sources/web_dimensions.json)，没有虚构已下载PDF的哈希，也没有把80N环拉断值当作扎紧力。

## 仍未完成

1. 其余固定点、应力释放和整体线束装入顺序；这一个压线座不能使整条路线自然保持设计形状。
2. 扎带穿入、尾端和剪切工具空间，以及压紧后对细导线的影响；不下发扎紧力。
3. 另外七根头部导线、CAM的实际互配件/针腔视图和完整相机FPC。
4. 供应商加工图中的最终端到端长度、公差、线材和压接组合；名义曲线长度不能直接下单。
5. 实物抓持、滑移、拉脱、PA12蠕变与弯折寿命。

供应商按图制作已确定；[之前的公开资料补查](../../supplier_made_harness/recheck_20261004/README.md)仍有效。公开目录中的尺寸与项目自己的布线/固定设计分开记录。

## 复查文件

- [独立Blender视图](review.blend)、[纯候选实体](candidate_v3/cleaned/candidate.blend)、[图像来源](render_manifest.json)。
- [局部实体与线形](candidate_v3/screen.json)、[保存后复核](candidate_v3/cleaned/storage_verification.json)、[舵机完整路径](candidate_v3/cleaned/servo_installation_replay.json)、[工具重放](candidate_v3/cleaned/tool_replay.json)。
- [复现命令](commands.json)、[本次来源清单](review_manifest.json)、[前一阶段四线连接结果](../cam_fan_in/index.html)。

原候选统计曾把121个角度样本乘2写成242°；新工具重放按端点差报告240°。网格修复采用1e-6mm合并，保存实体对目标布尔并集的双向顶点至表面最大偏差约0.000539mm，体积差约0.040mm³；这是数值检查，不是实物精度承诺。所有模型仍为 PROTOTYPE / UNVALIDATED。
'''
(OUT/'README.md').write_text(md)
fig=lambda f,label:f'<figure><a href="{f}.png"><img src="{f}.png" alt="{label}"></a><figcaption>{label} · 点击查看原图</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM压线座候选</title>
<style>body{font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#283e43;max-width:1120px;margin:28px auto;padding:0 24px 60px}a{color:#086f78}.note{background:#fff0d9;padding:18px 22px;border-radius:8px}.ok{background:#e4f2eb;padding:18px 22px;border-radius:8px}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.steps{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}figure{margin:0}img{width:100%;border-radius:8px}.detail{max-width:760px;margin:auto}table{border-collapse:collapse;width:100%}td,th{padding:11px;border-bottom:1px solid #cdd9d7;text-align:left}@media(max-width:760px){.images,.steps{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">全部剩余项目</a></p>
<h1>CAM四线：补一处压线座</h1><p class="ok">压线座并入原Pitch_Yoke，用一根扎带压住四根线；不增加打印件或螺钉。局部避让、舵机分步装入、工具与保存网格检查已完成。</p>
<p class="note">独立候选，尚未采用。这里只解决一个固定点；其余固定、整束装入与供应商最终加工长度仍未完成。主模型保持M1.47。</p>
<div class="detail">'''+fig('anchor_detail','青色为新增一体支臂和压线座；黄色为扎带尺寸占位')+'''</div>
<p>黄色大方块包住目录扣头各方向的尺寸，是空间预留，并非实际扎带外形或打印件。部分结构与插头在图中隐藏；四色只区分路线，不定义实际针脚或线色。</p>
<h2>头部姿态</h2><div class="images">'''+''.join(fig(f,l) for f,l in [('anchor_zero','零位'),('anchor_down20','低头20°'),('anchor_up25','抬头25°')])+'''</div>
<h2>台面拆装路径</h2><p>原来的直线推进会碰到上安装耳。先装俯仰舵机，后装Yaw舵机、俯仰头框和线束。下图按拆卸方向排列，安装时反向操作。</p><div class="steps">'''+''.join(fig(f'removal_{i}',l) for i,l in enumerate(['0 · 就位，先卸耳部紧固件','1 · 沿输出轴退出6mm','2 · 向前移6.5mm','3 · 移到中央，X位移共35mm','4 · 从上方取出']))+f'''</div>
<table><tr><th>检查</th><th>结果及限制</th></tr><tr><td>局部源实体 / 既有路线</td><td>PASS，2653次相对位置及44条路线、4根局部扫掠；姿态采样</td></tr><tr><td>舵机拆装路径</td><td>PASS，前移方案1066个位置样本；后三段平移间隙下界≥{offaxis:.3f}mm，起始接触另列</td></tr><tr><td>工具转动</td><td>PASS，−120°至+120°，跨度240°；手部空间未验证</td></tr><tr><td>保存后的模型</td><td>PASS，封闭单体、无退化面，207个其他源件保持</td></tr><tr><td>压紧、拉脱、线材寿命</td><td>NOT_TESTED，不能从几何无碰撞推断</td></tr></table>
<h2>还要继续做</h2><p>扎带的穿入、尾端与剪切工具空间；其余固定点和整束安装；另外七根头部导线、实际CAM插合件和相机FPC；最终线长、公差及供应商压接要求。</p>
<p>扎带参考来自<a href="https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01712">HellermannTyton T18R官方数据</a>。本候选覆盖不同地区图纸上界，仍未冻结采购版次。<a href="sources/web_dimensions.json">逐项尺寸与来源</a>。</p>
<p><a href="README.md">完整说明</a> · <a href="review.blend">Blender视图</a> · <a href="candidate_v3/cleaned/candidate.blend">候选实体</a> · <a href="candidate_v3/cleaned/servo_installation_replay.json">装入检查</a> · <a href="candidate_v3/cleaned/tool_replay.json">工具重放</a> · <a href="candidate_v3/cleaned/storage_verification.json">保存网格复核</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">来源清单</a></p></html>'''
(OUT/'index.html').write_text(html)

status_path=PARENT/'work_status.json';status=read(status_path)
row=next(r for r in status['remaining'] if r['id']=='harness');old_detail=row['detail']
row.update(detail=detail,evidence='harness_A8/cam_anchors/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_anchors/index.html',
    CAM_yaw_side_anchor_candidate='PASS',CAM_yaw_side_anchor_scope='One unapproved nominal support/tie allocation, servo service and stored mesh only',
    CAM_yaw_side_anchor_review='harness_A8/cam_anchors/index.html',CAM_yaw_side_anchor_applied=False,
    CAM_yaw_side_anchor_tie_installation='NOT_TESTED',CAM_all_anchors='NOT_TESTED',CAM_complete_harness_installation='NOT_TESTED')
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';text=p.read_text();assert old_detail in text
text=text.replace(old_detail,detail).replace('harness_A8/cam_fan_in/index.html','harness_A8/cam_anchors/index.html')
text=text.replace('最新：CAM接线端资料与两段线的衔接研究','最新：CAM四线压线座候选')
p.write_text(text)
for p,link in [(A8/'index.html','cam_anchors/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_anchors/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_anchors/index.html')]:
    text=p.read_text()
    if p==A8/'index.html':
        pattern=r'<section id="threading-update">.*?</section>'
        block=f'<section id="threading-update"><h2>最新：CAM四线压线座候选</h2><p>{detail}</p><p><a href="{link}">局部模型与拆装步骤</a>；下方保留历史阶段。</p></section>'
    else:
        start='<!-- A8_PITCH_FLEX_UPDATE -->';end='<!-- /A8_PITCH_FLEX_UPDATE -->'
        pattern=re.escape(start)+'.*?'+re.escape(end)
        block=f'{start}<section><h2>CAM四线压线座候选</h2><p>{detail}</p><p><a href="{link}">当前结果及剩余项目</a></p></section>{end}'
    text,n=re.subn(pattern,block,text,flags=re.S);assert n==1;p.write_text(text)
p=A8/'README.md';text=p.read_text()
text,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->',
    '<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM四线压线座候选](cam_anchors/index.html)：一处局部固定座、舵机拆装及网格检查完成。完整线束仍BLOCKED，主模型未采用。\n<!-- /A8_PITCH_FLEX_LATEST -->',text,flags=re.S)
assert n==1;p.write_text(text)

base='mechanical/studies/prearrival_finish/harness_A8/'
blender='/Applications/Blender.app/Contents/MacOS/Blender -b '
suffix=' -t 4 --python-exit-code 1 --python '+base
commands={'cwd':str(ROOT),'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','CAD_Python':'3.12.14'},
    'commands':[blender+'mechanical/mori_v1_2.blend'+suffix+'build_CAM_anchor_candidate_v3.py',
                blender+base+'cam_anchors/candidate_v3/candidate.blend'+suffix+'repair_CAM_anchor_storage.py',
                *[blender+'mechanical/mori_v1_2.blend'+suffix+s for s in ['verify_CAM_anchor_cleaned_storage.py','verify_CAM_anchor_cleaned_installation.py','verify_CAM_anchor_tool.py']],
                blender+base+'cam_anchors/candidate_v3/cleaned/candidate.blend'+suffix+'render_CAM_anchor_review.py',
                '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'publish_CAM_anchor_review.py',
                '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'verify_delivery.py'],
    'notes':['All new geometry is independent. Main/config/hardware are unchanged.',
             'V1 straight installation failed; V2 beam intersected tie; retain both failed candidates.',
             'Initial strict coincidence assertions failed on float mesh contacts; final records preserve exact small volumes and bounded surface comparison.',
             'Render was repeated to assign a separate neutral base material and hide the optical mast in inspection views. No geometry changed.',
             'The T18R direct downloads returned403; official web extraction is stored without claiming downloaded file hashes.']}
(OUT/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[OUT/'README.md',OUT/'index.html',OUT/'commands.json',OUT/'render_manifest.json',OUT/'review.blend',
       OUT/'sources/web_dimensions.json',OUT/'sources/receipt.json',C.parent/'screen.json',C/'candidate.blend',
       C/'repair.json',C/'storage_verification.json',C/'servo_installation_replay.json',C/'tool_replay.json']
files += [OUT/r['file'] for r in render['images']]
manifest={'status':'PASS','scope':'Independent one-anchor fit and service candidate; not full harness closure',
          'script_sha256':sha(SCRIPT),'source_main_sha256':screen['source_main_sha256'],
          'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'main_applied':False,
          'images_visually_reviewed':True,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_ANCHOR_PUBLISHED',len(files),'files',flush=True)
