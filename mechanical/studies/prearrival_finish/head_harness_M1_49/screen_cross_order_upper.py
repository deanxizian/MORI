"""Screen upper CAM options from a verified local neck, preserving pin identity.

Only curves in this independent study are generated. The existing upper pitch
loops are source-checked references; this individual screen does not prove
that the four fan options can coexist.
"""
from pathlib import Path
import itertools
import json
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
BASE = HERE / 'remaining_routes/left_tall_balanced'
OUT = HERE / 'remaining_routes/cam_cross_order_upper'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT / 'mechanical/scripts'))
sys.path.insert(0, str(HERE))
from harness_context import Context, np, sha
from validate import rigidtr
from upper_curve_geometry import make

ctx = Context()
started = time.time()
lower = json.loads((BASE / 'neck_screen.json').read_text())
upper = json.loads((HERE / 'cam_upper_screen.json').read_text())
old = json.loads((HERE / 'cam_joined_verification.json').read_text())
assert lower['status'] == upper['status'] == old['status'] == 'PASS'
for report, root in [(lower, PROJECT), (upper, HERE), (old, HERE)]:
    for name, digest in report['sources'].items():
        assert sha(PROJECT / name) == digest, name
    for name, digest in report['inputs'].items():
        input_root = PROJECT if name.startswith(('mechanical/', 'config/', 'contracts/', 'hardware/')) else root
        assert sha(input_root / name) == digest, name
lower_file = BASE / 'neck_candidates.npz'
upper_file = HERE / 'cam_upper_candidates.npz'
assert sha(lower_file) == lower['curve_sha256']
assert sha(upper_file) == upper['curve_sha256']
low, loops = np.load(lower_file), np.load(upper_file)
original = ctx.targets
groups = {n: s.group if s.group in ['yaw', 'pitch'] else 'body'
          for n, s in ctx.ss.items()}
targets = {g: {n: t for n, t in original.items() if groups.get(n, 'body') == g}
           for g in ['body', 'yaw', 'pitch']}
rows, arrays, checks = [], {}, 0

for pin in range(1, 5):
    slot = {1:7, 2:10, 3:9, 4:8}[pin]
    start = low[f'z149.0_dip0.6_wire{slot}_y0'][-1]
    anchor = loops[f'slot{pin-1}_pitch0'][0]
    previous = next(r for r in old['selected'] if r['pin'] == pin)
    # Rebuild the old parameter choice from the new start; never reuse another
    # signal's complete curve or change either connector's logical pin number.
    options = [(previous['waypoint_xy_mm'], previous['radius_mm'],
                previous['anchor_trim_mm'], previous['lead_mm'])]
    waypoints = [None, [-9., 7.], [-8., 7.], [-10., 7.], [-12.7, -8.],
                 [-7., 7.], [-6., 7.], [-5., 7.]]
    options.extend((waypoint, radius, trim, lead)
                   for lead, radius, trim, waypoint in itertools.product(
                       [15., 10.5, 0., 6., 3., 12., 9., 16.5, 18., 19.5],
                       [7., 8., 9., 10., 12., 14.], [0., 2., 4.], waypoints))
    accepted, failures, seen = [], [], set()
    accepted_leads = {}
    for waypoint, radius, trim, lead in options:
        identity = (tuple(waypoint) if waypoint else None, radius, trim, lead)
        if identity in seen:
            continue
        seen.add(identity)
        bucket = (tuple(waypoint) if waypoint else None, trim)
        used = accepted_leads.setdefault(bucket, set())
        if len(used) >= 3 or lead in used:
            continue
        end = anchor + [0., 0., trim]
        candidate = make(start, end, radius, lead, waypoint)
        if candidate is None:
            continue
        points, length, error = candidate
        case = dict(pin=pin, radius_mm=radius, lead_mm=lead,
                    anchor_trim_mm=trim, waypoint_xy_mm=waypoint)
        ctx.targets = original
        hit = ctx.clear(points, chord_error=error, radius=.3302)
        checks += 1
        if not hit:
            for group, selected_targets in targets.items():
                ctx.targets = selected_targets
                for yaw in (range(-60, 61, 10) if group == 'body' else [0]):
                    for pitch in (range(-20, 26, 5) if group == 'pitch' else [0]):
                        transform = (np.asarray(rigidtr(yaw, 0)) if group == 'body'
                                     else np.eye(4) if group == 'yaw'
                                     else np.linalg.inv(np.asarray(rigidtr(0, pitch))))
                        q = points @ transform[:3, :3].T + transform[:3, 3]
                        hit = ctx.clear(q, chord_error=error, radius=.3302)
                        checks += 1
                        if hit:
                            hit = dict(hit, group=group, yaw=yaw, pitch=pitch)
                            break
                    if hit:
                        break
                if hit:
                    break
        if hit:
            failures.append(dict(case, **hit))
            continue
        key = f'cross_order_pin{pin}_candidate{len(accepted)}'
        used.add(lead)
        arrays[key] = points
        accepted.append(dict(case, id=key, length_mm=length,
                             chord_error_mm=error, start_mm=start.tolist(),
                             end_mm=end.tolist()))
        print('SWAP_UPPER_OPTION', pin, len(accepted), case, flush=True)
    rows.append(dict(pin=pin, status='PASS' if accepted else 'BLOCKED',
                     candidates=accepted, failures=failures))
    print('SWAP_UPPER_PIN', pin, len(accepted), len(failures), flush=True)

ctx.targets = original
ctx.assert_unchanged()
np.savez_compressed(OUT / 'fan_candidates.npz', **arrays)
inputs = [BASE / 'neck_screen.json', lower_file,
          HERE / 'cam_upper_screen.json', upper_file,
          HERE / 'cam_joined_verification.json', HERE / 'upper_curve_geometry.py']
report = dict(status='PASS' if all(r['candidates'] for r in rows) else 'BLOCKED',
              sources=ctx.sources, rows=rows, checks=checks,
              inputs={str(p.relative_to(PROJECT)): sha(p) for p in inputs},
              curve_sha256=sha(OUT / 'fan_candidates.npz'),
              sampling='Up to three distinct accepted leads per waypoint/trim bucket; avoids keeping only the first unobstructed corridor',
              scope='Individual upper CAM options using the original pin3/4 upper approach lanes and front-left lanes for pin1/2; actual electrical pin identities unchanged, all body routes still unproven',
              required_surface_gap_mm=.3, wire_OD_mm=.6604,
              wire_wire='NOT_TESTED', anchors='NOT_TESTED', full_harness='BLOCKED',
              main_changed=False, supplier_cut_lengths_released=False,
              script_sha256=sha(Path(__file__)), elapsed_s=time.time()-started)
(OUT / 'fan_screen.json').write_text(json.dumps(report, indent=2)+'\n')
print('SWAP_UPPER_DONE', report['status'], report['elapsed_s'], flush=True)
