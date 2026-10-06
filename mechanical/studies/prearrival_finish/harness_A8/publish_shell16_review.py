"""Publish the current rigid path and the separately scoped wire checks."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
ORDER=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order'
OUT=ORDER/'shell16_joint_feed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
inputs={}

def receive(path,script,helper=None):
    d=read(path);assert d['script_sha256']==sha(A8/script),script
    inputs[str(path.relative_to(ROOT))]=sha(path)
    inputs[str((A8/script).relative_to(ROOT))]=sha(A8/script)
    if helper:
        assert d['helper_sha256']==sha(A8/helper),helper
        inputs[str((A8/helper).relative_to(ROOT))]=sha(A8/helper)
    for name,h in d.get('source_files',{}).items():
        assert sha(ROOT/name)==h,name;inputs[name]=h
    for name,h in d.get('outputs',{}).items():
        assert sha(path.parent/name)==h,name
        inputs[str((path.parent/name).relative_to(ROOT))]=h
    if 'curves_sha256' in d:
        assert sha(path.parent/'curves.npz')==d['curves_sha256']
        inputs[str((path.parent/'curves.npz').relative_to(ROOT))]=d['curves_sha256']
    return d

prefix=receive(OUT/'screen.json','screen_shell16_joint_feed.py','screen_rear_plug_shell_angles.py')
audit=receive(OUT/'verification.json','verify_shell16_prefix.py')
rigid=receive(ORDER/'shell16_full_rigid_path/screen.json','verify_shell16_rigid_path.py','diagnose_shell16_continuations.py')
linear=receive(ORDER/'shell16_back20_wire_families/screen.json','screen_shell16_back20_wire_families.py','screen_shell16_joint_feed.py')
graph=receive(ORDER/'shell16_back20_piecewise/screen.json','search_shell16_back20_piecewise.py','screen_shell16_back20_wire_families.py')
merged=receive(ORDER/'shell16_back20_merged/screen.json','merge_shell16_back20_wires.py','screen_shell16_back20_wire_families.py')
relief=receive(ORDER/'shell16_fourth_wire_relief/screen.json','screen_shell16_fourth_wire_relief.py','merge_shell16_back20_wires.py')
coupled=receive(ORDER/'shell16_coupled_hold_timing/screen.json','screen_shell16_coupled_hold_timing.py','merge_shell16_back20_wires.py')
projection=receive(OUT/'projections.json','extract_shell16_review.py')
plot=receive(OUT/'plot.json','plot_shell16_review.py')
assert prefix['status']==audit['status']==rigid['status']==graph['status']==projection['status']==plot['status']=='PASS'
assert rigid['sample_records']==297 and rigid['unique_poses']==294
assert audit['finite_sample_records']==98 and audit['unique_rigid_poses']==97
assert graph['complete_attached_assembly']=='BLOCKED'
for p,h in prefix['protected_sources'].items():assert sha(ROOT/p)==h,p
source_review_path=A8/'rear_plug_source_review/inspection.json'
source_review=receive(source_review_path,'review_rear_plug_sources.py')
for p in [source_review_path,A8/'rear_plug_source_review/README.md']:
    inputs[str(p.relative_to(ROOT))]=sha(p)
best_back=coupled if coupled['status']=='PASS' else relief
back_pass=best_back['status']=='PASS'
wire_text=(f"四根CAM线合并后的20mm后移，{len(best_back['records'])}个有限位置通过；仍需检查下一段竖直提离与完整连续装配。"
           if back_pass else "三根受限CAM线分别找到分步后移路径，第4根已有路线；合并检查仍有线间间隙问题，后移阶段尚未整体通过。")
supplier_link=os.path.relpath(A8/'supplier_source_update/index.html',OUT)
source_link=os.path.relpath(A8/'rear_plug_source_review/README.md',OUT)
graph_positions={r['pin']:len(r['selected_rows']) for r in graph['results']}
md=f'''# 外壳与桥的装配顺序候选

四段刚体路径已通过有限位置检查；完整带线装配仍未完成。主模型M1.47和硬件文件保持。

![顺序和检查范围](sequence.png)

## 相比此前解决了什么

后板J2插头继续使用11.8×6.85×4.8mm的原保守包络，没有缩小或删去。
外壳倾角从15°改为16°，仍上抬14mm；随后桥保持水平上抬18mm。
接着外壳与桥一起后移20mm，再一起竖直提离。
这个动作替代了原先会在后板J2/托板或外壳/桥之间相交的几种直接移动方式。

四段刚体复核：61、37、81、118个检查记录，总297记录、294个不同位置。
包含94件身体核心、22件上壳组、6件固定桥组，已安装身体/后板插头分配，以及14根固定身体线。
后续头部组件尚未装入；这些成员和该工序限制已在检查文件中列明。
直至最后一步，桥累计上移76.5mm，外壳累计上移72.5mm，保持16°和20mm后移。
这里的提离高度用于明确刚体已分离，不是要求人手精确停在这个高度。

## 导线检查的真实范围

前两段含四根CAM线共同检查：61+37记录、97个不同刚体位置，精确复用已经保存的完整导线形状。
两个阶段边界相同，全部名义线长保持；前两段导线相互最小保守间隙{audit['CAM_pair_gap_lower_bound_mm']:.3f}mm。

![前两段的三维实体投影](prefix_views.png)

{wire_text}

分步搜索中，CAM1、2、3各自检查位置分别为{graph_positions[1]}、{graph_positions[2]}、{graph_positions[3]}。
这三项是单根线对零件和既有身体线的结果，不能代替四根CAM线相互检查。
最初合并时CAM3/CAM4的保守间隙为{merged['failure']['surface_gap_lower_bound_mm']:.3f}mm，未达到本研究0.3mm几何预留。
后续比较提前调整第4根临时弯线的方式，以及第1/2根配对收弯的时机，具体结果见[第4根调整](../shell16_fourth_wire_relief/screen.json)和[共同收弯时序](../shell16_coupled_hold_timing/screen.json)。
这是所列有限参数和离散位置的结论，不是所有方案不可能，也不是无接触的连续运动证明。

## 插头来源

JST原厂PH目录给出了胶壳名义尺寸。本模型法向4.8mm来自直角板座的完整高度，PHR胶壳名义4.5mm；
准确插合位置和凸筋未完全定义，不能仅删减这0.3mm来放行。[本次来源核对]({source_link})。
原厂[PH目录](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)与[JST德国PHR-5页](https://jst.de/produkt/3526/680902-00)均有记录。

## 仍未完成

- 四根线的后移/竖直提离衔接及完整连续间隙；人手、夹持和扎带操作。
- H01/H04带线装入、其余跨关节线、FPC、后板支路线的完整顺序。
- 真实端子入壳及压接外形、实际线材/供应商首件。自由端子仍是明确标注的空间分配。
- 此研究使用既有尚未采用的Yaw Base/Pitch Yoke/Pitch Cradle候选，不能声称主模型已经采用。

供应商按图制作方式已确认，当前裁线尺寸与制造图未放行。

[刚体四段检查](../shell16_full_rigid_path/screen.json) · [前两段记录校验](verification.json) ·
[单根分步路径](../shell16_back20_piecewise/screen.json) · [来源清单](publication.json) · [进度总页]({supplier_link})
'''
(OUT/'README.md').write_text(md)
html=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MORI · 外壳与桥的装配顺序候选</title><style>body{{max-width:1120px;margin:auto;padding:24px;font:16px/1.8 system-ui,-apple-system,"PingFang SC",sans-serif;color:#263f47;background:#f4f7f7}}section{{background:#fff;padding:24px;margin:20px 0;border-radius:12px}}a{{color:#086d7e}}img{{width:100%;height:auto}}.note{{background:#fff0d9}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;border-bottom:1px solid #dfe7e8;padding:10px}}</style>
<p><a href="{supplier_link}">← 厂家资料与设计进度</a></p><h1>外壳与桥的零件路径已走通</h1>
<section class="note"><p>四段刚体检查通过。完整线束仍待衔接；主模型M1.47与硬件文件保持，制造图尚未放行。</p></section>
<section><h2>保留插头尺寸，调整装配顺序</h2><a href="sequence.png"><img src="sequence.png" alt="外壳16度抬高14毫米，桥上移18毫米，一起后移20毫米，再一起上移提离；各阶段检查范围分别标示"></a><p>297个检查记录、294个不同位置。包含身体与后板插头包络、14根固定身体线。后续头部件尚未安装；使用既有未采用的结构候选。</p></section>
<section><h2>前两段已经和CAM导线一起检查</h2><p>61+37个记录，392条保存曲线与此前联合抬升结果逐条相同；两段之间的边界保持。完整名义线长未缩短。</p><a href="prefix_views.png"><img src="prefix_views.png" alt="原始位置、外壳释放、桥上抬三个状态的侧面投影"></a></section>
<section class="note"><h2>后续导线：单根通过与四根一起通过要分开看</h2><p>{wire_text}</p><p>最初合并在第3、第4根之间只有约0.173mm保守间隙，低于研究采用的0.3mm预留。因此继续比较第4根的临时弯线，以及第1/2根配对收弯的时机，没有增加接口或修改打印件。</p><p><a href="../shell16_back20_piecewise/screen.json">单根分步路径</a> · <a href="../shell16_fourth_wire_relief/screen.json">第4根调整</a> · <a href="../shell16_coupled_hold_timing/screen.json">共同收弯时序</a></p></section>
<section><h2>已经取得的插头资料</h2><p>官方目录有PHR-5胶壳的名义外形尺寸。当前模型还保留板座法向余量和未完全确认的插合位置；这次没有缩小插头来消除检查结果。</p><p><a href="{source_link}">来源核对与尺寸边界</a> · <a href="https://www.jst-mfg.com/product/pdf/eng/ePH.pdf">JST原厂PH目录</a></p></section>
<section><h2>仍需完成</h2><p>后移和竖直提离时四根线的衔接、完整连续间隙、H01/H04带线装入、其他跨关节线和FPC，以及人手/扎带操作。真实压接外形和首件仍需后续验证。</p><p>这些范围分别记录，有限几何通过不代表实物装配或制造已经放行。</p><p><a href="README.md">详细说明</a> · <a href="../shell16_full_rigid_path/screen.json">四段刚体复核</a> · <a href="verification.json">保存记录校验</a> · <a href="publication.json">来源与结果范围</a></p></section></html>'''
(OUT/'index.html').write_text(html)
report=dict(status='PASS',scope='Publication and source consistency; complete assembly remains open',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),source_files=inputs,
    protected_sources=prefix['protected_sources'],rigid_sample_records=297,rigid_unique_poses=294,
    prefix_wire_sample_records=98,prefix_unique_poses=97,prefix_wire_status='PASS',
    back20_individual_status='PASS',back20_four_wire_status=best_back['status'],vertical_wire_status='NOT_TESTED',
    continuous_assembly='NOT_TESTED',complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False,
    outputs={n:sha(OUT/n) for n in ['README.md','index.html','sequence.png','prefix_views.png','projections.json','plot.json']})
(OUT/'publication.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
state_path=A8.parent/'work_status.json';state=read(state_path)
state['CAM_shell16_body_sequence']=dict(publication=str((OUT/'publication.json').relative_to(A8.parent)),
    publication_sha256=sha(OUT/'publication.json'),rigid_finite_path='PASS',rigid_sample_records=297,
    first_two_stages_with_CAM='PASS',prefix_sample_records=98,back20_individual='PASS',back20_four_wires=best_back['status'],
    vertical_CAM='NOT_TESTED',complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
state['CAM_H02_joint_lift']['shell16_followup']=str((OUT/'index.html').relative_to(A8.parent))
for item in state['remaining']:
    if item['id']=='harness':
        item['latest_shell16_evidence']=str((OUT/'index.html').relative_to(A8.parent))
        item['latest_shell16_detail']='外壳16°/抬高14mm、桥抬18mm后一起后移20mm再提离，四段刚体297记录通过；前两段含CAM共98记录通过。'+wire_text+'完整线束与制造图仍BLOCKED。'
state['updated_utc']=report['generated_utc']
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print('SHELL16_REVIEW_PUBLISHED rigid PASS297; wire-prefix PASS98; wire-back',best_back['status'],'full assembly BLOCKED')
