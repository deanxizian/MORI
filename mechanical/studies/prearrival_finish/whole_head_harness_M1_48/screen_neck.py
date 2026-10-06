"""Current-native, finite family screening before proposing any print change.

Only Yaw_Base and Pitch_Yoke are separately reported as prospective channel
hosts. All other native solids, mating allocations and fixed wires remain
obstacles. No part is edited and no proposed curve is called installed.
"""
from pathlib import Path
import sys, json, time, collections
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent/'outer_harness_M1_48'))
sys.path.insert(0, str(HERE))
from native_context import Context, np, sha
from validate import rigidtr
from neck_family import family, upper, rotate

ctx = Context()
started = time.time()
hosts = {'Yaw_Base', 'Pitch_Yoke'}
native_targets = ctx.targets.copy()
groups = {n: s.group for n, s in ctx.ss.items()}
targets_by_group = {
    group: {n: target for n, target in native_targets.items()
            if n not in hosts and (groups.get(n, 'body') if groups.get(n, 'body') in ['yaw', 'pitch'] else 'body') == group}
    for group in ['body', 'yaw', 'pitch']}
rows, curves, references = [], {}, []
width_source = HERE.parent/'head_harness/split_yaw_space.json'
prior = json.loads(width_source.read_text())
wire_od = next(g['OD'] for g in prior['groups'] if g['id'] == 'SERVO')
required_bend = 14.224 + wire_od/2

# The old four-line middle has a sampled minimum radius of about 7.955 mm.
# A longer common middle is screened explicitly for the other, thicker sample.
# Full port-to-port lengths, endpoint fan-outs and physical wire choice are open.
for bottom in [130., 128., 126.]:
    middle = family(z0=bottom)
    tip, tip_error = upper()
    curve_map = {}
    for row in middle:
        y = row['yaw_deg']
        p = np.vstack([row['points'], rotate(tip, y)[1:]])
        assert np.linalg.norm(row['points'][-1]-rotate(tip, y)[0]) < 1e-9
        key = f'z{int(bottom)}_y{y}'
        curves[key] = p
        curve_map[y] = dict(points=p, error=max(row['chord_error_mm'], tip_error))
    references.append(dict(bottom_z_mm=bottom, top_z_mm=175., radius_mm=7.2,
        middle_length_mm=middle[0]['model_length_mm'],
        maximum_middle_length_variation_mm=max(r['model_length_mm'] for r in middle)-min(r['model_length_mm'] for r in middle),
        sampled_middle_min_radius_mm=min(r['sampled_min_radius_mm'] for r in middle),
        analytic_upper_min_radius_mm=15., required_screen_radius_mm=required_bend))
    assert references[-1]['sampled_middle_min_radius_mm'] >= required_bend
    assert references[-1]['maximum_middle_length_variation_mm'] < 1e-9

    # First isolate the local hardware barrier. Report blockers instead of
    # silently cutting a shaft/servo or replacing one with an empty envelope.
    for angle in range(0, 360, 5):
        hits = []
        checked = 0
        for yaw in range(-60, 61, 10):
            spec = curve_map[yaw]
            p = rotate(spec['points'], angle)
            for pitch in [-20, 0, 25]:
                hit = None
                for group, targets in targets_by_group.items():
                    ctx.targets = targets
                    if group in ['yaw', 'pitch']:
                        tr = np.linalg.inv(np.asarray(rigidtr(yaw, pitch if group == 'pitch' else 0)))
                        local = p @ tr[:3,:3].T + tr[:3,3]
                    else:
                        local = p
                    hit = ctx.clear(local, spec['error'], radius=wire_od/2)
                    if hit:
                        hit['point_frame'] = group + '_zero_pose'
                        break
                checked += 1
                if hit:
                    hits.append(dict(yaw_deg=yaw, pitch_deg=pitch, **hit))
                    break
            if hits:
                break
        rows.append(dict(bottom_z_mm=bottom, zero_angle_deg=angle,
            status='BLOCKED' if hits else 'PASS', tested_poses=checked, hits=hits))
        if angle % 60 == 0:
            print('COMMON_NECK', bottom, angle, 'passes', sum(r['status']=='PASS' for r in rows if r['bottom_z_mm']==bottom), 'seconds', round(time.time()-started,1), flush=True)

ctx.targets = native_targets
ctx.assert_unchanged()
np.savez_compressed(HERE/'screen_curves.npz', **curves)
out = dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Bounded common-neck curve screening only; not a complete eleven-wire installation',
    source_main_sha256=ctx.source_hash, sources=ctx.sources,
    explicit_sample_source=str(width_source.relative_to(PROJECT)), explicit_sample_source_sha256=sha(width_source),
    script_sha256=sha(__file__), curve_helper_sha256=sha(HERE/'neck_family.py'),
    curves_sha256=sha(HERE/'screen_curves.npz'), native_parts=209, mating_allocations=29, existing_static_wires=14,
    wire_OD_mm=wire_od, wire_OD_status='ASSUMED planning allocation; existing 22AWG catalogue sample, not selected USB/SPK/servo wire',
    prospective_channel_hosts=sorted(hosts), host_cuts='NOT_TESTED',
    required_functional_conductors=11, simultaneous_eleven_paths='NOT_TESTED',
    finite_pitch_samples=[-20,0,25], finite_yaw_samples=list(range(-60,61,10)), angle_step_deg=5,
    references=references, rows=rows,
    blockers=dict(collections.Counter(h['object'] for r in rows for h in r['hits'])),
    main_applied=False, whole_harness='BLOCKED', supplier_cut_lengths_released=False, manufacturing_release=False,
    elapsed_s=time.time()-started,
    limitations=['The two named hosts were excluded only to diagnose whether a future channel could help; they are not removed or edited.',
       'Screens are finite pose checks, not continuous flex, strength or fatigue validation.',
       'Lower and upper endpoints are staging coordinates, not connector exits or real anchors.',
       'The old four CAM wires would need new approaches; no compatibility with the previous complete routes is claimed.'])
(HERE/'screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('COMMON_NECK_DONE', out['status'], out['blockers'], round(time.time()-started,1), flush=True)
