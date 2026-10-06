"""Publish the full-member assembly and neck-size consistency findings."""
from pathlib import Path
import json, hashlib, re, html
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={};data={}
specs=[('rigid','rigid_screen.json','screen_CAM_complete_head_insertion.py'),
 ('coupled','coupled/screen.json','screen_CAM_coupled_head_body.py'),
 ('lower','lower_core/screen.json','screen_CAM_lower_core_insertion.py'),
 ('neck','neck_contact/screen.json','screen_CAM_neck_contact_consistency.py'),
 ('poses','neck_contact/pose_search/screen.json','plan_CAM_larger_neck_poses.py'),
 ('render','review/manifest.json','render_CAM_body_supply_review.py')]
for label,rel,script in specs:
    p=OUT/rel;d=read(p);data[label]=d
    assert d['script_sha256']==sha(A8/script)
    assert d['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
    assert not d['main_applied'] and not d['manufacturing_release'] and d['whole_harness']=='BLOCKED'
    for q in [p,A8/script]:inputs[str(q.relative_to(ROOT))]=sha(q)
rigid,coupled,lower,neck,poses,render=(data[k] for k in ['rigid','coupled','lower','neck','poses','render'])
assert len(rigid['rows'])==8 and all(r['status']=='BLOCKED' for r in rigid['rows'])
assert len(coupled['rows'])==10 and all(r['status']=='BLOCKED' for r in coupled['rows'])
assert lower['rows'][0]['status']=='BLOCKED' and lower['rows'][0]['failure']['offset_z_mm']==-3.
assert neck['rows'][0]['status']=='PASS' and neck['rows'][1]['status']=='BLOCKED'
assert all(r['status']=='BLOCKED' for r in neck['rows'][2:])
assert poses['status']=='BLOCKED' and len(poses['rows'])==49 and poses['passing_candidates']==0
assert render['physical_source_objects_preserved']==214
for r in rigid['substituted_unadopted_prints'].values():
    assert sha(ROOT/r['path'])==r['sha256'];inputs[r['path']]=r['sha256']
for name,h in rigid['protected_sources'].items():assert sha(ROOT/name)==h
for d in [coupled,lower]:assert d['helper_sha256']==sha(A8/'screen_CAM_complete_head_insertion.py')
assert neck['helper_sha256']==sha(A8/'screen_CAM_complete_head_insertion.py')
assert poses['helper_sha256']==sha(A8/'screen_CAM_neck_contact_consistency.py')
assert render['helper_sha256']==sha(A8/'screen_CAM_complete_head_insertion.py')
assert neck['path_helper_sha256']==sha(A8/'check_coupled_terminal_feed.py')
assert coupled['source_rigid_screen_sha256']==lower['source_rigid_screen_sha256']==render['source_rigid_sha256']==sha(OUT/'rigid_screen.json')
assert poses['source_consistency_sha256']==render['source_neck_sha256']==sha(OUT/'neck_contact/screen.json')
for im in render['images']:
    p=OUT/'review'/im['file'];assert sha(p)==im['sha256'];inputs[str(p.relative_to(ROOT))]=sha(p)
p=OUT/'review/review.blend';assert sha(p)==render['review_sha256'];inputs[str(p.relative_to(ROOT))]=sha(p)
for p in [A8/'check_coupled_terminal_feed.py',ROOT/'hardware/v1_2/head_harness_A8_20261003/sources/JST_PH_20261003.pdf',
          ROOT/'hardware/v1_2/head_harness_A8_20261003/sources/JST_PH_20261003_PDFKit_2.png',
          A8.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json',OUT.parent/'audit.json']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
gap=neck['rows'][1]['cases'][0]['failures'][0]['nominal_gap_below_1_mm']
assert .25<gap<.26
candidate_dir=OUT/'larger_neck_candidate'
candidate=read(candidate_dir/'publication.json')
assert candidate['status']=='PASS' and candidate['script_sha256']==sha(A8/'publish_CAM_larger_neck_candidate.py')
assert candidate['local_continuous_neck']==candidate['topology']=='PASS'
assert not candidate['main_applied'] and not candidate['manufacturing_release'] and candidate['whole_harness']=='BLOCKED'
for path,digest in candidate['source_files'].items():assert sha(ROOT/path)==digest,path
for path,digest in candidate['protected_files'].items():assert sha(ROOT/path)==digest,path
for path,digest in candidate['outputs'].items():assert sha(candidate_dir/path)==digest,path
for p in [candidate_dir/'publication.json',A8/'publish_CAM_larger_neck_candidate.py']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
staged_dir=OUT/'split_assembly';staged=read(staged_dir/'publication.json')
assert staged['status']=='PASS' and staged['script_sha256']==sha(A8/'publish_CAM_staged_supply_review.py')
assert staged['source_main_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
assert staged['complete_four_wire_material_present'] and staged['full_material_supply']=='BLOCKED'
assert staged['yaw_with_horn_members']==22 and staged['cradle_CAM_members']==14
assert staged['LCD_overlap_after_refresh_mm3']==0 and staged['front_camera_support_clearance']=='BLOCKED'
assert not staged['main_applied'] and not staged['manufacturing_release']
for path,digest in staged['source_files'].items():assert sha(ROOT/path)==digest,path
for path,digest in staged['outputs'].items():assert sha(staged_dir/path)==digest,path
for p in [staged_dir/'publication.json',A8/'publish_CAM_staged_supply_review.py']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
staged_summary='新顺序按身体上壳/承重桥、22件偏航与舵盘、14件头托与CAM分步装入，所查刚体位置通过。四根线的全长及PH插头已建入，身体段临时走位仍未通过。LCD代理姿态误报已修正；相机支架上角与前壳约0.00765mm³相交仍需处理。'
candidate_summary=(f"较大端子 1×1.8×4.1 mm 预留已有局部可行候选：临时 R10 弯道、竖直起点上移 1 mm，"
    f"仅扩大两件未采用候选的既有通道。四方向连续穿入及导线回位通过，端子/导线间隙下界约 "
    f"{candidate['contact_gap_bound_mm']:.3f}/{candidate['wire_gap_bound_mm']:.3f} mm；"
    f"轴颈径向壁厚最小样本 {candidate['journal_wall_before_mm']:.3f}→{candidate['journal_wall_candidate_mm']:.3f} mm。"
    "强度、全长供线及完整顺序仍未完成，候选未应用主模型。")
md=f'''# CAM 身体供线与整套装配：补查结果

**完整装配仍为 BLOCKED。主模型、结构参数和硬件文件未改。**
此前的上部穿入、回位、入座和弯线通过各自范围的检查。

## 最新：颈部已有独立局部候选

{candidate_summary}

[剖面对比、保存网格与连续检查](larger_neck_candidate/index.html)。下文保留原路径
与整套装配失败证据，不能把局部候选通过解读为这些装配问题都已解决。

## 更新：分步装配与完整线长

{staged_summary}

[分步顺序、全长导线和局部剖面](split_assembly/index.html)。这次完整材料候选将每根约153–162mm
头侧材料暂存在上方；还没有通过从身体到头部的整个过程，不能据此发布裁线尺寸。

## 原路径的颈部尺寸问题

同一条既有颈部路径、同一组候选打印件下：旧 0.8×1.35×3.9 mm 方盒通过
四个方向的有限位置检查。上部研究已经使用的 **1×1.8×4.1 mm 预留体**，
在四个方向的下部 R8 弯道均出现余量不足；首个位置的间隙约 **{gap:.3f} mm**，
低于项目分配的 0.3 mm。该首个位置预留体本身相交量为零，不能描述成
真实端子撞坏结构或整个行程都没有碰撞。

保持打印件不变，另试了 7 个导引半径和 7 个端子滚转角，共 49 组；均未通过。
这只排除了已检查的参数组合，不表示一切装法都不可能。

较大方盒依然是 **ASSUMED 空间要求**，并非厂家完整压接成品外形。
原研究没有缩小端子或降低 0.3 mm 要求；最新通道调整仅在上方链接的独立候选中。

![下部弯道的空间预留检查](review/larger_contact_neck_section.png)

## 完整头部不能直接套用承重桥装配动作

模型中 209 个机器人实体全部分配到移动组、固定组或明确的后装组。
旧动作的 22 件身体上壳组，配上完整 72 件头部组后发生碰撞；暂缓 8 件头壳
及其紧固件仍不能绕开 Pitch_Yoke。前期只移动承重桥的 PASS 不覆盖这套完整总成。

| 检查方向 | 结果 |
|---|---|
| 原上壳独立倾斜动作，完整头部或后装头壳 | 两组各四段，均检出碰撞 |
| 上壳与完整头部同步移动 | 10 种限定动作均未通过；插舌约束与基板阻挡仍在 |
| 把完整下部框架从下方装入 | 位移约 3 mm 时，基板与身体上壳相交 |
| PH 端子反向穿过当前颈部路径 | 两种参考预留均在上部入口检查失败 |

这些都是有限位置的诊断。失败证据足以否定相应动作，但不能代替新方案的
连续路径、全长导线、插头、扎带和工具检查。

![旧上壳动作与已装头部支架的冲突](review/head_shell_order_collision.png)

## 厂家资料与设计责任

[JST 官方 PH 目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)可找到系列端子
5.7、1.5、2.08 mm 的图示标注，以及 SPH-004T-P0.5S 的线材范围和压接工装。
共用系列图没有完整确认该型号压接后的外轮廓、公差和弹片突出，因此反向穿线
只用作参考空间比较。不能拿 PH 系列标注替换 SH 端子的尺寸。

供应商按图制作的方式已经确认。**路线、分支、长度基准和装配图仍由项目完成**；
目前的问题不能全部归到等实物。最新全长存放候选仍有间隙问题，需要与颈部进线
及后续动作统一设计，再确定裁线尺寸。

下一步将局部颈部候选与分步穿线、身体端胶壳后装或后插接统一，并核对整条导线的材料
长度和暂存空间；改变交货入壳状态或打印结构需在完整候选可审阅后交用户确认。
没有采纳这些变更，也没有给供应商发送信息或下单。

[数据总表](publication.json) · [完整总成成员与检查](rigid_screen.json) ·
[颈部尺寸一致性](neck_contact/screen.json) · [49组姿态尝试](neck_contact/pose_search/screen.json) ·
[独立 Blender](review/review.blend) · [此前的材料账](../README.md)
'''
(OUT/'README.md').write_text(md)
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CAM 全段装配补查</title>
<style>body{{font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#243b42;background:#f5f7f7;max-width:980px;margin:32px auto;padding:0 24px 50px}}section{{background:white;padding:22px;margin:20px 0;border-radius:10px}}.note{{background:#fff0d8}}img{{width:100%;max-width:760px}}a{{color:#087488}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}table{{border-collapse:collapse;width:100%}}</style>
<h1>CAM 身体供线与完整装配补查</h1><section class="note"><b>最新：分步装配有进展，完整供线仍未通过。</b><p>{staged_summary}</p><p><a href="split_assembly/index.html">查看分步顺序、完整线长与局部剖面</a>。主模型 M1.47 未改。</p></section><section><h2>既有颈部局部候选</h2><p>{candidate_summary}</p><p><a href="larger_neck_candidate/index.html">剖面对比与连续检查</a>。下方保留原路径及旧顺序的失败证据。</p></section>
<section><h2>颈部旧尺寸不能直接沿用</h2><p>1×1.8×4.1 mm 端子预留体在下部 R8 弯道的首个不足位置，间隙约 {gap:.3f} mm，低于 0.3 mm 设计分配。此位置没有名义方盒穿透；也不代表真实压接端子已经确认能装。</p><p>保持打印件不变的 49 组位置与滚转角组合均未通过。结果仅对应已测组合，没有宣称所有路径都不可能。</p><img src="review/larger_contact_neck_section.png" alt="端子空间预留在颈部下弯道的剖面"><p>橙色为 ASSUMED 空间预留，灰色为现有候选支架剖切。</p></section>
<section><h2>旧顺序只检查了承重桥</h2><p>把完整头部加入后，上壳独立倾斜动作会碰到头部支架。暂缓安装头壳也不能消除这处冲突。</p><table><tr><th>已检查的替代动作</th><th>结果</th></tr><tr><td>完整头部或后装头壳，沿原上壳动作</td><td>两组各四段均有碰撞</td></tr><tr><td>头部与上壳同步抬起</td><td>10种限定动作均未通过</td></tr><tr><td>完整下部框架由下方装入</td><td>约3mm处基板与外壳相交</td></tr><tr><td>参考 PH 端子反向穿入</td><td>两种预留体均未通过上部入口</td></tr></table><img src="review/head_shell_order_collision.png" alt="倾斜身体上壳与完整头部支架的相交部位"><p>展示副本作剖切；209件来源实体全部归组，没有用隐藏检查障碍物来放行。图中红色相交体部分位于不透明零件内部。</p></section>
<section><h2>接下来仍属于设计工作的部分</h2><p>核对分步穿线和身体端最后插接，完整放置每根余线，再统一导线长度、扎带和工具路径。如果需要改变打印结构或供应商交货时的入壳状态，先给出具体候选供确认。</p><p><a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST PH 官方资料</a>已查到系列外形和适用线材、工装。完整压接成品外形与公差仍需逐项确认，不能由系列图自动补全。</p></section>
<p><a href="README.md">完整说明</a> · <a href="publication.json">结果与来源</a> · <a href="rigid_screen.json">完整总成检查</a> · <a href="neck_contact/screen.json">端子一致性</a> · <a href="neck_contact/pose_search/screen.json">49组尝试</a> · <a href="review/review.blend">独立 Blender</a> · <a href="../README.md">既有材料账</a></p></html>'''
(OUT/'index.html').write_text(page)
report=dict(status='PASS',scope='Source-preserving publication of historical failures and an unadopted local neck pass, not assembly approval',
    script_sha256=sha(SCRIPT),source_main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),
    source_files=inputs,protected_files=rigid['protected_sources'],physical_source_objects=209,
    archived_blend_source_objects=214,full_head_old_sequence='BLOCKED',coupled_variants=10,lower_core_insertion='BLOCKED',
    larger_contact_neck='BLOCKED',larger_contact_first_shortfall_gap_mm=gap,neck_roll_offset_trials=49,
    larger_contact_neck_scope='Unmodified inherited candidate and old R8 path',
    larger_neck_candidate='PASS',larger_neck_candidate_main_applied=False,
    larger_neck_candidate_publication_sha256=sha(candidate_dir/'publication.json'),
    larger_neck_candidate_review='larger_neck_candidate/index.html',
    staged_supply_publication_sha256=sha(staged_dir/'publication.json'),staged_supply_review='split_assembly/index.html',
    complete_four_wire_material_present=True,full_material_supply='BLOCKED',
    source_proxy_pose_refresh='PASS',LCD_overlap_after_refresh_mm3=0.,front_camera_support_clearance='BLOCKED',
    continuous_full_assembly='NOT_TESTED',images_visually_reviewed=True,
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    outputs={n:sha(OUT/n) for n in ['README.md','index.html']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
statuspath=A8.parent/'work_status.json';status=read(statuspath)
previous_detail=next(r['detail'] for r in status['remaining'] if r['id']=='harness')
latest=status['A8_harness_research'];rel=str((OUT/'index.html').relative_to(A8.parent))
latest.update(CAM_full_member_body_sequence='BLOCKED',CAM_lower_core_insertion='BLOCKED',
    CAM_larger_contact_neck='BLOCKED',CAM_larger_contact_neck_gap_mm=gap,CAM_neck_pose_trials=49,
    CAM_larger_contact_neck_scope='Unmodified inherited candidate and old R8 path',
    CAM_larger_neck_candidate='PASS',CAM_larger_neck_candidate_main_applied=False,
    CAM_larger_neck_candidate_review=str((candidate_dir/'index.html').relative_to(A8.parent)),
    CAM_larger_neck_candidate_publication_sha256=sha(candidate_dir/'publication.json'),
    CAM_staged_supply_publication_sha256=sha(staged_dir/'publication.json'),
    CAM_staged_supply_review=str((staged_dir/'index.html').relative_to(A8.parent)),
    CAM_four_full_nominal_wires_present=True,CAM_full_material_supply='BLOCKED',
    CAM_yaw_with_horn_members=22,CAM_cradle_CAM_members=14,CAM_source_proxy_pose_refresh='PASS',
    CAM_LCD_overlap_after_refresh_mm3=0.,CAM_front_camera_support_clearance='BLOCKED',
    CAM_body_supply_current_review=rel,CAM_body_supply_publication_sha256=sha(OUT/'publication.json'))
for r in status['remaining']:
    if r['id']=='harness':
        r['status']='BLOCKED'
        r['detail']='上部穿入/回位/入座/弯线与颈部R10独立候选已通过各自连续检查，未应用主模型。新顺序先装22件偏航与舵盘、再装14件头托与CAM，有限刚体路径通过。四根名义全长、153–162mm上方暂存线尾及共同PH插头已建入，身体段供线动作仍有间隙/相交问题。扎带、真实端子入壳、另7根跨关节线/FFC、完整连续顺序仍未完成。CAM内六角螺钉待确认；裁线图未放行。'
        r['evidence']=str((staged_dir/'index.html').relative_to(A8.parent))
contact_row=dict(id='head_front_contact',item='相机支架与头前壳局部间隙',status='BLOCKED',owner='机械',
    detail='相机支架上角与头前壳存在约0.00765mm³名义相交，需处理局部间隙、壳厚和安装路径。LCD及三枚安装螺钉的隐藏碰撞代理已统一刷新；此前LCD约0.148mm³相交是姿态误报，刷新后为零，该处不改硬件。主模型保持。',
    evidence=str((staged_dir/'index.html').relative_to(A8.parent))+'#source-contact')
old_contact=next((r for r in status['remaining'] if r['id']=='head_front_contact'),None)
if old_contact:old_contact.update(contact_row)
else:status['remaining'].insert(2,contact_row)
current=next(r for r in status['remaining'] if r['id']=='harness')
detail=current['detail']
views={}
p=A8.parent/'index.html';t=p.read_text().replace(previous_detail,detail)
block=f'<section id="threading-update"><h2>最新：完整装配与颈部补查</h2><p>{html.escape(detail)}</p><p><a href="{rel}">查看剖面和检查范围</a>。下方保留历史阶段。</p></section>'
t,n=re.subn(r'<section id="threading-update">.*?</section>',lambda m:block,t,flags=re.S);assert n==1
row=f'<tr><td>完整线束</td><td>BLOCKED<br>机械＋硬件线材输入</td><td>{html.escape(detail)} <a href="{rel}">依据</a></td></tr>'
t,n=re.subn(r'<tr><td>完整线束</td>.*?</tr>',lambda m:row,t,flags=re.S);assert n==1
contact_html=f'<tr id="head-front-contact"><td>{contact_row["item"]}</td><td>BLOCKED<br>机械</td><td>{html.escape(contact_row["detail"])} <a href="{contact_row["evidence"]}">依据</a></td></tr>'
if '<tr id="head-front-contact">' in t:t,n=re.subn(r'<tr id="head-front-contact">.*?</tr>',lambda m:contact_html,t,flags=re.S);assert n==1
else:t=t.replace(row,row+contact_html)
views[p]=t
for p,link in [(A8/'index.html',str((OUT/'index.html').relative_to(A8))),
               (A8.parent/'head_harness/index.html','../'+rel),
               (A8.parent/'supplier_made_harness/index.html','../'+rel)]:
    t=p.read_text()
    if p==A8/'index.html':
        pat=r'<section id="threading-update">.*?</section>'
        block=f'<section id="threading-update"><h2>最新：完整装配与颈部补查</h2><p>{html.escape(detail)}</p><p><a href="{link}">查看剖面和检查范围</a></p></section>'
    else:
        a='<!-- A8_PITCH_FLEX_UPDATE -->';b='<!-- /A8_PITCH_FLEX_UPDATE -->'
        pat=re.escape(a)+'.*?'+re.escape(b)
        block=f'{a}<section><h2>完整装配与颈部补查</h2><p>{html.escape(detail)}</p><p><a href="{link}">查看剖面和检查范围</a></p></section>{b}'
    t,n=re.subn(pat,lambda m:block,t,flags=re.S);assert n==1;views[p]=t
p=A8/'README.md';t=p.read_text()
block='<!-- A8_PITCH_FLEX_LATEST -->\n最新见[分步装配与完整线长]('+str((staged_dir/'index.html').relative_to(A8))+')：22件偏航与舵盘先装、14件头托与CAM后装的有限刚体路径通过；四根名义全长及共同PH插头已建入，供线动作仍未通过。既有颈部局部候选保持未采用，完整顺序、扎带和真实端子入壳未完成。LCD代理误报已修正，相机支架与前壳小相交仍待处理。主模型保持。\n<!-- /A8_PITCH_FLEX_LATEST -->'
t,n=re.subn(r'<!-- A8_PITCH_FLEX_LATEST -->.*?<!-- /A8_PITCH_FLEX_LATEST -->',lambda m:block,t,flags=re.S);assert n==1;views[p]=t
for p,t in views.items():p.write_text(t)
statuspath.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print('BODY_SUPPLY_PUBLICATION PASS; body/neck sequence BLOCKED; main unchanged')
