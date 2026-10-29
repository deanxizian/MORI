"""Preserve R148 studies and adopt verified E PCB into independent development only."""
import csv, gzip, hashlib, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source, candidate = dev / 'native', b / 'R148E'
evidence, study = dev / 'evidence/R148E', dev / 'evidence/R148_study'
base = Path('robot/.state/c3-completion/baseline')
backup = Path('robot/.state/c3-completion/baseline_R147L_before_R148E')
board = 'MORI_Interface_C3.kicad_pcb'
old = '6816b9c5783e5a699f5d3f1d0d102914269d37d6d756ef5158ed1b0b3fa129b6'
new = '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
def write(p, data):
    with p.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

assert sha(source / board) == old and sha(candidate / board) == new
assert not evidence.exists() and not study.exists() and not backup.exists()
result = read(b / 'R148E-verify/result.json')
planned = read(b / 'R148E-planned-delta.json')
reg = read(b / 'R148E-verify/regression.json')
metrics = read(b / 'R148E-local-metrics.json')
inspection = read(b / 'R148E-inspection.json')
assert (result['board_sha256'], result['unconnected_items'], result['violations'], result['schematic_parity'], result['erc_violations']) == (new, 26, 0, 0, 0)
assert planned['status'] == 'PASS' and len(planned['checks']) == 2528 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width']) == 50 and all(x['status'] == 'PASS' for x in reg['power_width'])
assert len(reg['critical_placement']) == 63 and all(x['status'] == 'PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']] == [155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] <= 1e-6 for x in reg['new_copper_review'])
assert sum(x['status'] == 'FAIL' for x in reg['reference_transitions']) == 6
assert metrics['same_face_body_hits'] == 0 and not inspection['same_face_nominal_body_intersections']
assert inspection['gate_groups'] == [['D1602.1', 'Q1601.4', 'Q1602.4', 'R1601.1', 'U1601.6']]
members = sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and p.name not in [board, 'MORI_Interface_C3.kicad_prl'])
assert len(members) == 77
for p in members:
    assert (base / p).read_bytes() == (source / p).read_bytes() == (candidate / p).read_bytes(), str(p)
all_source = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
old_status = read(dev / 'STATUS.json')
assert old_status['board_sha256'] == old
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
now = datetime.now(timezone.utc).isoformat()

