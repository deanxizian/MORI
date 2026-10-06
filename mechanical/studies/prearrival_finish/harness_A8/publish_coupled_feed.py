"""Publish the scoped J3 checks and remaining design defect, without adoption."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,html
HERE=Path(__file__).resolve().parent;OUT=HERE/'assembly_feed_v3';PARENT=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reload=read(OUT/'reloaded_verification.json');storage=read(OUT/'cleaned/storage.json')
relax=read(OUT/'relaxation_screen.json');wall=read(OUT/'journal_sections.json')
order=read(OUT/'local_wire_order.json');mouth=read(OUT/'upper_mouth_inspection.json')
for d in [reload,storage,relax,wall,order,mouth]:assert d['status']=='PASS'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==reload['source_blend_sha256']
assert storage['candidate_blend_sha256']==reload['source_candidate_sha256']==relax['source_candidate_sha256']==wall['source_cleaned_candidate_sha256']==sha(OUT/'cleaned/candidate.blend')
before=wall['wall_samples']['main'];after=wall['wall_samples']['J3']
old_area=min(r['area_mm2'] for r in before['section_properties_within_nominal_journal_cylinder'])
new_area=min(r['area_mm2'] for r in after['section_properties_within_nominal_journal_cylinder'])
scope_detail=('H06局部端子与随行软线的连续穿入包络、穿出后22个理线阶段、与另外3根已就位UART线的装入顺序检查通过；'
    'J3保存重载后的130个头部姿态也通过。两件打印候选仍未应用；头侧出口还留有薄边，完整固定、身体松散尾线操作、俯仰段/CAM和其余7根活动线未完成。主模型保持M1.47。')

md=f'''# J3：端子与尾线一起穿过偏航关节

**独立研究，整体线束仍为 BLOCKED。主模型、STL 和装配视频未更新；本页不是打印或线束加工放行。**

{scope_detail}

## 原厂资料与本次设计的关系

供应商按图制作已经由用户确认。已取得[JST SH官方目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)、[JST PH官方目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)、[AMASS XT30UPB官方产品资料](https://www.china-amass.net/xt30upb-m-product/)。本地来源、SHA256和限制见[A8接收记录](../receipt.json)、[端子工艺查询](../TOOLING_DETAILS.md)和[XT30互配尺寸](../amass_mating/README.md)。

SSH-003T-P0.2-H目录图的名义外形0.8×1.35×3.9mm用于穿装参考；这不是压接完成后的带公差CAD。Alpha2841/7的最大OD0.6604mm用于细线研究，未冻结订货后缀或声称动态寿命合格。压接查询还有来源版次限制，制线方仍需按具体线材、模具和适用文件确认。

## 这次补上的装配过程

J2只研究过裸端子自身的轨迹，不能替代带线穿装。J3让端子尾部沿导线中心线前进，刚性前端沿切线伸出3.9mm；软线始终接在端子后面。临时穿装半径位置为7.6mm，下、上转弯均为R8。只改变独立副本中的Yaw_Base、Pitch_Yoke，其余207个实体几何/位置保持。

![端子与尾线连续穿入截面](coupled_feed_sections.png)

名义穿线从下端R8弯前方3mm的暂存位置开始，不从PH胶壳开始；PH插头和身体端固定点尚未连接。穿出后，先径向移到6.8mm并调整上端高度，再引入中央角向松量。内部线长增加{relax['internal_length_growth_mm']:.2f}mm，由松散尾线补入；这不是整束装配松量或裁切长度。

| 检查 | 结果 | 严格范围 |
|---|---|---|
| 端子与随行线的连续扫掠 | PASS | 4个入口方向，207个未改源实体/代理、29个对插分配、14根静态线；两件候选实物网格另行回读检查 |
| 保存重载后原料空间检查 | PASS | 名义端子净空下界{reload['nominal_contact_gap_bound_mm']:.3f}mm，名义线净空下界{reload['nominal_tail_gap_bound_mm']:.3f}mm |
| 穿出后的线形调整 | PASS | 22个规定阶段×4根线，共88项；第一段径向/高度调整有连续包络，角向松量引入只有11个有限样本 |
| 局部逐根穿线顺序 | PASS | 12组有向组合；端子、尾线及第一段理线扫掠均避开另外3根已处于最终零位的UART线 |
| 已装形状的头部运动 | PASS | 130个Yaw/Pitch组合、520个线/姿态实例，使用保存重载后的J3实体；其他两组局部线环的既有检查仍只代表包络 |
| 两件网格保存与拓扑 | PASS | 均为单个连通闭合网格、无零面积三角面；数值整理后对实际保存实体再次检查所需通道 |
| 全部打印薄边与强度 | NOT_TESTED | 已发现并标出出口薄边；轴颈截面采样不能代替全件强度 |
| 整束装配、手和工具、固定、实际制线 | NOT_TESTED | 身体松散尾线、PH胶壳操作、7根其他活动线、完整俯仰段与CAM、FPC仍未完成 |

上表PASS只指名义几何。候选仍用未完全确认的插头分配，不代表实际端子、摩擦/插入力、磨损或线材弯折寿命已合格。

## 结构代价和未解决的薄边

![轴颈截面材料对比](journal_comparison.png)

轴颈名义外径19.9mm保持。在圆柱工作段16个截面、11520条径向射线中，最小壁厚样本从{before['minimum']['thickness_mm']:.3f}mm降到{after['minimum']['thickness_mm']:.3f}mm。另一个入口倒角截面的720条射线不适用于恒径圆柱壁厚指标，已明确列为NOT_APPLICABLE，而不是漏检或自动通过。

截面积采用全部17个截面（含入口倒角）、限制在名义轴颈圆柱内；最小样本{old_area:.3f}→{new_area:.3f}mm²，减少{100*(1-new_area/old_area):.2f}%。这是截面计算，不是承载/疲劳结论，也不是全件最小壁厚。

**头侧出口仍需清理：**在45°径向剖面，R13.50–13.777mm、Z190.166–191.00mm处有一片约0.277mm径向宽的薄边。它是J1运行线通道切出来、由J2/J3继承的材料，原主模型没有。偏离该剖面约±1mm后与主体相连，不是多出的独立零件，也不是法线显示问题。[来源与相邻剖面](upper_mouth_inspection.json)已保存。尚未盲目切除或宣称已经适合打印；需把通道出口整理成简单开口，并复核局部材料与功能面。

## 已处理的建模数值问题

早期构建把大量同向直线小段逐个并集，在Blender浮点存储后出现退化三角面。处理方式是把严格共线且方向相同的小段合并成单个端点凸包，再做原来的扫掠。没有放宽净空或网格验收门槛。旧失败结果保留在`history_initial_storage_fins/`；未加入理线微小包络时的失败结果保留在`history_feed_only/`。

## 可复查文件

- [独立可编辑Blender](cleaned/candidate.blend)：仅研究候选，未获应用确认。
- [连续穿装构建](candidate_screen.json)、[保存与回读](cleaned/storage.json)、[实际回读几何检查](reloaded_verification.json)。
- [理线阶段数据](relaxation_screen.json)、[逐根穿线顺序](local_wire_order.json)、[截面与功能件间隙](journal_sections.json)。
- [当前图像与报告来源清单](review_manifest.json)、[实际命令和复现命令](commands.json)。
- [身体端4线此前结果](../body_prefix_v2/index.html)、[完整项目状态](../../index.html)。

主模型SHA256：`{reload['source_blend_sha256']}`。硬件源文件只读。采购、制造、最终逐线加工图均未发布。
'''
(OUT/'README.md').write_text(md)

page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>J3 带线穿装 · MORI 独立研究</title>
<style>*{{box-sizing:border-box}}body{{font:16px/1.8 system-ui,-apple-system,sans-serif;max-width:1120px;margin:28px auto;padding:0 24px 50px;background:#f3f6f5;color:#2d4047}}a{{color:#087484}}h1{{font-size:30px;line-height:1.4}}h2{{font-size:23px;margin-top:30px}}img{{width:100%;height:auto;border-radius:8px}}.note{{background:#fff0d8;border-left:4px solid #bf7e23;padding:14px 18px}}.pass{{background:#e5f0e6;padding:14px 18px}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #cbd8d9;text-align:left;vertical-align:top}}code{{overflow-wrap:anywhere}}@media(max-width:650px){{body{{padding:0 14px}}th,td{{padding:7px;font-size:14px}}}}</style>
<p><a href="../index.html">← A8 原厂资料与线束研究</a> · <a href="../../index.html">完整工作状态</a></p>
<h1>端子与尾线一起穿过偏航关节</h1><p class="note">J3独立候选。主模型M1.47、STL与装配视频未改；头侧出口仍有待清理的薄边。完整线束为BLOCKED，这不是加工放行。</p>
<p class="pass">{scope_detail}</p>
<h2>资料已找到，逐线尺寸仍需由项目设计</h2><p>采用<a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST SH官方目录</a>的名义端子外形，结合已收到的<a href="../TOOLING_DETAILS.md">完整料号压接参考</a>与<a href="../amass_mating/index.html">AMASS插合图</a>。真实压接外形和公差仍未给齐；本地来源和限制均保留。</p>
<h2>穿入时软线始终接在端子后面</h2><img src="coupled_feed_sections.png" alt="实际源实体剖面，端子尾部连着R8软线穿过下端与上端，图中保留未清理的上端薄边">
<p>穿入使用R8弯曲，尾部中心经过半径7.6mm通道；随后移到装后的6.8mm位置。内部长度增加5.10mm，由未固定的尾线补入。下端从弯前3mm暂存位置开始，尚未包括PH胶壳操作。</p>
<table><tr><th>已验证范围</th><th>结果</th></tr><tr><td>4方向连续端子／随行线／第一次理线包络</td><td>PASS；对实际重载实体复核</td></tr><tr><td>名义端子／软线净空下界</td><td>{reload['nominal_contact_gap_bound_mm']:.3f}／{reload['nominal_tail_gap_bound_mm']:.3f}mm</td></tr><tr><td>穿出后规定线形调整</td><td>88项PASS；松量引入仍为有限样本</td></tr><tr><td>逐根穿线避开其余3根已就位线</td><td>12组有向检查PASS</td></tr><tr><td>装后头部姿态</td><td>130组合／520线姿态实例PASS</td></tr><tr><td>真实手工操作、完整固定及加工长度</td><td>尚未完成</td></tr></table>
<h2>局部材料变薄，尚不建议直接应用</h2><img src="journal_comparison.png" alt="原模型与J3轴颈截面对比，最小径向壁厚样本从2.25降到1.60毫米">
<p>圆柱段16个截面共11520条射线；入口倒角另720条列为不适用。截面积统计使用全部17个截面。这些值不能代替全件壁厚或PA12承载结论。</p>
<p class="note">头侧出口还留有一片薄边：45°剖面宽约0.277mm，侧向约1mm后与主体连上。它来自早期J1开通道，并非独立零件或显示褶皱。已定位来源，下一步需整理开口并复核局部材料；当前没有删除它或改动主模型。</p>
<h2>还需现在继续做</h2><p>出口薄边、身体端固定与松散尾线操作、俯仰段与CAM实际连接、其他7根活动线和FPC、完整装配与逐线加工长度。上述局部PASS没有关闭这些事项。</p>
<p><a href="README.md">详细范围与尺寸依据</a> · <a href="cleaned/candidate.blend">独立Blender候选</a> · <a href="reloaded_verification.json">回读及运动检查</a> · <a href="relaxation_screen.json">理线检查</a> · <a href="local_wire_order.json">穿线顺序</a> · <a href="upper_mouth_inspection.json">薄边来源</a> · <a href="journal_sections.json">截面采样</a> · <a href="commands.json">命令记录</a> · <a href="review_manifest.json">来源清单</a></p></html>'''
(OUT/'index.html').write_text(page)

base='/Applications/Blender.app/Contents/MacOS/Blender';rootcmd='mechanical/studies/prearrival_finish/harness_A8/'
actual=[]
for script,blend,log in [
 ('check_coupled_terminal_feed','mechanical/mori_v1_2.blend','coupled_feed.log'),
 ('build_coupled_feed_candidate','mechanical/mori_v1_2.blend','coupled_candidate_with_relaxation.log'),
 ('clean_coupled_feed_candidate',rootcmd+'assembly_feed_v3/candidate.blend','coupled_storage_with_relaxation.log'),
 ('verify_coupled_feed_candidate','mechanical/mori_v1_2.blend','coupled_verification.log'),
 ('check_coupled_feed_relaxation','mechanical/mori_v1_2.blend','coupled_relaxation.log')]:
    actual.append({'command':base+' -b '+blend+' -t 4 --python '+rootcmd+script+'.py > '+rootcmd+log+' 2>&1',
        'log':'../'+log,'evidence':'Script terminal marker and written result checked; these historical runs did not set --python-exit-code'})
for script,log in [('check_feed_wire_order','coupled_wire_order.log'),('inspect_coupled_feed_sections','coupled_sections_classified.log')]:
    actual.append({'command':base+' -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+rootcmd+script+'.py > '+rootcmd+log+' 2>&1','log':'../'+log,'evidence':'Process completion and written result checked'})
actual.append({'command':base+' -b mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python '+rootcmd+'inspect_upper_feed_mouth.py --python '+rootcmd+'inspect_coupled_feed_sections.py > '+rootcmd+'coupled_inspection_clarification.log 2>&1',
    'log':'../coupled_inspection_clarification.log','evidence':'First inspection completed; second script failed because shared bootstrap state was reused. Reran sections in a fresh process; never treated failed combined process as PASS.'})
reproduction=[]
for script,blend in [(s,'mechanical/mori_v1_2.blend') for s in ['check_coupled_terminal_feed','build_coupled_feed_candidate']]+[
    ('clean_coupled_feed_candidate',rootcmd+'assembly_feed_v3/candidate.blend')]+[(s,'mechanical/mori_v1_2.blend') for s in [
    'verify_coupled_feed_candidate','check_coupled_feed_relaxation','check_feed_wire_order','inspect_upper_feed_mouth','inspect_coupled_feed_sections']]:
    reproduction.append(base+' -b '+blend+' -t 4 --python-exit-code 1 --python '+rootcmd+script+'.py')
for s in ['plot_coupled_feed_review','publish_coupled_feed','verify_delivery']:
    reproduction.append('/Users/dean/.cache/codex-runtimes/mori-cad/bin/python '+rootcmd+s+'.py')
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'actual_runs':actual,
    'reproduction_commands_in_order_separate_processes':reproduction,
    'versions':{'blender':'5.2.2 LTS d13f752e3b9c','plot_python':'3.12.14'},
    'history':['Initial NameError feed run retained in coupled_feed_initial_error.log.',
        'Initial overlapping straight sweep faces failed storage checks; history_initial_storage_fins preserves failures.',
        'Feed-only candidate failed intermediate wire relaxation; history_feed_only preserves the failure and source hashes.',
        'An existing entry chamfer is excluded only from cylindrical-land thickness, not silently dropped from the area calculation.'],
    'main_model_applied':False},ensure_ascii=False,indent=2)+'\n')

sp=PARENT/'work_status.json';state=read(sp)
old=next(r['detail'] for r in state['remaining'] if r['id']=='harness')
for row in state['remaining']:
    if row['id']=='harness':row.update(detail=scope_detail,evidence='harness_A8/assembly_feed_v3/index.html')
state['A8_harness_research'].update(latest_review='harness_A8/assembly_feed_v3/index.html',
    J3_coupled_terminal_wire_feed='PASS',J3_saved_geometry_replay='PASS',J3_finite_relaxation_stages='PASS',
    J3_local_wire_installation_order='PASS',J3_head_motion='PASS',J3_applied=False,
    J3_upper_mouth_thin_edge='BLOCKED',J3_minimum_sampled_journal_wall_mm=after['minimum']['thickness_mm'],
    J3_full_print_wall_and_strength='NOT_TESTED',body_to_yaw_installation='NOT_TESTED',
    complete_UART_harness='BLOCKED',final_harness_drawing='BLOCKED')
state['updated_utc']=datetime.now(timezone.utc).isoformat();sp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
for path,href in [(HERE/'index.html','assembly_feed_v3/index.html'),(PARENT/'index.html','harness_A8/assembly_feed_v3/index.html')]:
    text=path.read_text();block=f'<section id="threading-update"><h2>最新：端子与尾线一起穿入的局部检查</h2><p>{scope_detail}</p><p><a href="{href}">查看J3截面、装配检查与未解决薄边</a>。下方保留早期研究记录。</p></section>'
    assert '<section id="threading-update">' in text
    text=re.sub(r'<section id="threading-update">.*?</section>',block,text,flags=re.S).replace(old,scope_detail);path.write_text(text)
path=HERE/'README.md';text=path.read_text()
note='<!-- coupled-feed-latest:start -->\n**最新进展：**'+scope_detail+'\n\n[J3带线穿装与截面检查](assembly_feed_v3/index.html)。下方为历史阶段资料，其PASS/BLOCKED仅针对当时的路线家族。\n<!-- coupled-feed-latest:end -->'
if '<!-- coupled-feed-latest:start -->' in text:text=re.sub(r'<!-- coupled-feed-latest:start -->.*?<!-- coupled-feed-latest:end -->',note,text,flags=re.S)
else:text=text.split('\n',1)[0]+'\n\n'+note+'\n'+text.split('\n',1)[1]
text=text.replace('## 最新进展：J2与对插包络复核','## 历史阶段：J2与旧对插包络复核').replace('## 最新进展：连续局部候选J1','## 历史阶段：连续局部候选J1')
path.write_text(text)

manifest={'status':'PASS','scope':'Review publication and source links only; upper mouth design is not closed',
    'updated_utc':datetime.now(timezone.utc).isoformat(),'source_blend_sha256':reload['source_blend_sha256'],
    'source_candidate_sha256':sha(OUT/'cleaned/candidate.blend'),'source_script_sha256':sha(Path(__file__)),
    'checks':{str(p.relative_to(OUT)):sha(p) for p in [OUT/'candidate_screen.json',OUT/'cleaned/storage.json',OUT/'reloaded_verification.json',OUT/'relaxation_screen.json',OUT/'local_wire_order.json',OUT/'journal_sections.json',OUT/'upper_mouth_inspection.json']},
    'images':[{'file':p.name,'sha256':sha(p)} for p in [OUT/'coupled_feed_sections.png',OUT/'journal_comparison.png']],
    'image_source_sections_sha256':sha(OUT/'sections.json'),'image_plot_script_sha256':sha(HERE/'plot_coupled_feed_review.py'),
    'main_model_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'review_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('J3_REVIEW_PUBLISHED_MAIN_UNCHANGED')
