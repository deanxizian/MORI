"""Publish J1 as a useful but incomplete independent design investigation."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,html
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[3];OUT=HERE/'joined_entry_candidate'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
route=read(HERE/'joined_entry_screen.json');solid=read(OUT/'screening.json')
spacing=read(HERE/'joined_wire_spacing.json');entry=read(OUT/'terminal_entry.json')
assert solid['status']=='PASS' and spacing['status']=='PASS' and entry['status']=='BLOCKED'
assert solid['source_route_sha256']==spacing['source_route_sha256']==sha(HERE/'joined_entry_screen.json')
assert solid['candidate_blend_sha256']==entry['source_candidate_sha256']==sha(OUT/'candidate.blend')
assert sha(ROOT/'mechanical/mori_v1_2.blend')==route['source_blend_sha256']
length=route['analytic_staging_length_mm']
review=f'''# J1：四根 UART 导线的连续进出候选

**主模型仍是 M1.47。J1 仅为独立副本，尚不建议应用，也不是供应商加工图。**

这次把下端、中央活动段和上端接成同一条路线。此前分开检查的段落没有被直接拼成“完整线束通过”。

![三个Yaw姿态](three_pose_paths.png)

## 本次已完成

- 四根线分别有完整、连续切线的局部路线：身体研究端点 → R8下弯 → 中央活动段 → R8上部S弯 → 随Yaw移动的研究端点。
- 保留原32 mm高活动段及其长度规律，整体下移3 mm至Z147–179；四根线的零位方位为45/135/225/315度。没有移动或缩放硬件。
- 每根局部中心线长度 **{length:.3f} mm**；13个Yaw姿态计算保持。最小抽样曲率半径 **{spacing['minimum_bend_mm']:.3f} mm**，大于候选线材目录参考加线半径的6.9342 mm筛查值。
- 在独立副本中仅修改 **Yaw_Base、Pitch_Yoke**，其余207个实体几何和位置保持。两件仍各为一个连通实体。相对原件只做减料，轴承、舵机和螺钉位置不动。
- 13个Yaw×10个Pitch姿态、四根线共520个“导线×姿态”，未检出局部曲线与209源实体/既有代理、14根固定线候选的间隙失败。四线相互表面间隙的全参数下界 **{spacing['minimum_interwire_surface_bound_mm']:.3f} mm**；另检查了抽样非局部自接近和两组外圈参考路线。

这是给定线形、离散姿态及名义尺寸的检查，不代表真实线束一定保持这个形状，也不代表动态疲劳、扭转或打印强度合格。

![两处打印件剖面](sections_review.png)

孔道刀具半径0.78 mm只是本次打印结构候选参数。Yaw_Base去除{solid['part_results']['Yaw_Base']['removed_volume_mm3']:.3f} mm³，Pitch_Yoke去除{solid['part_results']['Pitch_Yoke']['removed_volume_mm3']:.3f} mm³。距现有五金的间隙不等于剩余材料厚度；承压接触、开口边缘和疲劳仍未完成检查。

## 装入检查发现的实际问题

JST原厂SH目录第2页给出SSH-003T-P0.2-H名义示意尺寸3.9/1.35/0.8 mm，以及无凸耳SHR-04V-S胶壳5×5×2.8 mm。已保留来源、页码和哈希。这不是完整压接后端子公差图，也没有证明当前CAM板采用该厂牌/型号。

使用这两种**参考长方体包络**，在零位沿当前路线作切线随动穿入、分别尝试两种转向；四根路线共16项均出现包络与源实体重叠。因此不能把导线曲线检查直接当成插头/端子装入通过。

这只是16条具体穿入尝试失败：包络并非端子精确CAD，尚未检查任意姿态、临时拉直路径或分步拆装；也没有宣称所有装法都不可能。

接下来需要完成能够实际装入的方案，例如验证“一端预压端子、暂不装胶壳”的通道，或与关节装配顺序配合的开放放线结构。两者均尚未定型，不能先写成供应商必须执行的最终工艺。仍须补齐身体端固定、Yaw端固定、俯仰段、板端引出、完整分支和逐线长度。

**{length:.3f} mm是研究端点之间的局部长度，不能下料。** 当前仍无最终加工长度，未向任何供应商发送图纸或订单。

## 资料与结果

- [源模型局部路线检查](../joined_entry_screen.json)
- [两处候选改动及实体检查](screening.json)
- [线间、弯曲和长度检查](../joined_wire_spacing.json)
- [端子/胶壳装入尝试](terminal_entry.json)
- [JST原厂SH目录](../../../../../hardware/v1_2/head_harness_A8_20261003/sources/JST_SH_20261003.pdf)
- [独立候选Blender](candidate.blend)
- [压接资料与来源限制](../TOOLING_DETAILS.md)

实际CAM插座、匹配SCS0009舵盘/传动叠层仍有资料缺口；完整机械路线、固定与装入是项目尚未完成的设计，不能全部归为等资料或等实物。

复现工具：Blender5.2.2 LTS（d13f752e3b9c）、Python3.12.14。运行记录在[命令清单](commands.json)。主模型SHA256：`{route['source_blend_sha256']}`。
'''
(OUT/'README.md').write_text(review)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>J1 连续走线候选 · MORI M1.47</title><style>body{{font:16px/1.75 -apple-system,BlinkMacSystemFont,sans-serif;margin:40px auto;padding:0 24px;max-width:1080px;color:#263940;background:#f4f6f5}}h1{{font-size:30px}}h2{{margin-top:32px;font-size:23px}}img{{width:100%;background:white;border-radius:8px}}a{{color:#16617c}}.note{{border-left:4px solid #b68b3e;background:#fff8e9;padding:14px 18px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px 14px;border-bottom:1px solid #d4dedc;text-align:left}}code{{font-size:13px}}</style>
<p><a href="../index.html">← A8研究与官方资料</a></p><h1>四根UART导线：进出路线已接通，装入尚未完成</h1>
<p class="note">独立候选J1 · 主模型未修改 · 不是供应商加工图。需要先解决端子装入、固定、俯仰连接和整条长度。</p>
<img src="three_pose_paths.png" alt="相同端点和切线规则下，负60度、零位、正60度的四根局部导线路线">
<table><tr><th>检查</th><th>结果和范围</th></tr><tr><td>局部连续导线路线</td><td>PASS；四根线、130头部姿态、209源实体及14根固定线候选</td></tr>
<tr><td>弯曲与线间间隙</td><td>最小抽样弯曲半径{spacing['minimum_bend_mm']:.3f} mm；四线相互表面间隙下界{spacing['minimum_interwire_surface_bound_mm']:.3f} mm</td></tr>
<tr><td>打印件</td><td>只改Yaw_Base和Pitch_Yoke，207个其余实体保持；强度和开口边缘尚未验证</td></tr>
<tr><td>端子/胶壳装入</td><td>BLOCKED；16种名义参考包络切线随动尝试均有重叠，不等于所有装法无解</td></tr>
<tr><td>加工长度</td><td>BLOCKED；{length:.3f} mm只是局部研究长度</td></tr></table>
<h2>两处打印件需要局部让位</h2><img src="sections_review.png" alt="当前与J1候选的下端入口、上端出口真实实体剖面对比">
<h2>接下来必须完成的设计</h2><p>核对预压端子、暂不装胶壳的穿入办法，或与关节装配配合的开放放线方案；同时补齐固定、俯仰段和真实板端连接。现阶段不申请采用J1，以免只把未完成的装配问题带入主模型。</p>
<p>端子和胶壳采用JST目录名义包络，缺少压接后完整形状、公差及CAM实配型号。参考包络出现干涉不能直接解释为原厂端子绝对装不进去。</p>
<p><a href="README.md">完整说明</a> · <a href="candidate.blend">独立Blender</a> · <a href="screening.json">实体检查</a> · <a href="terminal_entry.json">装入尝试</a> · <a href="../joined_wire_spacing.json">线间检查</a> · <a href="../TOOLING_DETAILS.md">官方压接资料</a></p>
<p>主模型保持M1.47；没有采购、制造发布或硬件改动。</p></html>'''
(OUT/'index.html').write_text(page)
commands=[
    '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/check_joined_entry.py',
    '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/check_joined_wire_spacing.py',
    '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/build_joined_entry_candidate.py',
    '/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/check_terminal_entry.py',
    '/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/plot_joined_entry.py']
(OUT/'commands.json').write_text(json.dumps(dict(cwd=str(ROOT),commands=commands,source_blend_sha256=route['source_blend_sha256'],
    scope='J1 independent candidate only',known_failed_diagnostic='attempt_surface_filter/screening.json; corrected to retain cutter segments inside material'),ensure_ascii=False,indent=2)+'\n')

start='<!-- joined-entry:start -->';end='<!-- joined-entry:end -->'
block=f'''{start}
## 最新进展：连续局部候选J1

[J1路线与装配检查](joined_entry_candidate/index.html)已把四线下端、中央活动段和上端相接。独立副本中只改两件打印件，导线姿态/弯曲/相互间隙检查通过；端子参考包络沿线装入尚有干涉。主模型未改，也没有最终下料长度。以下原Z150–182及折线结果保留为历史研究，不应替代J1的最新范围说明。
{end}'''
p=HERE/'README.md';text=p.read_text()
if start in text:text=re.sub(re.escape(start)+'.*?'+re.escape(end),block,text,flags=re.S)
else:text=text.replace('## 新资料已接收',block+'\n\n## 新资料已接收')
text=text.replace('1. 依据出口复核，继续设计完整、可弯曲并可装入的进出路线；如需改变承重座/反力件，先做完整候选再交用户确认。',
                  '1. 完成J1端子装入、固定和俯仰连接，确认不会把局部通路误当成可装配线束；结构候选完整后再提交确认。')
p.write_text(text)
p=HERE/'index.html';text=p.read_text()
block='<section id="joined-entry"><h2>最新：J1连续局部路线</h2><p>四根线已将上下进出与中央活动段接通；独立副本修改两件打印件，导线姿态与间隙检查通过。端子参考包络装入仍未通过，完整固定、俯仰段和下料长度未完成。</p><p><a href="joined_entry_candidate/index.html">查看连续路线、剖面和装入问题</a>。以下原局部段和折线结果为此前研究，主模型未改。</p></section>'
if 'id="joined-entry"' in text:text=re.sub(r'<section id="joined-entry">.*?</section>',block,text,flags=re.S)
else:text=text.replace('<section id="endpoint-review">',block+'\n<section id="endpoint-review">')
p.write_text(text)
p=PARENT/'work_status.json';state=read(p)
detail='A8/J1把四根UART下端、中央与上端接成连续局部路线。独立副本仅改Yaw_Base和Pitch_Yoke，130姿态、线间及弯曲检查通过；端子/胶壳参考包络的16条装入尝试均有重叠，仍需设计可装入方案。真实固定、俯仰段、板端连接、逐线加工长度及完整相机FPC未完成。J1尚不建议应用，主模型未改。'
old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=detail,evidence='harness_A8/joined_entry_candidate/index.html')
state['A8_harness_research'].update(joined_entry_candidate='harness_A8/joined_entry_candidate/index.html',
    joined_local_route='PASS',joined_route_applied=False,joined_terminal_entry='BLOCKED',
    joined_route_physical_retention='NOT_TESTED',complete_UART_harness='BLOCKED')
state['updated_utc']=datetime.now(timezone.utc).isoformat();p.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';text=p.read_text().replace(old,detail)
block='<section id="harness-A8-update"><h2>A8/J1：连续路线与装入检查</h2><p><a href="harness_A8/joined_entry_candidate/index.html">四线已连接上下进出与中央段</a>；独立几何检查通过，端子装入、固定及完整连接仍未完成。主模型未改。</p></section>'
text=re.sub(r'<section id="harness-A8-update">.*?</section>',block,text,flags=re.S);p.write_text(text)
print('J1_REVIEW_PUBLISHED')
