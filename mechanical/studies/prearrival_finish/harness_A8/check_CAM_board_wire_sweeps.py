"""Bound continuous CAM mating/seating wire-to-solid clearances.

The candidate geometry is unchanged. Split the wire into an unchanged upper
straight, a narrowing core, an exact union of connector departure straights,
and nested fixed tail portions. Conservative distance bounds cover every h
between 0 and 6 mm, not just the earlier sixteen configurations.
"""
from pathlib import Path
WS_SCRIPT = Path(__file__).resolve()
WS_ROOT = WS_SCRIPT.parent
WS_HELPER = WS_ROOT / 'check_CAM_board_last.py'
__file__ = str(WS_HELPER)
exec(compile(WS_HELPER.read_text().split("\nif __name__=='__main__':", 1)[0], str(WS_HELPER), 'exec'), globals())
__file__ = str(WS_SCRIPT)
WS_OUT = WS_ROOT / 'cam_board_last'
ws_start = time.time()
ws_screen = json.loads((WS_OUT / 'screen.json').read_text())
assert ws_screen['status'] == 'PASS'
ws_D = 1. + math.pi / 2.
ws_core_speed = 1. / ws_D
ws_grip_core = {'Pitch_Yoke', 'CAM_Tie_Head', 'CAM_Tie_Band'}
ws_grip_tail = {'CAM_catalogue_housing', 'CAM_UART_4P', 'Pitch_Cradle',
                'CAM_connector_tie_head', 'CAM_connector_tie_band'}
ws_passed = []
ws_unproved = []
ws_tested = 0


def ws_span_check(points, error, target, contact, slot):
    name, group, m, lo, hi, tree = target
    keep = np.ones(len(points), dtype=bool)
    if contact == 'core' and name in ws_grip_core:
        keep &= ~((abs(points[:, 0] - xx[slot]) < 1e-5)
                  & (abs(points[:, 1] + 1.5) < 1e-5)
                  & (points[:, 2] <= 234.3 + 1e-5)
                  & (points[:, 2] >= 229.9 - 1e-5))
    if contact == 'tail' and name in ws_grip_tail:
        keep &= ~((abs(points[:, 0] - slots[slot, 0]) < 1e-5)
                  & (abs(points[:, 1] - slots[slot, 1]) < 1e-5)
                  & (points[:, 2] >= slots[slot, 2] - 5. - 1e-5)
                  & (points[:, 2] <= slots[slot, 2] + 1e-5))
    ids = np.flatnonzero(keep)
    for span in np.split(ids, np.flatnonzero(np.diff(ids) > 1) + 1):
        if not len(span):
            continue
        q = points[span]
        if len(q) == 1:
            q = np.vstack([q, q])
        hit = check_one(q, error, lo, hi, m, tree)
        if hit:
            return {'obstacle': name, 'slot': slot, **hit}
    return None


def ws_test(stage, a, b):
    mid = (a + b) / 2.
    half = (b - a) / 2.
    core, _, meta = bl_curves(mid, 0.)
    _, tails_long, tail_meta = bl_curves(a, 0.)
    top = np.array([xx[0], -1.5, 230. + bl_height0])
    itop = int(np.argmin(np.linalg.norm(core - top, axis=1)))
    assert np.linalg.norm(core[itop] - top) < 1e-8
    # First straight is fixed for the entire family. The remaining core is
    # 1/D-Lipschitz: upper semicircle r'=-1/(2D), and the lower pieces move
    # horizontally at -1/D. Its changing length needs no wire extension.
    fixed_core = core[:itop + 1]
    flex_core = core[itop:]
    for slot in range(4):
        tail = tails_long[slot]
        root_end = slots[slot] - [0., 0., 5.]
        itail = int(np.argmin(np.linalg.norm(tail - root_end, axis=1)))
        assert np.linalg.norm(tail[itail] - root_end) < 1e-8
        assert np.max(np.abs(tail[:itail + 1, :2] - slots[slot, :2])) < 1e-8
        # After the root, every h> a tail is a prefix of this longest tail.
        # The curved and quintic portions stay fixed in world coordinates.
        tail_body = tail[itail:]
        for target in bl_targets:
            name, group, *_ = target
            if group == 'plug':
                off_a, off_b, off_mid, speed = a, b, mid, 1.
            elif group == 'board':
                off_a, off_b = ((a, b) if stage == 'seating' else (6., 6.))
                off_mid = (off_a + off_b) / 2.
                speed = 1. if stage == 'seating' else 0.
            else:
                off_a = off_b = off_mid = speed = 0.
            offset = np.array([0., 0., off_mid])
            dx = np.array([xx[slot] - xx[0], 0., 0.])
            # Exact union of root straight intervals in this obstacle frame.
            # Contact exemptions are subtracted from that same union, not
            # frozen using the midpoint's contact classification.
            low = slots[slot, 2] - 5. - max(off_a, off_b)
            high = slots[slot, 2] + max(a - off_a, b - off_b)
            root_union = wi_line([slots[slot, 0], slots[slot, 1], low],
                                 [slots[slot, 0], slots[slot, 1], high], .02)
            pieces = [
                ('unchanged_core_straight', fixed_core + dx - offset,
                 speed * half, 'core'),
                ('narrowing_core', flex_core + dx - offset,
                 meta['core_error_mm'] + (ws_core_speed + speed) * half, None),
                ('departure_straight_union', root_union, 0., 'tail'),
                ('nested_tail_union', tail_body - offset,
                 tail_meta['tail_error_mm'] + speed * half, 'tail'),
            ]
            for kind, points, allowance, contact in pieces:
                # Only the two exact straight-piece unions get contact
                # exceptions. The first point of the bent tail is shared
                # with the root; any curved point is always checked.
                if kind == 'nested_tail_union' and name in ws_grip_tail:
                    points = points[1:]
                    contact = None
                hit = ws_span_check(points, allowance, target, contact, slot)
                if hit:
                    return {'piece': kind, 'added_temporal_bound_mm': allowance, **hit}
    return None


