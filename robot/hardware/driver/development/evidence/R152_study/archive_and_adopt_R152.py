"""Archive R152 evidence, then adopt verified O into the independent development entry only."""
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source, candidate = dev / 'native', b / 'R152O'
evidence, study = dev / 'evidence/R152O', dev / 'evidence/R152_study'
base = Path('robot/.state/c3-completion/baseline')
backup = Path('robot/.state/c3-completion/baseline_R148E_before_R152O')
board = 'MORI_Interface_C3.kicad_pcb'
old = '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
new = '7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def write(p, data):
    with p.open('x') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


assert sha(source / board) == old and sha(candidate / board) == new
assert not evidence.exists() and not study.exists() and not backup.exists()
result = read(b / 'R152O-verify/result.json')
planned = read(b / 'R152O-planned-delta.json')
reg = read(b / 'R152O-verify/regression.json')
metrics = read(b / 'R152O-local-metrics.json')
inspection = read(b / 'R152O-inspection.json')
assert (result['board_sha256'], result['unconnected_items'], result['violations'], result['schematic_parity'], result['erc_violations']) == (new, 25, 0, 0, 0)
assert planned['status'] == 'PASS' and len(planned['checks']) == 2535 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width']) == 50 and all(x['status'] == 'PASS' for x in reg['power_width'])
assert len(reg['critical_placement']) == 63 and all(x['status'] == 'PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']] == [155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] <= 1e-6 for x in reg['new_copper_review'])
assert sum(x['status'] == 'FAIL' for x in reg['reference_transitions']) == 6
assert metrics['same_face_body_hits'] == 1
assert len(inspection['same_face_nominal_body_intersections']) == 1
assert inspection['same_face_nominal_body_intersections'][0]['reference'] == 'J101'
assert inspection['connectivity']['/01 {slash} Core/BAT_ADC']['candidate'] == [['J101.5', 'R1021.2', 'R1031.1']]
assert not inspection['battery_sampling_chain_complete']
assert all(n in inspection['new_ground_via']['native_contact_layers'] for n in ['F.Cu', 'In1.Cu', 'In4.Cu'])
zone_tests = read(b / 'R152-zone-validation/result.json')
assert zone_tests['status'] == 'PASS' and len(zone_tests['checks']) == 18
assert all(x['status'] == 'PASS' for x in zone_tests['checks'])
members = sorted(p.relative_to(base) for p in base.rglob('*') if p.is_file() and p.name not in [board, 'MORI_Interface_C3.kicad_prl'])
assert len(members) == 77
for p in members:
    assert (base / p).read_bytes() == (source / p).read_bytes() == (candidate / p).read_bytes(), str(p)
all_source = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
old_status = read(dev / 'STATUS.json')
assert old_status['board_sha256'] == old
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
now = datetime.now(timezone.utc).isoformat()
images = read(b / 'R152O-render-manifest.json')['images']
assert len(images) == 15
for row in images:
    assert sha(b / row['png']) == row['png_sha256'] and sha(b / row['svg']) == row['svg_sha256']

evidence.mkdir()
study.mkdir()
for p in (b / 'R152O-verify').iterdir():
    shutil.copy2(p, evidence / p.name)
for src, name in [('R152O-plan.json', 'plan.json'), ('R152O-planned-delta.json', 'planned-delta.json'),
                  ('R152O-local-metrics.json', 'local-metrics.json'), ('R152O-inspection.json', 'inspection.json'),
                  ('R152O-commands.json', 'build_commands.json'), ('R152O-render-manifest.json', 'render-manifest.json')]:
    shutil.copy2(b / src, evidence / name)
(evidence / 'images').mkdir()
for row in images:
    for kind in ['svg', 'png']:
        shutil.copy2(b / row[kind], evidence / 'images' / row[kind])

