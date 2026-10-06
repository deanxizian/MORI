"""Rejoin a verified lower nine-wire proposal to the unchanged CAM upper loops.

The existing four upper loops are reused only after source hashes and the
original joined-prefix coordinates match. No upper servo/USB/speaker endpoint,
anchor, wire selection or installation sequence is approved by this check.
"""
from pathlib import Path
import sys, json, time, itertools

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
variant = next((v.split('=', 1)[1] for v in sys.argv if v.startswith('--route-set=')), 'nine_higher')
assert variant in ['nine_higher', 'nine_higher_directed', 'nine_higher_stagger', 'nine_higher_lift']
BASE = HERE / 'remaining_routes' / variant / 'combined'
OUT = BASE / 'cam_rejoined'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
sys.path.insert(0, str(HERE))
from harness_context import Context, np, sha
from curve_clearance import prepared, self_clear
from bounded_curve_checks import pair_threshold
from validate import rigidtr

ctx = Context()
started = time.time()
read = lambda p: json.loads(p.read_text())
new_report = read(BASE / 'lower_nine_screen.json')
old_report = read(HERE / 'cam_joined_verification.json')
old_lower_report = read(HERE / 'front_lower_verification.json')
lane_path = HERE / 'remaining_routes/higher_entry/neck_screen.json'
lane_report = read(lane_path)
assert new_report['status'] == old_report['status'] == old_lower_report['status'] == 'PASS'
for report in [new_report, old_report, old_lower_report, lane_report]:
    for name, digest in report['sources'].items():
        assert sha(PROJECT / name) == digest, name
for report, root in [(new_report, PROJECT), (old_report, HERE),
                     (old_lower_report, HERE), (lane_report, PROJECT)]:
    for name, digest in report['inputs'].items():
        assert sha(root / name) == digest, name

new_file = BASE / 'lower_nine_candidates.npz'
old_file = HERE / 'cam_joined_candidates.npz'
old_lower_file = HERE / 'front_lower_curves.npz'
neck_file = HERE / 'remaining_routes/higher_entry/neck_candidates.npz'
for file, report in [(new_file, new_report), (old_file, old_report),
                     (old_lower_file, old_lower_report), (neck_file, lane_report)]:
    assert sha(file) == report['curve_sha256'], str(file)
low = np.load(new_file)
old = np.load(old_file)
old_low = np.load(old_lower_file)
neck = np.load(neck_file)
lane = next(r for r in lane_report['results'] if r['z0_mm'] == new_report['z0_mm'])
assert lane['status'] == 'PASS'
selected = {r['endpoint']: r for r in new_report['selected']}
spare_slots = sorted(set(range(11)) - {r['slot'] for r in selected.values()})
assert len(spare_slots) == 2
assert len(new_report['whole_pairs']) == 715
assert all(r['status'] == 'PASS' for r in new_report['whole_pairs'])

checks, selves, joins, failures, values = [], [], [], [], {}
joined = {}
upper_by_pitch = {}
for pin, pitch in itertools.product(range(1, 5), range(-20, 26, 5)):
    prefix = old_low[f'pin{pin}_y0']
    whole = old[f'pin{pin}_y0_p{pitch}']
    assert np.array_equal(whole[:len(prefix)], prefix), (pin, pitch)
    suffix = whole[len(prefix) - 1:]
    upper_by_pitch[pin, pitch] = suffix

