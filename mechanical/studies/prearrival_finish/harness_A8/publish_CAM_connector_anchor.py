"""Publish the independently screened connector-side anchor; no main adoption."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;PARENT=A8.parent;ROOT=A8.parents[3]
OUT=A8/'cam_pitch_anchor';C=OUT/'connector_anchor'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
root=read(C/'root_v3_screen.json');bench=read(C/'assembly.json');render=read(C/'render_manifest.json')
assert root['status']==bench['status']==render['status']=='PASS'
assert root['source_main_sha256']==bench['source_main_sha256']==render['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assert bench['root_report_sha256']==render['root_report_sha256']==sha(C/'root_v3_screen.json')
assert bench['part_sha256']==sha(C/'Pitch_Cradle.npz')
assert render['outside_change_region_difference_mm3']<.05
assert bench['rows']['plug_after_board_from_below']['status']=='BLOCKED'
assert root['rows'][0]['wires']['routes_checked']==600
for row in render['images']:assert sha(C/row['file'])==row['sha256']
assert sha(C/'review.blend')==render['review_sha256']
detail='CAM插头附近新增独立固定座候选：并入现有头托，不增加打印件或螺钉，导线不移动；名义源件、600条相对线路检查及局部台面装入采样通过。须先插线再装CAM板。柔性穿紧、全部固定、其余7根头部导线/FPC和最终加工图仍未完成；主模型保持M1.47。'
md='''# CAM 插头附近的固定座候选

**局部候选已完成名义几何检查，尚未应用主模型。完整线束仍为 BLOCKED。**

供应商按图制作线束已经确定。标准资料继续由项目收集；MORI 的固定点、分支和长度基准需要由我们设计，不能把现有空间分配直接作为供应商下料图。

## 本次候选

在 CAM J11 的原有 5 mm 直线出线段旁设置短固定座，并入现有 Pitch_Cradle。使用一根 T18R 目录扎带空间分配，不增加打印件、螺钉或走线孔，不移动板卡、插头及已检查的四根导线。

![局部](connector_anchor/connector_detail.png)

青色为现有头托上增加的材料；黄色为扎带空间分配，并非完整供应商 CAD。四色导线只是几何槽位，不规定针脚或供货线色。局部图只显示 CAM 和离机头托，线段暂时保持竖直。

固定座用短连接接到后板，根部上表面连续倾斜，以增大与原板的连接截面。它替代了原先从显示支架延伸约 22 mm 到线环前端的尝试。这里仅确定应力释放位置，未证明 PA12 强度、抓持力或弯折寿命。

| 本轮检查 | 结果和边界 |
|---|---|
| 固定座与现有几何 | PASS，22590 次相对源件检查，包含 130 组头部姿态；最近名义间隙约 0.40 mm |
| 扎带本体空间 | PASS，近插头三个候选高度分别检查；当前选 Z212 mm；最近名义间隙约 0.60 mm |
| 既有导线 | PASS，600 条相对路线和 4 根局部直段；仅已完成的 CAM 四线和已有身体线路 |
| 连接实体 | 单一连续实体，和后板重合约 22.91 mm³；不是强度验证 |
| 保存到 Blender | 单一实体，其他 208 个物理对象保持；局部之外的几何差异受检查 |
| 完整线束、实际夹紧、柔性安装 | BLOCKED / NOT_TESTED，不能合并成整机安装通过 |

![整体位置](connector_anchor/connector_overview.png)

## 必须遵守的装配顺序

1. 在离机 CAM 板上先插入线束。
2. CAM 板连同插头、局部松弛导线一起装到离机头托。沿前后方向 20 mm 的 201 个位置采样通过；不包括完整线束尾端和手部。
3. 随后固定扎带、整理线环。闭环从下方预放的 121 个位置采样通过，但真实柔性穿带、扣合、拉紧和剪尾尚未完成验证。

**板卡装好以后，再把插头从下向上直接插入会碰到固定座。** 已保存该失败路径，不能把零件最终姿态不相交当作任意顺序都能装。

![绑扎前](connector_anchor/connector_before_tie.png)

![低头20度](connector_anchor/connector_down20.png)

这四根线的全部路线保持原样。插头到活动线环之间仍是预设柔性线形，不是有刚性导轨约束的形状。实际运动中的变形、张力和触碰仍需验证；本轮没有发布最终裁线长度。

## 保留的失败尝试

- [原显示支架延伸](support_screen.json)：低头时只有约 0.01 mm 的局部间隙，未采用。
- [整体侧移](warp_v1/screen.json)、[只调整前段侧移](warp_v2/screen.json)：会碰到相邻过渡导线，未采用。
- [沿前方直段夹持](clamp_positions/screen.json)、[从下方夹持](clamp_below/screen.json)：与舵机或颈部结构冲突，未采用。
- [初版短根部](connector_anchor/root_v2_screen.json)及[其局部装配记录](connector_anchor/assembly_before_taper.json)是中间计算记录；当前依据下列 V3 根部、重跑装配和保存记录。

## 公开资料与待补字段

[JST SH 官方目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)提供胶壳、端子、线径范围和压接工具资料；已下载的 [PH 目录](../../supplier_made_harness/recheck_20261004/JST_PH.pdf)与[逐型号压接资料](../TOOLING_DETAILS.md)继续保留。扎带依据[上一阶段取得的官方图纸](../cam_tie_install/index.html)。

尚缺的是具体采购版本的匹配信息：SCS0009 舵盘/有效啮合和轴向叠层、CAM 插头真实互配与针腔视图、OV3660 完整排线、WeAct 成品孔和排针插接数据。[逐项补查记录](../../supplier_made_harness/recheck_20261004/README.md)记录了已取得资料和未找到字段；不把目录候选称为实物配套。

当前没有联系供应商、下单或修改正式硬件。主模型、正式 STL 和装配动画均未采用本候选。

## 文件

[独立 Blender](connector_anchor/review.blend) · [V3 几何检查](connector_anchor/root_v3_screen.json) · [装配顺序检查](connector_anchor/assembly.json) · [存储及图像检查](connector_anchor/render_manifest.json) · [复现命令](commands.json) · [交付清单](review_manifest.json)
'''
(OUT/'README.md').write_text(md)
fig=lambda f,t:f'<figure><a href="connector_anchor/{f}.png"><img src="connector_anchor/{f}.png" alt="{t}"></a><figcaption>{t}</figcaption></figure>'
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM插头固定座候选</title>
<style>body{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#243b3c;max-width:1080px;margin:32px auto;padding:0 24px 60px}h1{font-size:30px}a{color:#08727b}.note{padding:18px;background:#fff0d9;border-radius:8px}.done{padding:18px;background:#dfede6;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccd8d4}table{width:100%;border-collapse:collapse}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">当前未完成项</a></p>
<h1>在CAM插头附近固定导线</h1><p class="done">短固定座并入现有头托；不增加打印件、螺钉或走线孔，保留所有原导线和硬件位置。局部名义几何检查通过。</p>
<p class="note">独立候选，主模型仍为M1.47。完整线束安装、实际夹紧和供应商加工图尚未完成；这些工作仍由项目继续处理。</p>
<div class="grid">'''+fig('connector_detail','青色：新增固定座；黄色：目录扎带空间；四色不代表针序')+fig('connector_before_tie','绑扎前的局部结构；板卡应先插线，再装到离机头托')+'''</div>
<h2>这次确定的装配限制</h2><p>先把插头插到CAM板上，再将板卡、插头和局部松弛导线一起装入头托，然后固定扎带。板卡装好以后从下方直插，会碰到固定座。</p>
<table><tr><th>检查</th><th>结果和范围</th></tr><tr><td>固定座与源件</td><td>22590次相对位置检查，最近名义间隙约0.40mm；有限头部姿态</td></tr><tr><td>导线</td><td>600条相对路线及4根局部直段通过；实际夹紧和绝缘压伤未验证</td></tr><tr><td>局部台面装入</td><td>预插CAM板201个位置，预放闭环121个位置通过；手部、完整尾线及柔性穿紧未验证</td></tr><tr><td>保存与范围</td><td>候选保持单实体，其他208个物理对象保留；主模型未应用</td></tr><tr><td>完整线束和加工图</td><td>BLOCKED：其余头部导线/FPC、完整固定和安装尚未完成</td></tr></table>
<div class="grid">'''+fig('connector_overview','原四线预设路线保留，固定座在CAM下方')+fig('connector_down20','低头20度的有限姿态；不代表实物线束的自由变形')+'''</div>
<h2>资料能找到，项目路线仍要设计</h2><p>JST连接器、端子和压接目录已经取得，T18R官方图纸也已归档。<a href="../../supplier_made_harness/recheck_20261004/README.md">逐项资料补查</a>列出仍缺的舵盘、真实互配、FPC和WeAct接口字段。供应商按图制作已确定，不再作为待用户决定项。</p>
<p>原来的长支架、局部侧移和前段夹持候选均因间隙或相交未采用。<a href="README.md">完整说明与失败记录</a>。保留这些记录，未覆盖主模型。</p>
<p><a href="connector_anchor/review.blend">独立Blender</a> · <a href="connector_anchor/root_v3_screen.json">几何检查</a> · <a href="connector_anchor/assembly.json">装入检查</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">交付清单</a></p></html>'''
(OUT/'index.html').write_text(html)
status_path=PARENT/'work_status.json';status=read(status_path)
row=next(r for r in status['remaining'] if r['id']=='harness');old_detail=row['detail'];row.update(detail=detail,evidence='harness_A8/cam_pitch_anchor/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_pitch_anchor/index.html',CAM_connector_anchor_candidate='PASS',
 CAM_connector_anchor_review='harness_A8/cam_pitch_anchor/index.html',CAM_connector_anchor_scope='Nominal integral short support, catalogue tie and bounded bench order; no complete installation',
 CAM_connector_anchor_applied=False,CAM_connector_anchor_full_installation='NOT_TESTED')
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';s=p.read_text();assert old_detail in s;s=s.replace(old_detail,detail).replace('harness_A8/cam_tie_install/index.html','harness_A8/cam_pitch_anchor/index.html').replace('最新：CAM扎带资料与安装顺序','最新：CAM插头固定座候选');p.write_text(s)
for p,link in [(A8/'index.html','cam_pitch_anchor/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_pitch_anchor/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_pitch_anchor/index.html')]:
    s=p.read_text()
    if p==A8/'index.html':pat=r'<section id="threading-update">.*?</section>';block=f'<section id="threading-update"><h2>最新：CAM插头固定座候选</h2><p>{detail}</p><p><a href="{link}">候选图与装配顺序</a>；下方保留历史阶段。</p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->';pat=re.escape(a)+'.*?'+re.escape(b);block=f'{a}<section><h2>CAM插头固定座候选</h2><p>{detail}</p><p><a href="{link}">候选图与局部检查</a></p></section>{b}'
    s,n=re.subn(pat,block,s,flags=re.S);assert n==1;p.write_text(s)
p=A8/'README.md';s=p.read_text();s,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->','<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM插头固定座候选](cam_pitch_anchor/index.html)：短固定座、局部路线和台面顺序已查；完整线束仍未完成，主模型未采用。\n<!-- /A8_PITCH_FLEX_LATEST -->',s,flags=re.S);assert n==1;p.write_text(s)
base='mechanical/studies/prearrival_finish/harness_A8/'
scripts=['screen_CAM_pitch_anchor','screen_CAM_pitch_anchor_warp','screen_CAM_pitch_anchor_warp_v2','screen_CAM_pitch_clamp_positions','screen_CAM_pitch_clamp_below','screen_CAM_connector_anchor','build_CAM_connector_anchor','build_CAM_connector_anchor_v2','build_CAM_connector_anchor_v3','check_CAM_connector_anchor_assembly']
cmds=['/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+base+x+'.py' for x in scripts]
cmds+=['/Applications/Blender.app/Contents/MacOS/Blender -b '+base+'cam_anchors/candidate_v3/cleaned/candidate.blend -t 4 --python-exit-code 1 --python '+base+'render_CAM_connector_anchor.py','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'publish_CAM_connector_anchor.py','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+base+'verify_delivery.py']
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':cmds,'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':'3.12.14'},'current_basis':'V3 root, assembly rerun after taper, final render; earlier attempts retained as history','main_applied':False},ensure_ascii=False,indent=2)+'\n')
files=[OUT/'README.md',OUT/'index.html',OUT/'commands.json']+[C/x for x in ['screen.json','root_v3_screen.json','assembly.json','render_manifest.json','Pitch_Cradle.npz','addition.npz','z212.0_head.npz','z212.0_band.npz','review.blend']]+[C/x['file'] for x in render['images']]
manifest={'status':'PASS','scope':'Local candidate and publication, not full harness release','script_sha256':sha(SCRIPT),'source_main_sha256':root['source_main_sha256'],
 'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_CONNECTOR_PUBLISHED',len(files),'files',flush=True)
