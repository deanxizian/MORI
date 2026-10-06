"""Publish only completed checks; preserve unresolved full wiring and approvals."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes';REST=OUT/'cam_restraints';VIEW=REST/'bench_review_clear'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
paths=[REST/'bench_preassembly_v2/review.json',REST/'bench_transfer/review.json',REST/'PH_terminal_gate/review.json',VIEW/'review.json']
reports=[read(p) for p in paths]
for r in reports:
    assert r['status']=='PASS' and not r['main_changed']
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
pub=read(OUT/'publication.json');assert not pub['C6_approved']
assert pub['source_blend_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
# Recheck actual protected files, exports and video; do not just repeat an old
# validation status or write a new main-model delivery receipt.
delivery_path=HERE.parent/'neck_adoption/delivery.json';deliv=read(delivery_path)
assert all(sha(ROOT/p)==h for p,h in deliv['files'].items())
protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
assert all(sha(ROOT/p)==h for p,h in protected.items())
exports=read(ROOT/'mechanical/reports/export_manifest.json')
assert all(sha(ROOT/'mechanical'/r['file'])==r['sha256'] for r in exports['parts'])
animation=read(ROOT/'mechanical/animation/delivery.json')
assert animation['source_revision']=='V1.2-M1.49' and animation['video_status']=='PASS'
assert all(sha(ROOT/'mechanical'/f)==h for f,h in animation['files'].items())
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
integrity=REST/'bench_main_integrity.json'
write(integrity,dict(status='PASS',utc=now,main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),
 config_sha256=sha(ROOT/'config/geometry.json'),main_delivery_files_checked=len(deliv['files']),
 protected_hardware_files_checked=len(protected),STL_files_checked=len(exports['parts']),
 animation_revision=animation['animation_revision'],animation_files_checked=len(animation['files']),
 source_delivery_sha256=sha(delivery_path),main_changed=False,script_sha256=sha(Path(__file__))))
assets=[];figures=''
labels={
 'bench_cutting.png':'先在离机头托上固定、剪尾。橙色线框是剪钳作业包络，不是零件；图中截去包络的远端。',
 'above_yoke.png':'预装好的头托移到偏航座上方，再竖直下放。图示距最终位置35mm；实际检查从80mm上方开始。',
 'seated_loose_leads.png':'头托已落座，四根身体端线尾仍暂时举起。它们尚未穿入导向和颈部，也未插入PH胶壳。',
 'PH_gate.png':'局部PH端子穿口检查：琥珀色是目录轮廓的直线扫掠，三根已穿导线暂时分成两排。不是实际端子的精细模型。',
}
for row in reports[-1]['images']:
 p=VIEW/row['file'];assert sha(p)==row['sha256'];assets.append(p)
 figures+=f'<figure><img src="{p.relative_to(OUT).as_posix()}" alt="{html.escape(labels[row["file"]])}" style="width:100%"><figcaption>{labels[row["file"]]}</figcaption></figure>'
blend=VIEW/'MORI_M1_49_CAM_bench_sequence.blend';assert sha(blend)==reports[-1]['blend_sha256'];assets.append(blend)
note=OUT/'CAM_BENCH_SEQUENCE.md'
note.write_text('''# CAM线束：离机预装与带线头托落座

主模型保持已批准的M1.49 C5＋K1。本研究使用guide_v4和return_clamp_v3两个既有候选特征，没有进一步加高夹持座。C6及固定特征均未应用到主模型、STL或视频。

## 这次完成的检查

1. 将Pitch_Cradle、CAM板、板上麦克风、4枚CAM螺钉、6个相关嵌件和候选扎带作为离机组件，放在机体右侧180mm处。两只舵机、偏航托架和俯仰轴承保留在机器人上；光学组件、头壳、短轴和最终锁紧依明确顺序后装。
2. 从CAM端经过回弯和15mm夹持直段的原路径不变；身体端余线暂时向上伸直。四条中心线总长分别约373.855、380.906、370.226、357.472mm，数值误差小于0.000001mm。这些是现有路线的名义长度，不是供应商裁线长度。裸端子及末端加工长度尚未冻结。
3. 名义剪钳作业包络和6种80mm扎带长尾空间均PASS。真实手部、张紧力及剪切动作尚未验证，不能把估计工具外形称为原厂CAD。
4. 组件先上抬80mm，横移180mm，再下放80mm。按0.25mm步长检查1363个位置；所查实体、四条导线、其他七条参考线无相交。四线自身/相互间距检查通过。固定件几何距离采用0.126mm截断查询，只能报告该检查阈值下的下界，不能称为整机最小间隙。
5. PH目录的通用未压接端子轮廓为5.7×2.08×1.5mm，采用2.08×1.5mm横截面，在现有5.5×2.6mm导向口局部直穿，另外三线暂时分两排，条件PASS。真实压接外形、公差和完整穿线仍未验证。

## 尚未关闭

- 头托落座之后，身体端自由线尾如何穿过导向和颈部、整理到最终连续路线，并装入PH胶壳和插合。
- 端子与线材选型统一：正式旧交接的SPH-002T-P0.5S要求绝缘OD0.8–1.5mm，当前几何细线OD0.6604mm不在范围内；SPH-004T-P0.5S的目录OD范围0.5–0.9mm仅在外径这一项匹配，还不是已选/已验证方案。详见CAM_PH_TERMINAL_HANDOFF.md。
- 身体端固定、其余上端接口、FFC/FPC和整机带线装配。

没有新增独立打印件、没有更改原生PCB或硬件合同。滑动磨损、压接、夹持力、动态弯折寿命与PA12强度仍需实物验证。

## 保留的未采用试验

- 把夹持座进一步上移4mm，运动几何通过但剪钳仍受阻，未选用。
- 第一版离机检查把原有夹持接触段误纳入非接触间距检查，因此报告BLOCKED。v2按实际变更边界，仅重新检查Z224.6000061mm以上的新自由线段；以下线形从通过的原路径完整复制，已有夹持实体/管形检查按源哈希复用。未修改打印件以消除这次检查结果。
''')
handoff=OUT/'CAM_PH_TERMINAL_HANDOFF.md'
handoff.write_text('''# CAM身体端PH端子：机械研究交接待统一项

状态：BLOCKED。此文件只是机械交接记录，未发送给供应商，未改hardware/或contracts/components.json，也没有选定替换料号。

| 来源/对象 | 已知字段 | 当前含义 |
|---|---|---|
| hardware/v1_2/handoff/mechanical_P5R7.json，motion J5 | B4B-PH-K-S(LF)(SN)，PHR-4，SPH-002T-P0.5S | 保留正式交接原值；板端和胶壳几何没有改 |
| JST PH目录第2页 | SPH002绝缘OD0.8–1.5mm，30–24AWG、0.05–0.22mm² | 当前细线OD0.6604mm低于其目录下限，外径检查FAIL |
| 同页SPH-004T-P0.5S | OD0.5–0.9mm，32–28AWG、0.032–0.08mm² | 当前细线仅OD检查PASS；导体、绝缘、具体压接工具/工艺仍须硬件与线束供应商确认 |
| 同页通用PH端子图 | 名义长5.7mm、横截面2.08×1.5mm | 不是某料号/线材组合的压接后最大外形；无权据此放行真实裸端穿线 |

新离机预装方案需要先装好CAM端，把身体端暂留在PHR-4胶壳外，穿导向/颈部后再入壳。它与此前CAM端先不入壳的装配方案方向不同，完整过线过程尚未验证；供应商制线图必须在最终方案确定后明确标出哪一端不入壳、针腔视图和末端长度基准。

需要硬件任务统一：确切线材/端子组合、PHR-4胶壳匹配、所用压接规范以及裸端最大外形。SPH004为条件比较项，不是本机械任务擅自替换的BOM。

[原厂PH目录](../../supplier_made_harness/recheck_20261004/JST_PH.pdf)（本次读取既有2026-10-04下载文件，第2页）；[来源下载记录](../../supplier_made_harness/recheck_20261004/retrievals.json)。目录图采用PDFium复核，Poppler因缺Adobe-Japan1映射而未正确显示文字，没有根据缺字图认读尺寸。

[局部穿口条件检查](cam_restraints/PH_terminal_gate/review.json)。该结果不会覆盖正式端子选型、实际压接或动态线束验证的BLOCKED/NOT_TESTED状态。
''')
links=''.join(f'<li><a href="{p.relative_to(OUT).as_posix()}">{p.parent.name}：{r["status"]}</a></li>' for p,r in zip(paths,reports))
section=f'''<!-- CAM_BENCH_PROGRESS --><section id="cam-bench"><h2>最新：CAM可先离机固定、剪尾，再带线落座</h2>
<p><strong>夹持座保持现有候选高度。</strong>这次解决了先前“装好后剪钳进不去”的名义操作空间问题：先在离机头托上完成固定和剪尾，再将组件装回。主模型仍为已批准的M1.49 C5＋K1；本研究没有应用C6或线束固定候选。</p>
<table><thead><tr><th>已查范围</th><th>结果与边界</th></tr></thead><tbody>
<tr><td>离机剪尾</td><td>PASS：剪钳作业包络、6种长尾空间；完整机器人作为旁侧障碍保留。工具外形仍有估算。</td></tr>
<tr><td>带线移入头托</td><td>PASS：1363个位置，四根身体端线尾保持松开、举起；线长保持。不是最终已穿好线束的装配检查。</td></tr>
<tr><td>PH裸端局部穿导向</td><td>条件PASS：目录通用5.7×2.08×1.5mm轮廓；三根已穿线临时分两排。实际压接外形、公差仍未确定。</td></tr>
<tr><td>落座后的完整穿线与接插</td><td>NOT_TESTED：仍需完成导向/颈部穿线、自由线形转换、入壳及身体端插合。</td></tr>
<tr><td>正式端子和细线匹配</td><td>BLOCKED：旧交接SPH002的绝缘OD下限0.8mm，大于当前细线0.6604mm。已记录SPH004外径匹配的条件比较，未改BOM。</td></tr>
</tbody></table>
<p>图中的自由线尾延伸出画面，实际名义余线约304～334mm。隐藏外壳仅为看清装配，原生外壳仍包含在移入检查中。短轴、光学件及头壳按明确顺序后装；真实手部和装配力尚未验证。</p>
{figures}<p><a href="CAM_BENCH_SEQUENCE.md">具体工序与未完成项</a> · <a href="CAM_PH_TERMINAL_HANDOFF.md">PH端子交接</a> · <a href="{blend.relative_to(OUT).as_posix()}">可编辑装配研究</a> · <a href="{integrity.relative_to(OUT).as_posix()}">主模型／硬件／STL／视频完整性复核</a></p>
<p>下一步验证落座后的线形转换和完整穿线，再完成身体端固定、其余上端接口及FFC/FPC。完整线束仍为BLOCKED；候选未进入主模型或视频。</p><ul>{links}</ul></section><!-- /CAM_BENCH_PROGRESS -->'''
page=OUT/'index.html';s=page.read_text();s=re.sub(r'<!-- CAM_BENCH_PROGRESS -->.*?<!-- /CAM_BENCH_PROGRESS -->','',s,flags=re.S)
s=s.replace('<h2>最新：CAM导向与夹持候选，装配仍有待解决项</h2>','<h2>此前：CAM导向、夹持与就位剪尾受阻</h2>')
s=s.replace('拟定穿线要求：供应商先不把CAM端端子插入胶壳，穿过颈部及导向后再入壳。','此前研究的穿线方向：CAM端暂不入壳；下方新离机预装研究改查身体端暂不入壳，最终工序尚未确定。')
s=s.replace('</main>',section+'</main>');page.write_text(s)
readme=OUT/'README.md';readme.write_text('''# M1.49线束候选

主模型C5＋K1已经应用。最新进展见index.html#cam-bench与CAM_BENCH_SEQUENCE.md。

CAM离机夹持/剪尾与带自由线尾的头托移入检查通过；后续穿导向、过颈部、整形和端头插合仍未完成。PH通用端子局部穿口条件检查通过，但实际线材/端子选择及压接外形仍需统一。完整线束BLOCKED。

C6、滑动导向、夹持座均未应用到主模型/STL/视频，也没有制造放行。旧候选和失败记录保留。
''')
oldnote=OUT/'CAM_RESTRAINT_PROGRESS.md'
oldtext=oldnote.read_text()
if not oldtext.startswith('> 历史阶段记录'):
 oldnote.write_text('> 历史阶段记录：下文是就位剪尾受阻时的状态。最新离机预装和带线移入已通过所述几何检查，见 [CAM_BENCH_SEQUENCE.md](CAM_BENCH_SEQUENCE.md)；完整后续穿线仍未关闭。\n\n'+oldtext)
state=read(OUT/'continuation_status.json');state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str(page.relative_to(ROOT))+'#cam-bench')
state['upper_current'].update(tool_access='PASS for detached preassembly only; seated17directions remain BLOCKED',
    bench_preassembly='cam_restraints/bench_preassembly_v2/review.json',loose_lead_cradle_transfer='cam_restraints/bench_transfer/review.json',
    PH_local_gate='cam_restraints/PH_terminal_gate/review.json',PH_contact_selection='BLOCKED',restraint_design='BLOCKED pending full wire feed/assembly and approval')
state['next_work']=[
 'C5+K1 are applied. C6 and two restraint print features still need approval; never apply them merely because K1 was approved.',
 'Keep guide_v4 and return_clamp_v3 at Z215. The further+4mm high trial passed motion but did not solve seated cutting; it was not selected.',
 'Detached module+CAM board with exact unchanged port return and equal-length upward body-end free leads passes cutter, all6tail spaces and1363transfer positions. Sources and actual scripts are in upper_connection_commands.json.',
 'Next explicitly thread BODY-side PH free contacts through guide and neck, deform the free leads to final cam_side_fans/c6_join routes, then insert into PHR4 and mate. Later complete feed/form/mate is NOT_TESTED. Do not infer it from the local PH gate or from moving the loose-lead module.',
 'PH_terminal_gate uses vendor family nominal5.7x2.08x1.5mm outline and3temporary two-row wire positions. Real crimped dimensions/tolerances remain unknown; whole temporary-lane transition is untested.',
 'Hardware old handoff J5 listsSPH002 withOD0.8..1.5, while currentCAMroute sampleOD0.6604. SPH004 matchesOD0.5..0.9only, unselected. Reconcile through hardware owner before supplier drawing release; hardware is read-only.',
 'Complete body strain relief, other upper endpoints, FFC/FPC and all wired assembly. Source board estimates, horn/short-shaft evidence and actual physical fit/strength remain separate limits.'
];write(OUT/'continuation_status.json',state)
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in paths+assets+[page,note,handoff,readme,oldnote,integrity,OUT/'upper_connection_commands.json']})
pub.update(utc=now,CAM_bench_preassembly='PASS',CAM_loose_lead_transfer='PASS',CAM_PH_local_gate='PASS',
 CAM_PH_contact_selection='BLOCKED',CAM_restraint_assembly='BLOCKED: later feed/form/mate not checked',full_harness='BLOCKED',
 bench_publisher_sha256=sha(Path(__file__)),bench_publish_command=[sys.executable,*sys.argv])
write(OUT/'publication.json',pub);print('CAM_BENCH_PUBLISHED',len(protected),'protected',len(exports['parts']),'STLs',flush=True)