def ws_interval(stage, a, b, depth=0):
    global ws_tested
    ws_tested += 1
    hit = ws_test(stage, a, b)
    if hit and depth < 10:
        mid = (a + b) / 2.
        ws_interval(stage, a, mid, depth + 1)
        ws_interval(stage, mid, b, depth + 1)
    elif hit:
        ws_unproved.append({'stage': stage, 'interval_mm': [a, b], 'failure': hit})
    else:
        ws_passed.append({'stage': stage, 'interval_mm': [a, b], 'status': 'PASS'})
        print('CAM_CONTINUOUS_SOLIDS', stage, a, b, 'PASS', round(time.time()-ws_start, 2), flush=True)


for ws_stage in ['mating', 'seating']:
    ws_interval(ws_stage, 0., 6.)
    rows = sorted((r for r in ws_passed + ws_unproved if r['stage'] == ws_stage),
                  key=lambda r: r['interval_mm'][0])
    assert rows[0]['interval_mm'][0] == 0. and rows[-1]['interval_mm'][1] == 6.
    assert all(x['interval_mm'][1] == y['interval_mm'][0] for x, y in zip(rows, rows[1:]))
    print('CAM_CONTINUOUS_STAGE', ws_stage, len(rows), 'unproved',
          sum(r['stage'] == ws_stage for r in ws_unproved), flush=True)

ws_report = {
    'status': 'PASS' if not ws_unproved else 'BLOCKED',
    'scope': 'Continuous four-wire clearance to stage solids for 6 mm mating and seating; not complete assembly qualification',
    'source_main_sha256': source_hash,
    'script_sha256': sha(WS_SCRIPT), 'helper_sha256': sha(WS_HELPER),
    'screen_sha256': sha(WS_OUT / 'screen.json'),
    'target_count': len(bl_targets), 'stages': ['mating', 'seating'],
    'passed_intervals': ws_passed, 'unproved_intervals': ws_unproved,
    'interval_tests': ws_tested, 'travel_mm': 6.,
    'core_shape_speed_bound_mm_per_mm': ws_core_speed,
    'minimum_wire_to_solid_surface_gap_mm': .3,
    'wire_od_mm': OD,
    'mathematical_basis': [
        'Upper semicircle r(h)=r0-h/(2D), D=1+pi/2; pointwise derivative magnitude <=1/D; all following core pieces translate at1/D.',
        'Core starting straight is fixed. Tail after its initial departure is a fixed curve restricted by a moving endpoint; every intermediate tail is a subset of the h=a tail.',
        'Root straight union is exact in each obstacle frame; contact subintervals are excluded only at previously declared own attachment/connector interfaces.',
        'Distance to a fixed solid is1-Lipschitz. Midpoint temporal displacement plus existing chord and nearest-sample error bounds covers the full interval.',
    ],
    'constant_total_length': 'PASS_ANALYTICAL_FROM_SOURCE',
    'continuous_wire_to_wire_packing': 'NOT_TESTED',
    'unfitted_pitch_parts': wi_excluded,
    'original_straight_screw_tool': 'BLOCKED',
    'socket_tool_candidate': 'PASS_AWAITING_USER_CONFIRMATION',
    'initial_wire_formation_and_threading': 'NOT_TESTED',
    'actual_insertion_depth': 'BLOCKED_PENDING_EXACT_CONNECTOR',
    'main_applied': False, 'whole_harness': 'BLOCKED',
    'manufacturing_release': False, 'elapsed_s': time.time() - ws_start,
}
(WS_OUT / 'continuous_wire_solids.json').write_text(json.dumps(ws_report, ensure_ascii=False, indent=2) + '\n')
assert sha(source) == source_hash
print('CAM_CONTINUOUS_WIRE_SOLIDS_DONE', ws_report['status'], len(ws_passed), len(ws_unproved), flush=True)