for yaw in range(-60, 61, 10):
    tr = np.asarray(rigidtr(yaw, 0))
    inv = np.linalg.inv(tr)
    raw_lower, lower_items = {}, {}
    for name, row in selected.items():
        points = low[name + f'_y{yaw}']
        points = points @ inv[:3, :3].T + inv[:3, 3]
        raw_lower[name] = points
        lower_items[name] = prepared(points, row['OD_mm'] / 2,
                                    max(row['chord_error_mm'], lane['chord_error_mm']))
    for slot in spare_slots:
        points = neck[f'z{new_report["z0_mm"]}_wire{slot}_y{yaw}']
        points = points @ inv[:3, :3].T + inv[:3, 3]
        name = 'SPK_reservation_' + str(slot)
        raw_lower[name] = points
        lower_items[name] = prepared(points, .5842, lane['chord_error_mm'])

    for pin, pitch in itertools.product(range(1, 5), range(-20, 26, 5)):
        name = 'CAM_' + str(pin)
        old_prefix = old_low[f'pin{pin}_y{yaw}']
        old_whole = old[f'pin{pin}_y{yaw}_p{pitch}']
        assert np.array_equal(old_whole[:len(old_prefix)], old_prefix)
        suffix = old_whole[len(old_prefix) - 1:]
        upper = upper_by_pitch[pin, pitch]
        assert np.allclose(suffix, upper @ tr[:3, :3].T + tr[:3, 3], atol=1e-8, rtol=0)
        prefix = raw_lower[name]
        error = float(np.linalg.norm(prefix[-1] - upper[0]))
        assert error < 1e-8, (pin, yaw, pitch, error)
        a = prefix[-1] - prefix[-2]
        b = upper[1] - upper[0]
        tangent_cosine = float(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b))
        assert tangent_cosine > .9999, (pin, yaw, tangent_cosine)
        joins.append(dict(pin=pin, yaw=yaw, pitch=pitch, error_mm=error,
                          sampled_tangent_cosine=tangent_cosine))
        full = np.vstack([prefix, upper[1:]])
        result = self_clear(prepared(full, .3302,
                                    max(lower_items[name]['error'], .0003)))
        selves.append(dict(pin=pin, yaw=yaw, pitch=pitch, **result))
        if result['status'] != 'PASS':
            failures.append(dict(kind='self', **selves[-1]))
        upper_item = prepared(upper, .3302, .0003)
        for other, lower_item in lower_items.items():
            if other == name:
                continue
            result = pair_threshold(upper_item, lower_item)
            row = dict(CAM_pin=pin, lower=other, yaw=yaw, pitch=pitch, **result)
            checks.append(row)
            if result['status'] != 'PASS':
                failures.append(dict(kind='upper_to_lower', **row))
        world = full @ tr[:3, :3].T + tr[:3, 3]
        joined[f'pin{pin}_y{yaw}_p{pitch}'] = world
        length = float(np.linalg.norm(np.diff(world, axis=0), axis=1).sum())
        values.setdefault(pin, []).append(length)
    print('HIGHER_CAM_YAW', yaw, 'failures', len(failures), flush=True)

ctx.assert_unchanged()
success = not failures and len(checks) == 5200 and len(selves) == len(joins) == 520
if success:
    np.savez_compressed(OUT / 'cam_joined_candidates.npz', **joined)
inputs = [BASE / 'lower_nine_screen.json', new_file,
          HERE / 'cam_joined_verification.json', old_file,
          HERE / 'front_lower_verification.json', old_lower_file, lane_path,
          neck_file, HERE / 'curve_clearance.py', HERE / 'bounded_curve_checks.py']
report = dict(
    status='PASS' if success else 'BLOCKED', sources=ctx.sources,
    inputs={str(p.relative_to(PROJECT)): sha(p) for p in inputs},
    joins=joins, self_checks=selves, upper_lower_checks=checks, failures=failures,
    lengths=[dict(pin=pin, minimum_polygon_length_mm=min(v),
                  maximum_polygon_length_mm=max(v), variation_mm=max(v)-min(v),
                  not_supplier_cut_length=True) for pin, v in values.items()],
    scope='Four continuous CAM routes together with five lower power/servo routes and two local speaker reservations; finite nominal geometry only',
    proof_reuse='Exact unchanged old CAM upper coordinates, native source hashes and prior joined proof; lower nine and eleven local-wire checks from new report. New upper/lower and whole-CAM self checks are explicit here.',
    clearance_rule_mm=.3, complete_CAM_curves=len(joined) if success else 0,
    curve_sha256=sha(OUT/'cam_joined_candidates.npz') if success else None,
    main_changed=False, full_harness='BLOCKED', remote_endpoints='BLOCKED',
    anchors='NOT_TESTED', wired_assembly='NOT_TESTED', physical_qualification='NOT_TESTED',
    supplier_cut_lengths_released=False, script_sha256=sha(Path(__file__)),
    elapsed_s=time.time()-started)
(OUT/'cam_joined_screen.json').write_text(json.dumps(report, indent=2)+'\n')
print('HIGHER_CAM_DONE', report['status'], report['elapsed_s'], flush=True)
