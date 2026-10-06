"""Publish the sourced terminal geometry and continuous forming substep."""
from pathlib import Path
import hashlib,json,shutil,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3];FM=A8/'cam_wire_forming';OUT=FM/'terminals'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=read(OUT/'screen.json');c=read(FM/'continuous/screen.json');a=read(FM/'continuous/math_audit.json')
h=read(FM/'housed/screen.json');e=read(FM/'end_approach/screen.json');r=read(OUT/'render_manifest.json')
lift6=read(FM/'lifted_end/screen.json');lift2=read(FM/'lifted_end2/screen.json')
for report,script in [(t,'check_CAM_forming_terminals.py'),(c,'check_CAM_forming_continuous.py'),
    (a,'audit_CAM_forming_bounds.py'),(h,'screen_CAM_housed_forming.py'),(e,'check_CAM_forming_end_approach.py'),
    (r,'render_CAM_forming_contact_review.py'),(lift6,'screen_CAM_forming_lifted_end.py'),(lift2,'screen_CAM_forming_lifted_end2.py')]:
    assert report['script_sha256']==sha(A8/script)
    assert report['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
    assert not report['main_applied'] and report['whole_harness']=='BLOCKED'
assert t['status']==a['status']==r['status']=='PASS'
assert c['status']=='BLOCKED' and not c['complete_coverage'] and c['unproved_intervals']
assert lift6['status']=='BLOCKED' and lift2['status']=='PASS'
assert lift2['final_plug_lift_mm']==2 and lift2['continuous_forming']=='NOT_TESTED'
assert h['status']=='BLOCKED' and any(x['housing']['hits'] for tr in h['trials'] for x in tr['rows'])
assert e['status']=='BLOCKED' and not any(z['physical_surface_intersection_witness'] for x in e['rows'] for z in x['hits'])
assert r['source_terminal_screen_sha256']==sha(OUT/'screen.json') and r['source_housed_screen_sha256']==sha(FM/'housed/screen.json')
assert r['review_sha256']==sha(OUT/'review.blend')
pdf=A8.parent/'supplier_made_harness/recheck_20261004/JST_SH.pdf';assert sha(pdf)==t['contact_source_pdf_sha256']
for x in r['images']:assert sha(OUT/x['file'])==x['sha256']
count=len(c['passed_intervals']);contactgap=c['minimum_contact_gap_lower_bound_mm'];seatgap=c['minimum_seating_gap_lower_bound_mm']
failuregap=min(x['failure'].get('gap_mm',float('inf')) for x in c['unproved_intervals'])
liftcount=len(lift2['trials'][-1]['rows'])
md=f'''# CAM端子资料与成形复核

供应商按图制作已确定。公开资料由项目查询，MORI走线、分支和长度图由项目设计。主模型M1.47、正式PCB、STL和正式装配视频未改。

## 找到的资料与证据边界

[JST官方SH目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)第2页给出SSH-003T-P0.2-H端子标称跨度0.8×1.35×3.9mm、AWG32–28和绝缘外径0.4–0.8mm范围。[保存的官方目录](../../../supplier_made_harness/recheck_20261004/JST_SH.pdf)哈希与检查记录一致。

本次按跨度构造长方体检查包络。它不是完整厂家CAD，也不是实际压接后的轮廓或公差。CAM插座只有SH1.0系列信息，真实厂牌、完整料号和针腔视图仍未确认，不能据此放行互配或针序。

新增[同料号端子的官方细节图](../../ssh_catalogue_addendum/README.md)显示，下方锁止弹片超出上述1.35mm尺寸线。该方盒不能理解为完整外形最大包络；历史检查结果只保留原声明范围，不能直接用于真实端子装配放行。

![散端子靠近头托](loose_terminals.png)

黄铜色长方体是端子检查包络。上图仅隔离显示头托和线端以便查看；其他零件仍参与检查。四色不是电气针序。

## 连续检查发现原41位置筛查漏检

原最大抬高9mm、最终直接回到安装高度的路线，散端子在41个位置均保留0.3mm间隙。但连续检查在成形参数约0.9867附近发现：端子与头托间隙约{failuregap:.3f}mm，低于0.3mm要求。

已证明{count}个区间，另31个小区间未通过后停止细分；**全过程覆盖为否，连续结果为BLOCKED**。这是明确的名义间隙不足，不能把之前的41位置PASS写成完整路线通过；也不能仅凭这一数值声称端子已经穿入材料。未扩大孔槽或删掉周围实体。

末段导线落槽另作检查：对已有有槽托床检查实际线径无穿透，其他区域保持0.3mm。51个末段位置未发现导线本体穿入托床；这份有限检查不能替代未完成的连续末段验证。名义槽半径0.35mm和最大线半径0.3302mm间只有约0.02mm径向余量，实际配合仍需试打。

## 新的装配顺序候选：在上方2mm完成成形

先试了6mm线端抬高：线与端子有限位置通过，但CAM板从12mm下降到6mm时，板上麦克风及元件会碰到头托，因此整段未通过。

随后缩为2mm：先把散端子停在最终位置上方2mm，准备装入胶壳；CAM板从上方8mm降至2mm完成6mm相对插合，再沿既有落座曲线降到0mm。模型不拉长导线、不改支架，不移动最终板卡和插座。

| 子项 | 当前证据 |
|---|---|
| 2mm成形路线，四根线及标称散端子对已装实体 | PASS，{liftcount}个有限位置；最大临时线环抬高仍为9mm |
| CAM板从8mm下降到2mm、插头留在2mm | PASS，后续1057个连续区间已覆盖刚体与四线 |
| 与原落座曲线的端点衔接 | PASS，最终自由端与既有h=2mm曲线端点一致，总线长不变 |
| 新路线完整连续成形 | 未完成；后续已发现线间实体相交，停止只算线对结构件的旧路线 |
| 四线之间及上游导线 | BLOCKED；参数0.8处中心线距离上界0.527150mm，小于两线半径之和0.6604mm |
| 端子对导线 | 有限位置未检出相交，但0.3mm操作裕量未通过；装壳顺序未完成 |
| 端子插入胶壳、扎带收紧及初次颈部穿线到此初态 | NOT_TESTED |

裸端子盒在1mm节距下只有0.2mm标称间隙，不满足原0.3mm裕量；实际压接外形、四个自由端的操作顺序和装壳过程仍待处理。

## 先装胶壳再弯曲的既定路线未通过

![预装胶壳碰到舵机](housing_collision.png)

局部隔离视图显示相关舵机和胶壳；检查仍用完整工序实体。9mm候选有位置仅剩约0.112mm间隙。增大到12、15、18mm的轨迹均有相交；图中12mm候选与俯仰舵机相交约9.65mm³。保留失败，不为此给支架开孔；这些检查并非证明所有预装胶壳工序都不可能。

![早期9mm线环候选概览](forming_overview.png)

本工序未安装CAM板、显示支架和头壳，CAM扎带尚未收紧，已有Yaw接触只沿用不动的前4.3mm。线束座、颈部通道及四枚CAM内六角螺钉仍属未全部采用的候选。主模型未改，没有采购或制造放行。

其余七根跨关节功能线、USB完整尾线、LCD排线、相机FPC及身体固定还需完成。供应商最终分支图和裁线图尚未发布，原有参考长度不能当作裁线尺寸。

[未通过的连续记录](../continuous/screen.json) · [曲线公式复核](../continuous/math_audit.json) · [新的2mm候选](../lifted_end2/screen.json) · [6mm方案的板卡冲突](../lifted_end/screen.json) · [端子41位置](screen.json) · [胶壳失败记录](../housed/screen.json) · [独立Blender](review.blend) · [命令](commands.json) · [交付记录](review_manifest.json)
'''
md=md.replace('## 找到的资料与证据边界','## 最新：新路线的四线成形动作连续通过\n\n[当前四段路径及步骤衔接](../lifted_end2/index.html)：最后一根从负侧绕开原相交位置，四段规定成形动作已连续通过；板卡8→2mm连续下降保持通过。初始穿线、端子入壳、扎带和完整装配仍未完成，主模型未改。下文保留旧路线的端子及间隙记录。\n\n## 找到的资料与证据边界')
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI · CAM端子与成形复核</title><style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;max-width:1060px;margin:30px auto;padding:0 24px 60px;background:#f4f6f5;color:#253b3d}}a{{color:#096a74}}.note{{padding:18px;background:#fff0d9;border-radius:10px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}img{{width:100%;border-radius:8px}}figure{{margin:20px 0}}figcaption{{font-size:14px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #cad7d2}}table{{width:100%;border-collapse:collapse}}@media(max-width:700px){{.pair{{display:block}}}}</style>
<p><a href="../index.html">← 早期成形研究</a> · <a href="../../cam_socket_tool/index.html">螺钉待确认方案</a></p>
<h1>加入端子后，连续检查发现末段间隙不足</h1>
<p class="note">原41位置通过只是初筛。连续检查在接近最终位置时发现端子与头托间隙约{failuregap:.3f}mm，低于0.3mm要求；原路线未通过。主模型M1.47未改。</p>
<h2>公开资料已用于模型检查</h2><p><a href="https://www.jst-mfg.com/product/pdf/eng/eSH.pdf">JST官方SH目录</a>给出端子0.8×1.35×3.9mm标称跨度。金色为按此构造的检查包络，不是实际压接CAD。实际CAM插座料号和针腔视图仍待确认。</p>
<div class="pair"><figure><img src="loose_terminals.png" alt="散端子接近头托的局部"><figcaption>只隔离显示头托和端子以便查看，其余零件仍参与检查。</figcaption></figure><figure><img src="housing_collision.png" alt="预装胶壳碰到俯仰舵机"><figcaption>预装胶壳的失败路线：12mm临时抬高，与舵机相交约9.65mm³。</figcaption></figure></div>
<h2>新候选：先在上方2mm完成成形</h2><p>散端子在上方2mm完成成形，再准备装入胶壳；CAM板从8mm降到2mm完成相对插合，随后沿既有落座曲线降到0mm。{liftcount}个成形位置和25个板卡下降位置通过初筛。没有拉长导线、挪动最终板卡或修改支架。</p>
<table><tr><th>项目</th><th>状态</th></tr><tr><td>原路线连续过程</td><td>BLOCKED；{count}个区间已证，另31个末段区间未通过，完整覆盖未完成。</td></tr><tr><td>新2mm候选</td><td>有限位置PASS；连续成形和连续板卡插合尚未检查。</td></tr><tr><td>固定槽与端子间隙</td><td>槽的名义径向余量约0.02mm；裸端子彼此只有0.2mm标称间隙，仍需实物配合与装壳顺序核对。</td></tr><tr><td>完整线束</td><td>未完成：线间、端子对导线、装壳、扎带、初次穿线及其他线路仍需继续。</td></tr></table>
<p>供应商按图制作已确定。公开资料由项目搜集，线路与裁线图由项目设计。尚无正式裁线图和制造放行。</p>
<p><a href="README.md">完整说明</a> · <a href="../continuous/screen.json">连续失败记录</a> · <a href="../lifted_end2/screen.json">2mm候选结果</a> · <a href="../lifted_end/screen.json">6mm候选的板卡冲突</a> · <a href="review.blend">原9mm候选Blender</a> · <a href="commands.json">命令</a> · <a href="review_manifest.json">交付记录</a></p></html>'''
html=html.replace('<h2>公开资料已用于模型检查</h2>','<section class="note"><h2>最新：新路线的四线成形动作连续通过</h2><p>最后一根从负侧绕开旧路线的相交位置，四段规定动作与步骤衔接检查通过。板卡8→2mm连续下降也已通过。初始穿线、端子入壳、扎带和完整装配仍未完成。<a href="../lifted_end2/index.html">查看当前路线与证据</a></p></section><h2>公开资料已用于模型检查</h2>')
html=html.replace('有限位置PASS；连续成形和连续板卡插合尚未检查。','新路线四线规定成形动作及板卡下降连续PASS；初次穿线、端子入壳和完整工序仍未完成。')
html=html.replace('<h2>公开资料已用于模型检查</h2>','<h2>公开资料已用于模型检查</h2><p class="note">新增同料号的官方细节图显示：下方锁止弹片超出 1.35 mm 尺寸线。旧方盒不含完整弹片，不能用来确认真实端子装配。<a href="../../ssh_catalogue_addendum/README.md">查看原图与新增尺寸</a>。</p>')
(OUT/'index.html').write_text(html)
commands=[]
jobs=[('check_CAM_forming_terminals.py','terminals','terminals/screen.log'),
 ('check_CAM_forming_end_approach.py','end_approach','end_approach/screen.log'),
 ('screen_CAM_housed_forming.py','housed_forming','housed/screen.log'),
 ('check_CAM_forming_continuous.py','continuous','continuous/screen.log'),
 ('audit_CAM_forming_bounds.py','bounds','continuous/math_audit.log'),
 ('render_CAM_forming_contact_review.py','contact_render','terminals/render.log'),
 ('screen_CAM_forming_lifted_end.py','lifted_end','lifted_end/screen.log'),
 ('screen_CAM_forming_lifted_end2.py','lifted_end2','lifted_end2/screen.log')]
for script,log,output in jobs:
    source=Path('/tmp')/('mori_CAM_forming_'+log+'.log')
    if log=='housed_forming':source=Path('/tmp/mori_CAM_housed_forming.log')
    if source.is_file():shutil.copyfile(source,FM/output)
    else:assert (FM/output).is_file(),f'Missing preserved execution log: {FM/output}'
    commands.append('/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend -t 4 --python-exit-code 1 --python mechanical/studies/prearrival_finish/harness_A8/'+script)
(OUT/'commands.json').write_text(json.dumps({'cwd':str(ROOT),'commands':commands,'versions':{'Python':platform.python_version(),'Blender':'5.2.2 LTS d13f752e3b9c'}},indent=2)+'\n')
files=[p for folder in ['terminals','continuous','housed','end_approach','lifted_end','lifted_end2'] for p in (FM/folder).rglob('*')
       if p.is_file() and p.name!='review_manifest.json' and not p.name.endswith('.blend1')]
files.append(FM/'lifted_end2/review_manifest.json')
(OUT/'review_manifest.json').write_text(json.dumps({'status':'PASS','scope':'Source-linked digital substep delivery; whole harness incomplete',
 'script_sha256':sha(SCRIPT),'source_main_sha256':t['source_main_sha256'],'source_contact_pdf_sha256':sha(pdf),
 'source_continuous_sha256':sha(FM/'continuous/screen.json'),'source_math_audit_sha256':sha(FM/'continuous/math_audit.json'),
 'continuous_status':'BLOCKED','continuous_passed_intervals':count,'new_lifted2_screen_sha256':sha(FM/'lifted_end2/screen.json'),'source_contact_dimensions_mm':t['contact_nominal_box_mm'],
 'new_lifted2_delivery_sha256':sha(FM/'lifted_end2/review_manifest.json'),
 'terminal_catalogue_span_is_complete_envelope':False,
 'extra_contact_catalogue_sha256':sha(A8/'ssh_catalogue_addendum/JST_eLBT.pdf'),
 'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'images_visually_reviewed':True,
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
print('CAM_FORMING_CONTACT_PUBLISHED',len(files),'continuous_intervals',count,flush=True)