reviews = {
    'J101': 'The F.Cu BAT_ADC escape goes straight outward from pin 5 through only its nominal housing lip, then turns below the body. Its 0.0762582306 mm2 outside-pad nominal projection is a documented connector escape exception, not zero overlap. Native keepouts are intact. The inner FAULT route passes under the other end of this fixed header with intervening In1 ground. Mating, actual envelope and thermal/EMC qualification remain open.',
    'Q1301': 'The front FAULT branch projects opposite the fixed back AO3400A fault transistor. Intervening In1/In4 reference ground and native clearances were inspected; existing transistor connections are unchanged. Local reference continuity is not switching-coupling or temperature qualification.',
    'R1031': 'The In2 FAULT branch projects below the front 100k battery-divider resistor with intervening In1 ground. The front ADC exits its actual pad outward and no longer grazes the nominal body outside that pad. The replacement ground path reaches an actual stitch contacting both reference planes. Divider settling, injected error and temperature effects remain unqualified.',
    'R1308': 'The bottom-edge front ADC trace projects opposite the fixed back 100k HEAD_UV_N pull-up. In1/In4 ground remains between the faces and all existing pull-up power/ground connectivity is preserved. Reference screening does not establish ADC accuracy or cross-coupling performance.',
    'U1301': 'The front resistor-to-resistor ADC segment projects opposite the fixed back TPS3700DDCR monitor, separated by the reference planes. The monitor connections and neighboring supply widths are unchanged. Transient coupling, sensing accuracy and heat remain unqualified.',
}
projections = sorted({(h['reference'], row['net'], row['layer']) for row in metrics['new_tracks'] for h in row['nominal_body_projections']})
assert all(ref in reviews for ref, net, layer in projections)
visual = {
    'board_sha256': new, 'local_status': 'PASS_WITH_DOCUMENTED_CONNECTOR_ESCAPE',
    'whole_board': 'NOT_TESTED',
    'images_actually_viewed': [{'path': 'images/' + row['png'], 'sha256': row['png_sha256'],
                              'scope': 'Native geometry rendered offline; actually viewed. Six right-side layers, three pin-5 details, four bottom-edge layers and two power-zone comparisons.'} for row in images],
    'findings': [
        'J101.5 now joins R1021.2 and R1031.1 in one BAT_ADC group; R1021.1 to U1001.3 is still open.',
        'No parts move. Twenty-five new segments replace twelve old ones; one new GND via and one 0.08 mm move of an existing HEAD_BUCK_IN via.',
        'The new front ADC route clears the right-side connector guards and its thermal spokes. The bottom run turns outside the nominal housing; one necessary pin-5 outward escape is explicitly recorded.',
        'The upper existing FAULT branch moves to its already-allowed In2 corridor; the lower front detour preserves the original connected FAULT group. Three other FAULT gaps remain.',
        'The HEAD_BUCK_IN In2 allocation grows by exactly 1.65 mm2. Source priority 20, clearance 0.4 mm, fill minimum 0.25 mm, thermal settings and all native rules remain unchanged.',
        'Before/after In2 plots show the north-side power neck restored. The old 0.80/0.40 mm power via moves from (45.4,29.1) to (45.48,29.1), with a rebuilt 0.80 mm back trace to unchanged D901.1.',
        'All 50 supply-width, 155 ground-pad, 63 adjacency and old/new reference checks pass. Ground via (45.65,30) actually contacts F, In1, In4 and B ground. Six historical transition flags remain.',
    ],
    'same_face_exception': inspection['same_face_exception'],
    'same_face_nominal_body_intersections': inspection['same_face_nominal_body_intersections'],
    'projection_review': [{'reference': ref, 'net': net, 'layer': layer, 'review': reviews[ref],
                          'reference_screen': 'PASS', 'coupling_and_thermal': 'NOT_TESTED; local geometry reviewed only.'}
                         for ref, net, layer in projections],
    'limits': ['Nominal Fab/fallback envelopes are not manufacturer maximum or measured body dimensions.',
               'Native plots do not depict every through-hole drill cut distinctly; actual native pad/drill geometry governs.',
               'Local supply width is a geometry screen, not ampacity or thermal qualification.',
               'Whole-board routing style, six historical transitions, parasitics, mechanical fit and physical tests remain open.'],
    'physical': 'NOT_TESTED', 'manufacturing_release': False,
}
write(evidence / 'visual_review.json', visual)
with (evidence / 'remaining_connections.csv').open('x', newline='') as f:
    w = csv.writer(f)
    w.writerow(['item', 'description', 'endpoint_descriptions'])
    for i, x in enumerate(read(evidence / 'drc.json')['unconnected_items'], 1):
        w.writerow([i, x['description'], ' | '.join(y['description'] for y in x['items'])])

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
    payloads.append(dict(path=dest.relative_to(study).as_posix(), sha256=sha(dest),
                         source_sha256=hashlib.sha256(data).hexdigest(), source_bytes=len(data), gzip=compressed))


# Complete native projects and UI/cache extras stay untouched locally. Archive
# original boards, plans, logs, checks, exchange inputs/outputs and settings.
accepted_images = {row[kind] for row in images for kind in ['png', 'svg']}
for p in sorted(b.glob('R152*')):
    if p.is_file():
        if p.name not in accepted_images:
            preserve(p, Path('raw') / p.name)
    elif p.name in ['R152' + x for x in 'BCDEFGHIJKLMNO']:
        preserve(p / board, Path('boards') / (p.name + '.kicad_pcb'))
        for name in ['edit_plan.json', 'edit_manifest.json', 'MORI_Interface_C3.kicad_pro']:
            q = p / name
            if q.is_file() and (name != 'MORI_Interface_C3.kicad_pro' or q.read_bytes() != (source / name).read_bytes()):
                preserve(q, Path('raw') / p.name / name)
        report = b / (p.name + '-drc.json')
        if report.is_file():
            d = read(report)
            trials.append(dict(revision=p.name, board_sha256=sha(p / board), adopted=p.name == 'R152O',
                               status='BUILT_AND_NATIVE_CHECKED',
                               **{k: len(d.get(k, [])) for k in ['unconnected_items', 'violations', 'schematic_parity']}))
        else:
            assert p.name == 'R152K'
            trials.append(dict(revision=p.name, board_sha256=sha(p / board), adopted=False,
                               status='BUILD_REJECTED_BEFORE_SAVE; copied source only, not a built candidate'))
    else:
        for q in sorted(p.rglob('*')):
            if not q.is_file():
                continue
            rel = q.relative_to(b)
            if 'altered-clearance' in rel.parts:
                if q.name not in [board, 'edit_plan.json', 'edit_manifest.json']:
                    continue
            if 'user-data' in rel.parts and q.name != 'freerouting.json':
                continue
            preserve(q, Path('raw') / rel)
