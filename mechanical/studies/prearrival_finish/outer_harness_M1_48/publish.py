"""Publish this bounded study without changing the robot's geometry."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3];FINISH=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads((HERE/p).read_text())
packing=load('packing.json');verification=load('verification.json')
assert packing['status']==verification['status']=='PASS'
assert verification['source_main_sha256']==sha(PROJECT/'mechanical/mori_v1_2.blend')
options=[load(n) for n in ['outer_risers.json','outer_risers_R8.json','outer_risers_R10.json']]
assert all(r['status']=='BLOCKED' and not r['motion_survivors'] for r in options)
tested=sum(len(r['trials']) for r in options)
static=sum(r['zero_pose_passes'] for r in options)
gap=min(p['surface_gap_lower_bound_mm'] for p in packing['selected_pairs'])
now=datetime.now(timezone.utc).isoformat()

rows='\n'.join(f'| J5.{r["pin"]} | {r["azimuth_deg"]:g}° | {r["analytic_body_neck_length_mm"]:.2f} |' for r in packing['selected'])
readme=f'''# M1.48：身体 J5 至颈部的四线候选

**四根下部路线一起通过名义几何检查；完整线束仍为 BLOCKED。**
主模型保持 M1.48。这次没有改打印件、板卡、孔位、STL 或正式装配动画。

## 已完成的范围

直接读取当前主模型的 209 件实体，并加入 29 个对插包络和 14 根已有候选线。
未加载任何未采用的桥座或头座切槽。三条旧外侧通路在补入插头后不再满足间隙，
因此只调整线的下弯高度和一个方位，板卡及插头位置保持。

四根线现在从基板 Motion J5 的原针序起点连续接到颈部 Z168 mm 的暂定交接点。
线径仍为 0.6604 mm、名义表面间隙要求为 0.3 mm，最小解析弯曲半径为 7 mm。
四线 6 对之间的保守表面间隙下界最小为 {gap:.3f} mm；130 个头部姿态未检出间隙失败。
每条线的连续曲线间隙包含采样间距和解析圆弧弦误差，头部姿态本身仍是离散检查。

![四线与原模型的独立预览](body_routes.png)

| 身体端针脚 | 颈部暂定方位 | 本段中心线长度 / mm |
|---|---:|---:|
{rows}

这些是**未接完的路径长度，不是裁线长度**，未包含上方活动段、端子/剥线长度或制作余量。
方位分配只是机械走向，没有改变电气针序。图中色彩只用于区分路径。

![四根已连接的下部路径](routes_plan.png)

## 上方仍需设计活动段

简单内收再竖直向上的延长会穿入现有头座/反力连接区域，未采用。
另筛查 {tested} 条保持在颈部外侧的 S 弯上行路线，{static} 条在机械零位通过；
它们都未能覆盖所查头部姿态，分别受头座或前后壳阻挡。这只排除这些整段固定的
有限候选，不能推导为所有走线方法均不可行。后续应设计固定端至运动端的活动线环。

![原件剖面和未通过的直接延长](neck_connection.png)

## 仍未完成

- 偏航、俯仰活动段及它们与 CAM 插头的连续连接。
- 全部线的实际材料长度、扎线/应力释放、带线端子和胶壳装入顺序。
- 其余跨关节线和 FFC、完整带线装配及人手/工具操作。

29 个插头和压接出线仍含空间预留；14 根既有线也是候选，不能当成已经安装的实物。
没有发布供应商裁线图、采购或制造数据。已确认的相机上沿和 CAM 内六角螺钉仍保持 M1.48。

## 文件与核对

- [可编辑独立 Blender](review.blend)，橙色为这次四根候选，灰蓝色为已有候选线；隐藏的头部与外壳没有删除。
- [四线同时排布](packing.json) · [当前实体及 130 姿态](verification.json)
- [补入插头后的旧通路检查](neck_allocations.json) · [下端连接](body_prefix_pools.json)
- [直接延长失败](upper_entry.json) · [外侧 R7](outer_risers.json) / [R8](outer_risers_R8.json) / [R10](outer_risers_R10.json)
- [执行命令与哈希](publication.json) · [交付核对](delivery.json)

更新时间：{now}。
'''
(HERE/'README.md').write_text(readme)
table=''.join(f'<tr><td>J5.{r["pin"]}</td><td>{r["azimuth_deg"]:g}°</td><td>{r["analytic_body_neck_length_mm"]:.2f} mm</td></tr>' for r in packing['selected'])
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI M1.48 · 身体至颈部四线候选</title>
<style>body{{margin:0;background:#f1f5f3;color:#243c35;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif}}main{{max-width:1100px;margin:auto;padding:28px 22px 60px}}h1{{font-size:31px;line-height:1.3}}h2{{margin-top:32px}}a{{color:#14715d}}.note{{padding:16px 20px;background:#fff2d6;border:1px solid #d6b276}}figure{{margin:24px 0;background:white;border:1px solid #c5d3cd}}img{{display:block;width:100%}}figcaption{{padding:12px 16px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:12px;border-bottom:1px solid #cad7d1;text-align:left}}.links{{display:flex;gap:18px;flex-wrap:wrap}}details{{border:1px solid #c5d3cd;padding:14px 18px;margin-top:22px}}@media(max-width:650px){{main{{padding:20px 12px}}h1{{font-size:25px}}}}</style>
<main><nav><a href="../index.html">到货前复核</a> · <a href="../../../index.html?revision=V1.2-M1.48#camera-cam">主模型</a></nav>
<h1>身体端已接到颈部，头内活动段还未接完</h1>
<p class="note"><b>四根下部路线同时通过名义几何检查。</b> 完整线束与带线装配仍未完成，候选未应用主模型。本页没有增加孔、切槽或零件。</p>
<figure><img src="body_routes.png" alt="原桥座和电路板旁的四根橙色候选线，上方端点尚未连接"><figcaption>橙色：本次四根身体至颈部候选；灰蓝：14 根已有候选线。线径按模型原尺寸显示。头部和外壳在本视图中隐藏。</figcaption></figure>
<h2>这次完成了什么</h2><p>四根线保持 Motion J5 原针序，连接到颈部 Z168 mm。直接用当前主模型的 209 件实体，加上 29 个对插包络、14 根已有候选线重新检查，没有借用未采用的结构通道。</p>
<p>四线相互间隙的保守下界最小为 <b>{gap:.3f} mm</b>，满足本次 0.3 mm 名义要求；最小弯曲半径 7 mm，130 个头部姿态未检出间隙失败。对插与压接细节仍含估计，几何结果不等于实物合格。</p>
<figure><img src="routes_plan.png" alt="四根线路从原基板针脚到不同颈部交接点的俯视投影"><figcaption>空心圆是未连接的上端。图示颜色只区分路径。</figcaption></figure>
<table><thead><tr><th>身体端针脚</th><th>颈部方位</th><th>已绘制下部路径长度</th></tr></thead><tbody>{table}</tbody></table>
<p><b>表中不是裁线尺寸。</b> 上方活动段、端子、剥线长度及制作余量尚未纳入。</p>
<h2>下一处问题已定位</h2><p>直接向头内竖直延长会碰到头座/反力连接区域。另试的 {tested} 条外侧 S 弯中，有 {static} 条在零位能放下，但转头、低头后仍被头座或壳体挡住。这些上行部分需要按相对运动重新设计，不能沿用整段固定的路线。</p>
<figure><img src="neck_connection.png" alt="当前原件剖面：蓝色固定局部段通过，红色直接上行方案未通过"><figcaption>原打印件剖面与具体失败路线。没有据此认定必须切槽，也没有修改结构。</figcaption></figure>
<p>尚缺：上方偏航/俯仰活动线环、CAM 插头连接、其余跨关节线与 FFC、全长材料与固定，以及完整带线装配顺序。当前没有供应商制作图放行。</p>
<p class="links"><a href="review.blend">下载独立 Blender</a><a href="README.md">完整说明</a><a href="body_routes_top.png">原模型俯视图</a></p>
<details><summary>原始检查记录与执行证据</summary><p class="links"><a href="packing.json">四线同时排布</a><a href="verification.json">当前实体与姿态</a><a href="neck_allocations.json">对插包络复查</a><a href="upper_entry.json">直接延长</a><a href="outer_risers_R8.json">外侧绕行</a><a href="publication.json">命令与哈希</a><a href="delivery.json">交付检查</a></p></details>
</main></html>'''
(HERE/'index.html').write_text(html)

changed={}
for path,href in [(FINISH/'index.html','outer_harness_M1_48/index.html'),
                  (PROJECT/'mechanical/index.html','studies/prearrival_finish/outer_harness_M1_48/index.html'),
                  (FINISH/'neck_threading_M1_48/index.html','../outer_harness_M1_48/index.html')]:
    before=sha(path);text=path.read_text()
    block=f'<aside id="M1-48-outer-harness" class="notice"><b>四根身体至颈部候选已接通。</b> 补入对插包络后调整了下部线路，四线同时排布和130个头部姿态检查通过；上方活动段及完整装配仍未完成。<a href="{href}">查看当前原模型检查与独立预览</a>。</aside>'
    if 'id="M1-48-outer-harness"' in text:
        text=re.sub(r'<aside id="M1-48-outer-harness".*?</aside>',block,text,count=1,flags=re.S)
    else:
        assert '<main>' in text;text=text.replace('<main>','<main>'+block,1)
    path.write_text(text);changed[str(path.relative_to(PROJECT))]=dict(before=before,after=sha(path))

path=FINISH/'work_status.json';before=sha(path);w=json.loads(path.read_text())
w['updated_utc']=now
w['outer_harness_M1_48']=dict(status='PASS',scope='Four fixed body-root to neck curves only',
    evidence='outer_harness_M1_48/index.html',source_blend_sha256=verification['source_main_sha256'],
    native_parts=209,mating_allocations=29,existing_candidate_wires=14,
    head_poses=130,minimum_interwire_surface_gap_bound_mm=gap,
    upper_service_loop='NOT_TESTED',assembly='NOT_TESTED',whole_harness='BLOCKED',main_applied=False,
    fixed_upper_riser_candidates=tested,upper_riser_zero_passes=static,upper_riser_motion_survivors=0)
r=next(x for x in w['remaining'] if x['id']=='harness')
r['latest_current_native_evidence']='outer_harness_M1_48/index.html'
r['latest_current_native_detail']=f'直接读取M1.48原件：四根从基板J5到颈部Z168的已连接候选，加入29个插头包络和14根已有候选线后通过；四线间隙下界最小{gap:.3f}mm、130姿态通过。上部固定式绕行筛查未通过，活动线环和完整带线装配仍未完成。'
r['detail']='当前主模型下，四根CAM线已找到从Motion J5至颈部Z168的共同排布，未改打印件。该固定段通过252个零位目标和130头部姿态检查；上方偏航/俯仰活动段、完整材料长度与端子装入、固定、人手工具、其余跨关节线/FFC和整套装配仍待完成。历史采用切槽候选的头内/装配结果不能直接沿用到当前原件；旧来源声明已更正。完整线束与供应商裁线图仍BLOCKED，候选未应用。'
path.write_text(json.dumps(w,ensure_ascii=False,indent=2)+'\n')
changed[str(path.relative_to(PROJECT))]=dict(before=before,after=sha(path))

commands=[]
for script,log,args,factory in [
    ('check_neck_allocations.py','check_neck_allocations.log','',False),
    ('select_necks.py','select_necks.log','',False),
    ('plan_body_prefix.py','plan_body_prefix.log','',False),
    ('pack_body_prefix.py','pack_body_prefix.log','',True),
    ('verify_packed.py','verify_packed.log','',False),
    ('screen_upper_entry.py','screen_upper_entry.log','',False),
    ('screen_outer_risers.py','screen_outer_risers.log','',False),
    ('screen_outer_risers.py','screen_outer_risers_R8.log',' -- --radius 8',False),
    ('screen_outer_risers.py','screen_outer_risers_R10.log',' -- --radius 10',False),
    ('render_review.py','render_review.log','',False)]:
    contents=(HERE/log).read_text();assert 'Blender quit' in contents and 'Traceback' not in contents,log
    inputarg='--factory-startup' if factory else 'mechanical/mori_v1_2.blend'
    commands.append(dict(command=f'/Applications/Blender.app/Contents/MacOS/Blender -b {inputarg} --python-exit-code 1 --python {str((HERE/script).relative_to(PROJECT))}{args}',
                         cwd=str(PROJECT),exit_code=0,log=log,log_sha256=sha(HERE/log)))
commands.append(dict(command='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+str((HERE/'plot_review.py').relative_to(PROJECT)),cwd=str(PROJECT),exit_code=0))
pub=dict(status='PASS',scope='Bounded installed-route geometry and independent review, not a complete harness',utc=now,
    source_main_sha256=verification['source_main_sha256'],native_sources=verification['sources'],
    commands=commands,tools={'Blender':'5.2.2 LTS d13f752e3b9c','plot_runtime':'mori-cad Python 3.12.14'},
    changed_presentation_files=changed,
    files={p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['publication.json','delivery.json']},
    geometry_scope='No source geometry, part transforms, STL or main animation changed.',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    earlier_attempts=['Initial body pool failed on mating-envelope overlaps; final candidates adjusted wire bends only.',
                      'Initial renderer used a localized default shader node name; explicit nodes repaired the renderer. No main write.'],
    candidate_limits=['Mating/exit allocations are not measured parts.',
                      'Fourteen other wires remain independent candidates.',
                      'Finite head poses; no dynamic material, support or complete assembly proof.'])
(HERE/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n')
print('OUTER_HARNESS_PUBLISHED',gap,'upper_trial_count',tested,flush=True)