# These ten PNGs were actually viewed, including the full WDI approach in detail.
overview = ['F.Cu', 'B.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'R147L-B.Cu', 'R147L-In3.Cu']
images = [('images/' + n + '.png', b / 'R148E-views' / (n + '.png')) for n in overview]
images += [('details/' + n + '.png', b / 'R148E-detail-views' / (n + '.png')) for n in ['F.Cu', 'B.Cu']]
assert all(p.is_file() for _, p in images)
evidence.mkdir()
study.mkdir()
for p in (b / 'R148E-verify').iterdir():
    shutil.copy2(p, evidence / p.name)
for src, name in [('R148E-plan.json', 'plan.json'), ('R148E-planned-delta.json', 'planned-delta.json'), ('R148E-local-metrics.json', 'local-metrics.json'), ('R148E-inspection.json', 'inspection.json'), ('R148E-commands.json', 'build_commands.json')]:
    shutil.copy2(b / src, evidence / name)
shutil.copytree(b / 'R148E-views', evidence / 'images')
shutil.copytree(b / 'R148E-detail-views', evidence / 'details')

review_by_ref = {
    'C1003': 'The rerouted inner clamp branch projects below the slightly translated back-face bypass capacitor. Intervening In4 ground and the short restored 3V3 feed were checked; all 50 power-width screens and capacitor ground connectivity remain intact. Actual supply noise and temperature remain unqualified.',
    'J102': 'WDI leaves the unchanged front-mounted through-hole header on the back face and runs directly between actual pad centres. Intervening ground and native hole/land clearances were checked; the header and mating geometry were not moved or qualified.',
    'Q1601': 'Back gate copper and the inner clamp branch project opposite the fixed front power MOSFET. Existing source/drain copper is preserved and In1/In4 ground geometry was inspected. A ground-reference screen is not high-side GATE-to-SOURCE switching-loop or thermal qualification.',
    'Q1602': 'The back/inner clamp branch projects opposite the fixed front MOSFET. The new front gate escape leaves pad 4 outward without entering the nominal body; original source/drain copper and reference coverage remain intact. Drain coupling, gate transients and temperature are not qualified.',
    'R1001': 'The inner clamp branch passes beneath the fixed back-face resistor with intervening In4 reference ground. Existing resistor pads, nets and adjacent routes are preserved. The local geometric separation does not establish noise or thermal performance.',
    'U1001': 'The inner clamp branch remains beneath the fixed back-face ADC switch, separated by In4 ground. Old ADC connections, reference coverage and the nearby C1003 feed remain intact. Clamp-to-ADC coupling and dynamic measurement error remain open.',
    'U1601': 'The back-face clamp branch extends opposite the fixed front gate controller, with continuous In4 reference. Existing controller connections are preserved. Controller noise, switching waveforms and thermal behavior remain unqualified.',
}
projections = sorted({(h['reference'], row['net'], row['layer']) for row in metrics['new_tracks'] for h in row['nominal_body_projections']})
assert all(ref in review_by_ref for ref, net, layer in projections)
visual = {
    'board_sha256': new, 'local_status': 'PASS', 'whole_board': 'NOT_TESTED',
    'images_actually_viewed': [{'path': rel, 'sha256': sha(p), 'scope': 'Native geometry rendered in separate processes; actually viewed for local routing/reference review.'} for rel, p in images],
    'findings': [
        'Q1602.4 now joins Q1601.4, U1601.6, D1602.1 and R1601.1 in one ACT_GATE group.',
        'C1003 moves left 0.15 mm and R303 up 0.35 mm without rotation; their owner guards follow the explicit plan.',
        'A former clamp via is explicitly reassigned and moved to gate (37.2,7.3); a new clamp via is at (36.54,7.55). No ground via moves.',
        'The front gate approach uses one outward escape and deliberate bends to avoid source copper and the actual merged reference-plane void. No new same-face nominal body hit remains.',
        'The inner clamp detour preserves filled 3V3 corridors and reference ground; native fill minimum thickness matters in addition to trace clearance.',
        'WDI uses a single direct pad-centre segment; the tiny rounded-pad/body intersection in candidate D is eliminated.',
        'All original connections, 50 power-width, 155 ground-pad and 63 adjacency screens remain valid. Six historical transition flags remain.',
    ],
    'projection_review': [{'reference': ref, 'net': net, 'layer': layer, 'review': review_by_ref[ref], 'reference_screen': 'PASS', 'coupling_and_thermal': 'NOT_TESTED; local geometry reviewed, full engineering qualification remains open.'} for ref, net, layer in projections],
    'limits': ['Nominal Fab/fallback bodies are not manufacturer maximum or measured envelopes.', 'Whole-board review, GATE/SOURCE dynamics, parasitics, heat and physical assembly remain unfinished.', 'The 2 mm return-via criterion is a project screen, not EMC qualification.'],
    'physical': 'NOT_TESTED', 'manufacturing_release': False,
}
write(evidence / 'visual_review.json', visual)
with (evidence / 'remaining_connections.csv').open('x', newline='') as f:
    w = csv.writer(f)
    w.writerow(['item', 'description', 'endpoint_descriptions'])
    for i, x in enumerate(read(evidence / 'drc.json')['unconnected_items'], 1):
        w.writerow([i, x['description'], ' | '.join(y['description'] for y in x['items'])])

# Preserve reports, failed boards and diagnostics; full trial projects remain untouched locally.
payloads, trials = [], []
def preserve(src, rel):
    data = src.read_bytes()
    compressed = src.suffix == '.kicad_pcb' or len(data) > 524288
    dest = study / rel
    if compressed:
        dest = dest.with_name(dest.name + '.gz')
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
    payloads.append(dict(path=dest.relative_to(study).as_posix(), sha256=sha(dest), source_sha256=hashlib.sha256(data).hexdigest(), source_bytes=len(data), gzip=compressed))
for p in sorted(b.glob('R148*')):
    if p.is_file():
        preserve(p, Path('raw') / p.name)
    elif p.name in ['R148' + x for x in 'ABCDE']:
        preserve(p / board, Path('boards') / (p.name + '.kicad_pcb'))
        d = read(b / (p.name + '-drc.json'))
        trials.append(dict(revision=p.name, board_sha256=sha(p / board), adopted=p.name == 'R148E', **{k: len(d.get(k, [])) for k in ['unconnected_items', 'violations', 'schematic_parity']}))
    else:
        for q in sorted(p.rglob('*')):
            if q.is_file():
                preserve(q, Path('raw') / q.relative_to(b))
preserve(Path(__file__), Path('archive_and_adopt_R148.py'))
write(study / 'summary.json', dict(source_revision='R147L', source_sha256=old, adopted_revision='R148E', adopted_sha256=new, candidates=trials, remaining_unconnected_items=26, remaining_connectivity_fraction=.65, not_engineering_progress=True, manufacturing_release=False))
write(study / 'archive_manifest.json', {'scope': __doc__, 'payloads': payloads})
for row in payloads:
    p = study / row['path']
    assert sha(p) == row['sha256']
    data = gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['source_sha256']
write(study / 'archive_verification.json', dict(status='PASS', payload_count=len(payloads), all_stored_and_original_byte_hashes_match=True, source_local_trials_untouched=True))
(study / 'README.md').write_text('''# R148：补接 Q1602 栅极并保留供电与参考地

仅 E 采用到独立开发入口：27 → **26 项未连接**，相对最初 40 项剩 **65%**。发布仍 R108P；该比例不是工程或时间完成率。

- 固定布局有限网格搜索没有通路，随后联合调整 C1003、R303、D1001 K 支路和换层孔；搜索无路径不证明不可布通。
- A 为 27 opens / 2 other DRC，并破坏 3.3 V 和旧参考地。B 虽 0 other DRC，仍割裂 3.3 V；内层填铜最小厚度不能忽略。均未采用。
- C 恢复供电并降到 26 opens，但新铜仍有三处实际参考地缺口。未扩大容差或删除缺口；D 改走向后消除它们。
- D 的电气回归通过，但 WDI 在圆角焊盘之外擦过 R303 名义本体约 0.000006417 mm²，未采用。E 用实际焊盘中心间单段直线消除这处问题。
- E 的原生 DRC/ERC、2528 项精确计划核对、50 供电铜宽、155 GND、63 邻接及新旧参考地通过；六层局部图、前后对比和 WDI/门极细节共十张图已实际查看。

[接收证据](../R148E/README.md)与本目录保留原生板、失败输出、计划、命令和诊断脚本；大文件使用 gzip，manifest 同时验证压缩文件和原字节哈希。完整试验工程仍在本机 `.state`，没有清理或覆盖失败源文件。

6 项历史回流提示、全板逐线逐孔、电源/热/耦合、机械/线束与实物资格仍未完成。没有制造导出、设备操作或发布合并。
''')

# Back up every existing native member and UI extra, then replace only the PCB.
shutil.copytree(source, backup, copy_function=shutil.copy2)
assert {p.relative_to(backup).as_posix(): sha(p) for p in backup.rglob('*') if p.is_file()} == all_source
shutil.copy2(candidate / board, source / board)
assert sha(source / board) == new
for rel, digest in all_source.items():
    if rel != board:
        assert sha(source / rel) == digest
write(evidence / 'adoption.json', dict(adopted_at_utc=now, source_commit=commit, source_sha256=old, adopted_board_sha256=new, source_full_local_backup=str(backup.absolute()), other_native_members_unchanged=77, member_checks=[dict(member=str(p), sha256=sha(source / p)) for p in members], development_only=True, published_revision='C3 R108P', adopted_in_main_model=False, adopted_in_software=False, engineering_status='FAIL', physical='NOT_TESTED', manufacturing_release=False, goal_complete=False))
status = dict(result)
status.update({k: v for k, v in old_status.items() if k.startswith('remaining_')})
status.update(dict(revision='C3 R148E', status='INDEPENDENT_DEVELOPMENT_CANDIDATE', published_revision='C3 R108P', adopted_in_main_model=False, previous_candidate='C3 R147L', previous_candidate_sha256=old, strict_regression_explanation='Raw audit retains FAIL for two explicit part translations and owner guards, ten replaced tracks and one reassigned/moved non-ground via. Exact planned-delta review passes 2528 checks; old connections, power, adjacency and reference regression pass. This is local development evidence, not whole-board or physical qualification.', step_regression_status='FAIL', planned_delta_review_status='PASS', planned_delta_check_count=2528, electrical_regression_status='PASS', local_visual_review='PASS', local_visual_review_explanation='Six local layers, two source comparisons and two pad/gate details actually viewed. Zero new same-face nominal body hits; thermal/coupling and whole-board qualification remain open.', whole_board_route_style='NOT_TESTED', new_same_face_nominal_body_projection_groups=0, segment_count=1287, via_count=323, footprint_count=215, baseline_unconnected_items=40, remaining_connectivity_fraction=.65, connectivity_fraction_is_not_engineering_progress=True, remaining_ACT_GATE_groups=1, goal_complete=False))
(dev / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
(evidence / 'README.md').write_text('''# C3 R148E 独立开发接收

2026-10-27：已采用到 `development/native`，**26 项未连接、0 其他 DRC、0 图板差异、0 启用项 ERC**。相对原 40 项消除 14 项，剩余连通数量比例 **65%**；工程仍 FAIL / PROTOTYPE / UNVALIDATED。发布仍 R108P，机械与软件未采用，不可制造。

PCB SHA256：`958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1`。

Q1602.4 接入 Q1601.4、U1601.6、D1602.1、R1601.1 的 ACT_GATE 组。C1003 左移 0.15 mm，R303 上移 0.35 mm，均保留朝向；原 K 支路孔显式改网并移至门极 `(37.2,7.3)`，新 K 孔位于 `(36.54,7.55)`。精确替换 10 段旧铜、新增 19 段，共 1287 段 / 323 孔 / 215 器件。固定接口、电路、源漏铜、全部地孔、原生规则及 77 非 PCB 文件保持。

- [原生结果](result.json)、[验证命令](commands.json)、[构建命令](build_commands.json)。
- [2528 项精确差异核对](planned-delta.json)、[原始回归](regression.json)：原连接、50 供电铜宽、155 GND、63 邻接和新旧参考地通过；严格几何审计仍保留显式修改的 FAIL。
- [实际查看的局部图与逐项投影审查](visual_review.json)、[逐段几何](local-metrics.json)、[剩余连接](remaining_connections.csv)、[原字节/备份记录](adoption.json)。
- 新门极换参考面附近地孔距离约 0.914 mm，满足项目几何筛查；不是高边 GATE-SOURCE 回路或 EMC 资格。原 6 项历史换层提示仍在。

[A–D 失败资料](../R148_study/README.md)完整保留。全板、动态/寄生/热、机械/线束及实物资格仍未完成；接通门极网络不表示整个保护电路已经验证。
''')
print(json.dumps(dict(adopted='R148E', unconnected=26, remaining_fraction=.65, exact_plan_checks=2528, archive_payloads=len(payloads), non_pcb_source_members_unchanged=77, goal_complete=False)))
