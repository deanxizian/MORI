"""Publish the CAM-side bundle result without claiming complete connectivity."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
PUB_SCRIPT=Path(__file__).resolve();HERE=PUB_SCRIPT.parent;OUT=HERE/'cam_parallel_pitch';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tail=read(OUT/'shifted_tail_screen.json');tail_math=read(OUT/'tail_math_bounds.json')
loops=read(OUT/'following_arc/screen.json');packing=read(OUT/'following_arc/packing.json');loop_math=read(OUT/'following_arc/math_bounds.json')
render=read(OUT/'render_manifest.json')
assert all(d['status']=='PASS' for d in [tail,tail_math,loops,packing,loop_math,render])
assert sha(ROOT/'mechanical/mori_v1_2.blend')==loops['source_main_sha256']
first=packing['rows'][0];assert first['status']=='PASS'
gap=first['minimum_mutual_gap_bound_mm'];prefix_gap=first['minimum_prefix_gap_bound_mm']
partial=loops['selected'][0]['exact_length_mm']+tail_math['length_lower_mm']
detail=('CAM端改为四根共同排布的俯仰线环和缓慢侧移出线，3组候选均通过130个组合姿态的源实体检查；'
        '相机端四线整体的自交、相互间隙及原身体线段共存检查通过，最小线间隙下界约0.306mm。'
        '线环在整个俯仰范围的长度、半径及正直段已有解析界；碰撞仍是姿态采样。'
        '颈部原出线点到这组线环的过渡段、真实固定、整束装入及其余头部线路仍需设计。实际CAM插合件未定；主模型未改，不能下发最终线长。')
md=f'''# CAM 端四线俯仰线环

**本次完成 CAM 端局部成组路线。完整线束仍为 BLOCKED，主模型保持 M1.47。**

之前把四根线分别优化，会在抬头时互相靠近。当前候选让四根活动线位于间距1mm的平行平面；前侧线段随俯仰变化，上方半圆的高度补偿长度变化。相机插头后先保留5mm直段，再缓慢侧移到两只舵机之间。

| 检查对象 | 结果与范围 |
|---|---|
| 源实体、29个既有插头分配及14根静态线 | 3组候选各130个 yaw/pitch 组合姿态 PASS；使用未采用的J3M局部打印候选 |
| 每根 CAM 端线自身及四根线相互间隔 | PASS；最小表面间隙下界 {gap:.6f} mm，要求0.3mm |
| 与原身体侧四条线段共存 | PASS；每组2080个组合，间隙下界至少 {prefix_gap:.3f} mm；两端还没有连接 |
| 俯仰线环长度、圆弧半径、直段长度 | 整个−20°至+25°范围解析检查 PASS；活动段半径不小于7.5mm |
| 相机端侧移曲率 | 整段下界 {tail_math['minimum_curvature_radius_lower_bound_mm']:.4f} mm，筛查值6.9342mm |
| 连续角度碰撞、真实导线自然形状、弯折寿命 | NOT_TESTED；解析长度证明不代替这些检查 |

## 三个姿态

![零位，CAM端局部线环](zero.png)
![低头20度](down20.png)
![抬头25度](up25.png)

图片选择性显示CAM、两只舵机、俯仰座和显示支架，其余零件为看清路线暂时隐藏，实体检查仍包括它们。四色表示几何槽位，不能当作供应商颜色或针腔定义。线环下端为**临时接续基准**，未建夹持座，也未连接颈部原线段。

[独立可编辑 Blender 副本](comparison.blend)。没有修改正式模型、STL、动画、PCB或针序。

## 仍需在下图前完成

1. 把颈部原四个出线点接到新的线环基准，并一起检查线间距离与完整拆装顺序。
2. 设计真实固定和应力释放；涉及打印结构变化时，按既定要求先展示具体候选再确认。
3. 纳入其余七根头部活动导线、相机FPC及其插拔空间，检查照片位置误差。
4. 确定实际CAM插合料号、针腔视图和供应商采用的压接组合，再给整根下料长度与公差。

候选0的CAM端局部中心线长约{partial:.2f}mm，仅从临时接续点到插头出线面。它不含身体线路、尚缺的过渡段或端子加工余量，**不是下料长度**。6.9342mm是参考线材数据形成的当前筛查值，不是动态寿命保证。

## 来源与保留记录

- [CAM板端照片复核及JST目录资料](../cam_pitch_flex/index.html)：板端照片映射已复核，实际针腔插合视图仍未确认。
- [固定出线](shifted_tail_screen.json)、[固定出线整段数学界](tail_math_bounds.json)、[线环源实体检查](following_arc/screen.json)、[整束检查](following_arc/packing.json)、[全俯仰区间数学界](following_arc/math_bounds.json)。
- [旧单独线环未通过的整束](../cam_pitch_flex/side/packing.json)、[本轮直下弯失败](tail_screen.json)、[固定前侧位置失败](arc_service/screen.json)保留；失败的有限路径族不能说明所有路线都无解。
- [命令](commands.json)、[图像来源](render_manifest.json)、[本次交付来源](review_manifest.json)。所有模型仍是 PROTOTYPE / UNVALIDATED。
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM端四线俯仰线环</title>
<style>body{{font:16px/1.75 system-ui,-apple-system,"PingFang SC",sans-serif;background:#f3f6f5;color:#283e43;max-width:1120px;margin:28px auto;padding:0 24px 60px}}a{{color:#086f78}}.note{{background:#fff0d9;padding:18px 22px;border-radius:8px}}.ok{{background:#e4f2eb;padding:18px 22px;border-radius:8px}}.images{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}figure{{margin:0}}img{{width:100%;border-radius:8px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:11px;border-bottom:1px solid #cdd9d7;text-align:left}}@media(max-width:760px){{.images{{grid-template-columns:1fr}}}}</style>
<p><a href="../index.html">← A8研究</a> · <a href="../../index.html">全部剩余项目</a></p><h1>CAM端四线俯仰线环</h1>
<p class="ok">CAM端四根线已经共同通过本轮名义几何检查，解决了此前单线分别优化后相互靠近的问题。</p>
<p class="note">完整线束仍为BLOCKED。线环下端还没有接到颈部线路，也没有真实夹持座。主模型、STL和装配动画未改；本页不能作为供应商加工图。</p>
<p>四根线在平行平面内共同弯曲，前侧随俯仰变化，上方半圆调整高度以保持同一长度。相机插头后保留5mm直段，再缓慢侧移进入舵机间隙。</p>
<div class="images">''' + ''.join(f'<figure><a href="{file}.png"><img src="{file}.png" alt="{title}，CAM端局部线环"></a><figcaption>{title}；点击看原图</figcaption></figure>' for file,title in [('zero','零位'),('down20','低头20°'),('up25','抬头25°')])+f'''</div>
<p>图中隐藏部分零件以显示线路；检查包含它们。四色为几何槽位，非供应商针腔或线色定义。线环下端是临时接续基准，尚未连接或固定。</p>
<table><tr><th>检查</th><th>结果</th></tr><tr><td>源实体与既有插头/静态线</td><td>3组候选各130个组合姿态PASS；J3M独立候选，未应用主模型</td></tr><tr><td>四线自身与相互间距</td><td>PASS，最小间隙下界{gap:.3f}mm</td></tr><tr><td>与原身体线段共存</td><td>PASS，最小间隙下界{prefix_gap:.2f}mm；尚未连接</td></tr><tr><td>整个俯仰区间的线长、半径、正直段</td><td>解析检查PASS；未证明连续碰撞或真实线材动态行为</td></tr><tr><td>过渡连接、固定、装入及完整线束</td><td>仍需设计，不能下发最终长度</td></tr></table>
<h2>下一步</h2><p>完成颈部到线环的过渡和实际固定，再纳入其余头部线路、FPC及装拆检查。CAM插合件与压接组合仍需确认。局部中心线约{partial:.2f}mm仅用于设计，不能直接下料。</p>
<p><a href="README.md">完整说明与边界</a> · <a href="comparison.blend">Blender检查副本</a> · <a href="following_arc/packing.json">四线整束检查</a> · <a href="following_arc/math_bounds.json">全角度长度/半径界</a> · <a href="tail_math_bounds.json">侧移段曲率</a> · <a href="../cam_pitch_flex/index.html">公开资料及此前结果</a> · <a href="commands.json">复现命令</a> · <a href="review_manifest.json">来源</a></p></html>'''
(OUT/'index.html').write_text(html)
status_path=PARENT/'work_status.json';status=read(status_path)
row=next(x for x in status['remaining'] if x['id']=='harness');old_detail=row['detail'];row.update(detail=detail,evidence='harness_A8/cam_parallel_pitch/index.html')
status['updated_utc']=datetime.now(timezone.utc).isoformat()
status['A8_harness_research'].update(latest_review='harness_A8/cam_parallel_pitch/index.html',
    CAM_parallel_pitch_fixed_tail='PASS',CAM_parallel_partial_bundle='PASS',CAM_parallel_analytic_length_radius='PASS',
    CAM_parallel_partial_gap_bound_mm=gap,CAM_parallel_fan_in='NOT_TESTED',CAM_parallel_anchors='NOT_TESTED',
    CAM_parallel_review='harness_A8/cam_parallel_pitch/index.html',CAM_route_applied=False)
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=PARENT/'index.html';text=p.read_text();assert old_detail in text
text=text.replace(old_detail,detail).replace('<a href="harness_A8/cam_pitch_flex/index.html">','<a href="harness_A8/cam_parallel_pitch/index.html">');p.write_text(text)
for p,link in [(HERE/'index.html','cam_parallel_pitch/index.html'),(PARENT/'head_harness/index.html','../harness_A8/cam_parallel_pitch/index.html'),(PARENT/'supplier_made_harness/index.html','../harness_A8/cam_parallel_pitch/index.html')]:
    text=p.read_text()
    if p==HERE/'index.html':
        block=f'<section id="threading-update"><h2>最新：CAM端四线共同排布通过</h2><p>{detail}</p><p><a href="{link}">查看三姿态图、检查和未完成连接</a>。下方保留历史阶段。</p></section>'
        text,n=re.subn(r'<section id="threading-update">.*?</section>',block,text,flags=re.S);assert n==1
        text=text.replace('<h2>最新：J1连续局部路线</h2>','<h2>历史阶段：J1连续局部路线</h2>')
    else:
        marker='<!-- A8_PITCH_FLEX_UPDATE -->';end='<!-- /A8_PITCH_FLEX_UPDATE -->'
        block=f'{marker}<section><h2>CAM端四线共同排布更新</h2><p>{detail}</p><p><a href="{link}">当前结果及未完成部分</a></p></section>{end}'
        text,n=re.subn(re.escape(marker)+'.*?'+re.escape(end),block,text,flags=re.S);assert n==1
    p.write_text(text)
p=HERE/'README.md';text=p.read_text()
text,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->',f'<!-- A8_PITCH_FLEX_LATEST -->\n最新见[CAM端四线俯仰线环](cam_parallel_pitch/index.html)：局部四线共同排布检查通过；颈部过渡、真实固定和整束装配仍需完成，主模型未替换。以下保留历史阶段。\n<!-- /A8_PITCH_FLEX_LATEST -->',text,flags=re.S);assert n==1;p.write_text(text)
commands={'cwd':str(ROOT),'versions':{'Blender':'5.2.2 LTS d13f752e3b9c','Python':'3.12.14'},
    'commands':[f'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/{name}.py' for name in ['screen_parallel_pitch_tails','screen_parallel_shifted_tails','plan_cam_following_arc','check_cam_parallel_bundle']]+[
        f'/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/harness_A8/{name}.py' for name in ['audit_parallel_tail_math','audit_cam_following_arc']],
    'render_command':'/Applications/Blender.app/Contents/MacOS/Blender -b mechanical/studies/prearrival_finish/harness_A8/assembly_feed_v3/open_mouth/cleaned/candidate.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/render_cam_parallel_review.py',
    'execution_notes':['The original R11 forward-tail failure and the X shift1.9mm failure are preserved in history directories.',
        'A7.2mm candidate passed but was superseded by a7.5mm recipe to increase curvature margin; both are preserved.',
        'High-anchor fixed-column search was stopped after repeated display-frame failures; its partial log is retained as incomplete.',
        'The subsequent lower-anchor fixed-column search completed with no accepted configuration; the following-column family passed.',
        'Only independent study outputs and status pages changed; no main geometry, hardware or production drawing changes.']}
(OUT/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[OUT/n for n in ['README.md','index.html','commands.json','shifted_tail_screen.json','shifted_tails.npz','tail_math_bounds.json',
    'following_arc/screen.json','following_arc/curves.npz','following_arc/packing.json','following_arc/math_bounds.json','render_manifest.json','zero.png','down20.png','up25.png','comparison.blend']]
manifest={'status':'PASS','scope':'Reviewed independent CAM-side bundle and source-backed publication only',
    'script_sha256':sha(PUB_SCRIPT),'source_main_sha256':loops['source_main_sha256'],'main_applied':False,
    'whole_harness':'BLOCKED','manufacturing_release':False,'images_visually_reviewed':True,
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('CAM_PARALLEL_REVIEW_PUBLISHED')