preserve(Path(__file__), Path('archive_and_adopt_R152.py'))
write(study / 'summary.json', dict(source_revision='R148E', source_sha256=old,
    adopted_revision='R152O', adopted_sha256=new, candidates=trials,
    unbuilt_proposal='R152A: existing ARMED-group redundancy only; not constructed',
    deliberate_test_fixture='R152-zone-validation/altered-clearance is a rejection test, not an engineering candidate',
    remaining_unconnected_items=25, remaining_connectivity_fraction=.625,
    not_engineering_progress=True, manufacturing_release=False))
write(study / 'archive_manifest.json', {'scope': __doc__, 'payloads': payloads,
    'accepted_images': [{'path': '../R152O/images/' + row[kind], 'sha256': row[kind + '_sha256']}
                        for row in images for kind in ['png', 'svg']],
    'local_only': 'Full unchanged native project copies, KiCad UI files and Freerouting runtime log/cache duplicates; none deleted.'})
for row in payloads:
    p = study / row['path']
    assert sha(p) == row['sha256']
    data = gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['source_sha256']
write(study / 'archive_verification.json', dict(status='PASS', payload_count=len(payloads),
    all_stored_and_original_byte_hashes_match=True, source_local_trials_untouched=True))

# Preserve every native member and UI extra before replacing only the PCB.
shutil.copytree(source, backup, copy_function=shutil.copy2)
assert {p.relative_to(backup).as_posix(): sha(p) for p in backup.rglob('*') if p.is_file()} == all_source
shutil.copy2(candidate / board, source / board)
assert sha(source / board) == new
for rel, digest in all_source.items():
    if rel != board:
        assert sha(source / rel) == digest
write(evidence / 'adoption.json', dict(adopted_at_utc=now, source_commit=commit,
    source_sha256=old, adopted_board_sha256=new, source_full_local_backup=str(backup.absolute()),
    other_native_members_unchanged=77, member_checks=[dict(member=str(p), sha256=sha(source / p)) for p in members],
    development_only=True, published_revision='C3 R108P', adopted_in_main_model=False,
    adopted_in_software=False, engineering_status='FAIL', physical='NOT_TESTED',
    manufacturing_release=False, goal_complete=False))
status = dict(result)
status.update({k: v for k, v in old_status.items() if k.startswith('remaining_')})
status.update(dict(revision='C3 R152O', status='INDEPENDENT_DEVELOPMENT_CANDIDATE',
    published_revision='C3 R108P', adopted_in_main_model=False, previous_candidate='C3 R148E',
    previous_candidate_sha256=old,
    strict_regression_explanation='Raw audit retains FAIL for twelve replaced tracks, one moved non-ground power via and the explicit 1.65 mm2 power allocation expansion. Exact planned-delta review passes 2535 checks; old connections, power, adjacency and reference regression pass. This is local development evidence, not whole-board or physical qualification.',
    step_regression_status='FAIL', planned_delta_review_status='PASS', planned_delta_check_count=2535,
    electrical_regression_status='PASS', local_visual_review='PASS_WITH_DOCUMENTED_CONNECTOR_ESCAPE',
    local_visual_review_explanation='Fifteen local native images actually viewed, including all six right-side layers and power before/after. One explicit J101.5 straight outward housing-lip escape intersects nominal same-face body outside its pad; all native keepouts preserved. Full coupling/thermal and whole-board qualification remain open.',
    whole_board_route_style='NOT_TESTED', new_same_face_nominal_body_projection_groups=1,
    same_face_exception='J101.5 outward escape, nominal outside-pad intersection 0.0762582306 mm2; not measured housing clearance.',
    segment_count=1300, via_count=324, footprint_count=215, baseline_unconnected_items=40,
    remaining_connectivity_fraction=.625, connectivity_fraction_is_not_engineering_progress=True,
    remaining_BAT_ADC_groups=1, remaining_U1001_D1_BAT_ADC_groups=2,
    battery_sampling_chain_complete=False, goal_complete=False))
(dev / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(adopted='R152O', unconnected=25, remaining_fraction=.625,
    exact_plan_checks=2535, archive_payloads=len(payloads), non_pcb_source_members_unchanged=77,
    goal_complete=False)))
