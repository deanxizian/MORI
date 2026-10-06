"""Publish the completed finite checks without promoting candidates to main."""
from pathlib import Path
import datetime,hashlib,html,json,re,sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';VIEW=REST/'threading_review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
names=['threading_formation','threading_formation_v2','threading_descent','contact_corridor','contact_corridor_inward','threading_review']
paths=[REST/n/'review.json' for n in names]+[BASE/'reaction_current/review.json']
reports={p.parent.name:read(p) for p in paths}
for r in reports.values():
    assert not r['main_changed']
    for f,h in {**r['sources'],**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
f=reports['threading_formation_v2'];d=reports['threading_descent'];v=reports['threading_review']
assert f['status']=='PASS' and sum(x['checked'] for x in f['summaries'])==453
assert d['summaries'][0]['status']=='PASS' and d['summaries'][0]['checked']==186
assert v['obstruction']['stored_centerline_points_strictly_inside']==38
receipt=read(BASE/'CAM_PH_RECEIPT.json')
for p,h in receipt['received_files'].items():assert sha(ROOT/p)==h,p
assert receipt['hardware_turn_status']=='COMPLETED'

now=datetime.datetime.now(datetime.timezone.utc).isoformat()
main_delivery=read(HERE.parent/'neck_adoption/delivery.json')
protected=read(HERE.parent/'neck_adoption/approval.json')['protected_hardware']
for p,h in {**main_delivery['files'],**protected}.items():assert sha(ROOT/p)==h,p
exports=read(ROOT/'mechanical/reports/export_manifest.json')
for row in exports['parts']:assert sha(ROOT/'mechanical'/row['file'])==row['sha256']
animation=read(ROOT/'mechanical/animation/delivery.json')
for p,h in animation['files'].items():assert sha(ROOT/'mechanical'/p)==h
integrity=REST/'threading_main_integrity.json'
write(integrity,dict(status='PASS',utc=now,main_changed=False,
    main_sha256=sha(ROOT/'mechanical/mori_v1_2.blend'),config_sha256=sha(ROOT/'config/geometry.json'),
    main_delivery_files_checked=len(main_delivery['files']),protected_hardware_files_checked=len(protected),
    hardware_research_receipt_files_checked=receipt['checked_file_count'],STL_files_checked=len(exports['parts']),
    animation_revision=animation['animation_revision'],animation_files_checked=len(animation['files']),
    script_sha256=sha(Path(__file__))))

note=BASE/'CAM_THREADING_PROGRESS.md'
note.write_text('''# CAM 穿线：已查步骤与两个具体卡点

主模型保持 M1.49 C5＋K1。C6、guide_v4 和 return_clamp_v3 均是未应用的独立候选。
这次没有扩大主模型开口、改变舵机位置或替换端子。

## 已完成

- 硬件 CAM-PH-RECON-R1 已接收，62 个文件哈希通过。Alpha 2841/7＋SPH-004 是硬件此前接收的研究组合；正式 P5R7 仍为 SPH-002。真实压接成品尺寸与工艺未批准。见 [接收说明](CAM_PH_RECEIPT.md)。
- 四根自由线尾的临时停放，以及逐根弯回、移至导向上方 Z270 mm 的 453 个姿态通过名义几何筛选。四条总线长保持，最大离散长度差约 0.000012 mm。采用 R7 mm 的圆弧；这不是线材允许动态弯曲半径或寿命证明。
- 第一根线的名义 PH 端子从 Z270 降到 Z223.85 mm，共 186 个位置通过，包括该步新形状与保留结构、其他参考线的检查。
- 将此前的反力连接问题重新放到当前 M1.49 C5＋K1 上检查：直柄工具仍重叠约 5.837 mm³；反力件上移 2 mm 仍重叠约 18.134 mm³。不能因轴承通道改大就称反力连接已可初装。

## 两个卡点

1. 若每穿完一根就把它整理到最终回弯，下一根端子会被它挡住。第二根端子后端面在 Z252 mm 时，第一根已存储曲线有 38 个中心线点严格位于端子名义盒内；图中红点标出其中一处。这是该顺序的实体交叉证据，不只是保守间距阈值。
2. 裸端子不能直接照抄细导线的最终中心线。沿最终路线推进，四个受限路径分别在约 39.71、38.00、37.49、23.48 mm 处不满足 0.3 mm 检查间距，涉及 Pitch_Yoke 或 Pitch_Servo。另试三种向环形通道中部靠拢的有限路径，仍受反力件或舵机限制。这不能证明所有临时穿入路线都不可能，也不能据此盲目开大孔。

下一步需联合评估：已穿线的临时停放、端子的专用穿入路径，以及反力件的初装顺序。反力件依赖尚未定型的 SCS0009 舵盘／短轴；不能直接删掉它作为无障碍空间。

## 检查边界

- 后续导向／颈部完整穿线、恢复最终线形、入壳、身体端插合与应力释放没有通过；其余上端接口及 FFC/FPC 仍未完成。完整线束为 BLOCKED。
- 453 个姿态按每根线分别检查，前面的线有条件地放在最终位置；并非已证明四根连续依次装入的全过程。
- 5.7×2.08×1.5 mm 只取自 PH 目录通用未压接端子，不是实际已压接端子、锁舌／毛刺／保护件的完整最大包络。当前图中橙色盒仅作候选筛选。
- 临时自由线尾约 304～334 mm 是施工阶段的剩余线长；不是成品中多余垂直长线，也不是供应商裁线长度。
- 有限采样未作为连续软线力学、手部操作、装配力或动态疲劳的证明。夹持、PA12 强度和真实接口仍须实物验证。
- 第一版弯回检查保留为 BLOCKED：原始不等距折线的全局半步长扣减过于保守。v2 只细分未改变的参考折线到最多 0.01 mm；没有缩小线径、放宽间距或修改路径。

[弯回检查](cam_restraints/threading_formation_v2/review.json) · [下穿检查](cam_restraints/threading_descent/review.json) · [最终中心线穿入筛查](cam_restraints/contact_corridor/review.json) · [向内靠拢路径](cam_restraints/contact_corridor_inward/review.json) · [当前反力连接复核](reaction_current/review.json) · [图与交叉点证据](cam_restraints/threading_review/review.json)
''')
assets=[];figures=''
captions={
    'formation.png':'第一根线弯回到导向上方，另外三根暂时举起。图中是施工阶段的长余线，部分线尾超出画面；并非最终装配姿态。',
    'descent_conflict.png':'蓝色：第一根已放好的线。绿色：第二根正在下穿的线。橙色线框：名义端子；红点：前一根线进入端子盒的一处交叉。',
    'neck_corridor_section.png':'托架剖开后查看名义端子的间距不足位置。橙色只是目录轮廓；剖切仅用于看图，实际零件未删改。',
}
for row in v['images']:
    p=VIEW/row['file'];assert sha(p)==row['sha256'];assets.append(p)
    figures+=f'<figure><img src="{p.relative_to(BASE).as_posix()}" style="width:100%" alt="{html.escape(captions[p.name])}"><figcaption>{captions[p.name]}</figcaption></figure>'
blend=VIEW/'MORI_M1_49_CAM_threading_review.blend';assert sha(blend)==v['blend_sha256'];assets.append(blend)
links=''.join(f'<li><a href="{p.relative_to(BASE).as_posix()}">{p.parent.name}: {read(p)["status"]}</a></li>' for p in paths)
section=f'''<!-- CAM_THREADING_PROGRESS --><section id="cam-threading"><h2>当前：临时弯回通过，完整穿线仍有两处卡点</h2>
<p>主模型仍为已批准的 M1.49 C5＋K1。新检查没有改变主模型、STL 或装配视频，也没有将 C6 和固定座候选应用进去。</p>
<table><thead><tr><th>范围</th><th>结果</th></tr></thead><tbody>
<tr><td>自由线尾停放／弯回</td><td>453 个有限姿态 PASS，四根线长度保持；逐根有条件检查，不等于整套顺序通过。</td></tr>
<tr><td>第一根端子下穿导向</td><td>186 个位置 PASS，仅针对目录名义轮廓。</td></tr>
<tr><td>后续端子与已放线</td><td>BLOCKED：先整理好的回弯挡住后一根端子；已保存明确交叉点。</td></tr>
<tr><td>直接沿最终线形穿颈</td><td>BLOCKED：受托架／舵机限制。向通道中部靠拢的有限备选也未通过；需重新安排临时穿入路径和反力件初装。</td></tr>
<tr><td>PH 线材／端子资料</td><td>硬件资料已接收，实际压接包络与工艺仍 BLOCKED。正式 BOM 未替换。</td></tr>
</tbody></table>
<p>后续工作还包括身体端固定、其余上端接口、FFC/FPC 和完整带线装配。图中的端子形状、有限采样以及无软线的装配检查，都不能当作实物合格或制造放行。</p>
{figures}<p><a href="CAM_THREADING_PROGRESS.md">具体步骤与限制</a> · <a href="CAM_PH_RECEIPT.md">硬件资料接收</a> · <a href="CAM_PH_RECEIPT.json">接收校验</a> · <a href="{blend.relative_to(BASE).as_posix()}">可编辑 Blender 局部检查</a> · <a href="{integrity.relative_to(BASE).as_posix()}">主模型／硬件／STL／视频保留检查</a></p><ul>{links}</ul></section><!-- /CAM_THREADING_PROGRESS -->'''
page=BASE/'index.html';text=page.read_text()
text=re.sub(r'<!-- CAM_THREADING_PROGRESS -->.*?<!-- /CAM_THREADING_PROGRESS -->','',text,flags=re.S)
text=text.replace('<h2>最新：CAM可先离机固定、剪尾，再带线落座</h2>','<h2>此前：CAM离机固定、剪尾与带线落座</h2>')
text=text.replace('</main>',section+'</main>');page.write_text(text)
readme=BASE/'README.md';readme.write_text('''# M1.49 线束候选

主模型 C5＋K1 已应用。最新检查见 [穿线进展](index.html#cam-threading) 和 [具体说明](CAM_THREADING_PROGRESS.md)。

离机固定、带自由线尾落座、临时弯回和第一根名义端子下穿分别通过各自检查；后续端子被已放线挡住，直接沿最终曲线穿颈的受限路线也未通过。完整线束仍为 BLOCKED。

硬件 CAM-PH-RECON-R1 已接收；真实压接成品包络与工艺仍待确定。C6、导向与夹持座未应用，主模型／STL／视频未变，没有制造放行。
''')
state=read(BASE/'continuation_status.json')
state.update(utc=now,active_processes=[],review_url='http://127.0.0.1:58201/'+str(page.relative_to(ROOT))+'#cam-threading')
state['CAM_threading_current']=dict(formation='PASS',formation_sample_count=453,first_contact_descent='PASS',first_contact_samples=186,
    full_sequence='BLOCKED',actual_crimped_envelope='BLOCKED',
    reports=[str(p.relative_to(BASE)) for p in paths],note=note.name,
    obstruction='Earlier final-position CAM service loop intersects later nominal PH contact; restricted neck feed paths not accepted',
    main_changed=False,C6_main_applied=False)
state['hardware_follow_up'].update(status='COMPLETED_RECEIVED',receipt='CAM_PH_RECEIPT.json',revision=receipt['hardware_revision'],
    response_received=True,formal_BOM_changed=False,actual_crimped_envelope='BLOCKED',
    scope='User-authorized research handoff completed and received; no pending response, no formal substitution or supplier contact')
state['next_work']=[
    'C5+K1 are applied. C6 and restraint features are not approved; do not apply them with K1 authorization.',
    'Keep the passed bench preassembly, loose-lead module transfer and above-head formation as separate, scoped stages.',
    'Do not finalize each CAM return immediately after feeding: the stored earlier loop intersects the next nominal contact. Develop complete temporary parking and restoration, not just a local two-row gate.',
    'Restricted final-centreline and inward-biased PH feed paths fail. Jointly evaluate temporary contact paths and reaction-link preassembly. Never omit the link without an explicit staged assembly proof.',
    'Hardware CAM-PH-RECON-R1 received; formal SPH002 unchanged, SPH004 plus Alpha2841/7 only research. Exact crimp/protection envelope needs manufacturer or qualified supplier data.',
    'Current M1.49 recheck still fails the provisional straight reaction tool and 2mm link lift. SCS0009 matching horn/shaft remains a separate evidence dependency.',
    'Complete body strain relief, other upper endpoints, FFC/FPC, complete wired assembly and supplier drawings; physical strength and fit remain separate.'
]
write(BASE/'continuation_status.json',state)
pub=read(BASE/'publication.json');assert not pub['C6_approved']
assert pub['source_blend_sha256']==sha(ROOT/'mechanical/mori_v1_2.blend')
pub['files'].update({str(p.relative_to(ROOT)):sha(p) for p in paths+assets+[note,page,readme,integrity,BASE/'CAM_PH_RECEIPT.json',BASE/'CAM_PH_RECEIPT.md',BASE/'upper_connection_commands.json']})
pub.update(utc=now,CAM_free_end_formation='PASS',CAM_first_contact_descent='PASS',CAM_full_contact_feed='BLOCKED',
    CAM_PH_hardware_receipt='PASS',CAM_PH_contact_selection='BLOCKED',CAM_restraint_assembly='BLOCKED',
    full_harness='BLOCKED',reaction_current='BLOCKED',threading_publisher_sha256=sha(Path(__file__)),
    input_receipt_refresh='Receipt repeated once before publication and changed its timestamp. Made receipt idempotent and reran dependent descent, corridor and review checks against the final receipt; no input-hash waiver.',
    threading_publish_command=[sys.executable,*sys.argv])
write(BASE/'publication.json',pub)
print('CAM_THREADING_PUBLISHED',len(protected),'protected',len(exports['parts']),'STLs',flush=True)
