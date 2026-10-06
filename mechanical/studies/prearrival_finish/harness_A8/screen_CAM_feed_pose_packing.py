"""Search body-connected CAM shapes at a specific obstructed bridge pose.

This is only a configuration feasibility search. A passing set would still
need a continuous material-preserving transition from the settled source.
Native body pins, source wire lengths, and candidate print solids stay fixed.
"""
from pathlib import Path

PACKING_SCRIPT = Path(__file__).resolve()
PACKING_HELPER = PACKING_SCRIPT.parent / 'screen_CAM_elevated_bridge_feed.py'
__file__ = str(PACKING_HELPER)
exec(compile(PACKING_HELPER.read_text().split('\nstarted = time.time()', 1)[0],
             str(PACKING_HELPER), 'exec'), globals())
__file__ = str(PACKING_SCRIPT)
from collections import Counter, defaultdict
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--y', type=float, default=0.)
parser.add_argument('--z', type=float, default=18.)
parser.add_argument('--label', default='lift18')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assert args.label.replace('_', '').replace('-', '').isalnum()
OUT = ORDER_OUT / 'feed_pose_packing' / args.label
OUT.mkdir(parents=True, exist_ok=True)
bt = trans(y=args.y, z=args.z)
st = shellpose(15., args.y, max(14., args.z-4.))
matrices = dict(core=I, upper=np.linalg.inv(st), bridge=np.linalg.inv(bt))
assert rigid_check(housing, matrices, True) is None
families = ['LSL', 'LSR', 'RSL', 'RSR', 'LRL-1', 'LRL1', 'RLR-1', 'RLR1']
started = time.time()


def variant_curve(pin, azimuth, bend_radius, family, elevation_fraction):
    original = specifications[pin]['selected']
    selected = dict(original, entry_azimuth_deg=azimuth,
                    planar_path=dict(original['planar_path'], radius_mm=bend_radius, family=family))
    specifications[pin]['selected'] = selected
    try:
        curve, failure = make_elevated_curve(pin, bt, elevation_fraction)
    finally:
        specifications[pin]['selected'] = original
    if curve:
        curve['parameters'] = dict(entry_azimuth_deg=azimuth, planar_radius_mm=bend_radius,
                                   family=family, elevation_fraction=elevation_fraction)
        curve['selection_score'] = ((azimuth-original['entry_azimuth_deg'])/15.)**2 + (
            (bend_radius-original['planar_path']['radius_mm'])/2.)**2 + 4*(1-elevation_fraction)**2
    return curve, failure


pools = {}
rows = []
saved = {}
for pin in range(1, 5):
    counts = Counter()
    blockers = Counter()
    examples = {}
    choices = []
    old = specifications[pin]['selected']
    angles = sorted(set(old['entry_azimuth_deg']+d for d in [-30., -15., 0., 15., 30., 45.]))
    for azimuth, radius, fraction, family in itertools.product(angles, [7., 8., 10., 12., 14.],
                                                              [0., .25, .5, .75, 1.], families):
        counts['controls'] += 1
        curve, failure = variant_curve(pin, azimuth, radius, family, fraction)
        if failure:
            counts[failure['kind']] += 1
            continue
        lengths[pin-1]['curve_chord_error_mm'] = curve['curve_chord_error_mm']
        failure = wire_check(pin, curve['points'], matrices)
        if failure:
            counts['geometry_reject'] += 1
            blockers[failure['obstacle']] += 1
            examples.setdefault(failure['obstacle'], dict(parameters=curve['parameters'], failure=failure))
            continue
        counts['individual_pass'] += 1
        choices.append(curve)
    # Keep variation between path families rather than only nearly identical
    # short curves. This remains a bounded selection, not global feasibility.
    by_family = defaultdict(list)
    for curve in sorted(choices, key=lambda c: (c['selection_score'], c['prefix_analytic_mm'])):
        key = curve['parameters']['family']
        if len(by_family[key]) < 8: by_family[key].append(curve)
    pool = sorted([c for family_pool in by_family.values() for c in family_pool],
                  key=lambda c: (c['selection_score'], c['prefix_analytic_mm']))
    for i, c in enumerate(pool):
        c['candidate_id'] = f'pin{pin}_{i}'
        saved[c['candidate_id']] = c['points']
    pools[pin] = pool
    rows.append(dict(pin=pin, status='PASS' if pool else 'BLOCKED', counts=dict(counts),
                     retained_candidates=len(pool), blockers=dict(blockers), examples=examples))
    print('CAM_POSE_POOL', args.label, pin, rows[-1]['status'], dict(counts),
          dict(blockers), round(time.time()-started, 2), flush=True)

cache = {}
trees_by_id = {}
pair_calls = 0
search_nodes = 0
NODE_LIMIT = 100000


def compatible(a, b):
    global pair_calls
    key = (a['candidate_id'], b['candidate_id'])
    if key in cache: return cache[key]
    pair_calls += 1
    if b['candidate_id'] not in trees_by_id:
        tree = KDTree(len(b['points']))
        for i, p in enumerate(b['points']): tree.insert(p, i)
        tree.balance()
        trees_by_id[b['candidate_id']] = tree
    tree = trees_by_id[b['candidate_id']]
    uncertainty = (max(np.linalg.norm(np.diff(a['points'], axis=0), axis=1))
                   +max(np.linalg.norm(np.diff(b['points'], axis=0), axis=1)))/2
    uncertainty += a['curve_chord_error_mm']+b['curve_chord_error_mm']+.0001
    minimum = math.inf
    for p in a['points']:
        minimum = min(minimum, float(tree.find(p)[2]))
        if minimum < OD+MARGIN+uncertainty: break
    gap = float(minimum-OD-uncertainty)
    result = dict(status='PASS' if gap >= MARGIN else 'BLOCKED',
                  surface_gap_lower_bound_mm=gap, complete_minimum=gap >= MARGIN)
    cache[key] = result
    return result


order = sorted(pools, key=lambda pin: len(pools[pin]))


def search(selected):
    global search_nodes
    search_nodes += 1
    if search_nodes > NODE_LIMIT: return None
    if len(selected) == 4: return selected
    for curve in pools[order[len(selected)]]:
        if all(compatible(previous, curve)['status'] == 'PASS' for previous in selected):
            found = search(selected+[curve])
            if found: return found
    return None


selected = search([]) if all(pools.values()) else None
selected_pairs = []
if selected:
    for a, b in itertools.combinations(selected, 2):
        selected_pairs.append(dict(a=a['candidate_id'], b=b['candidate_id'], **compatible(a, b)))
np.savez_compressed(OUT/'curves.npz', **saved)
report = dict(status='PASS' if selected else 'BLOCKED',
              scope='Four-wire finite-pose configuration search only; no transition or complete assembly proof',
              script_sha256=sha(PACKING_SCRIPT), helper_sha256=sha(PACKING_HELPER),
              source_main_sha256=source_hash, protected_sources=protected,
              source_files={str(p.relative_to(PROJECT)):sha(p) for p in
                            [pack_path, joined_path, body_math_path, partial_path, datum_path, h02_path, h02_check_path,
                             PACKING_SCRIPT.parent/'body_prefix_v2/curvature_paths.py', membership_path]},
              substituted_unadopted_prints=membership['substituted_unadopted_prints'],
              pose=dict(bridge=bt.tolist(), shell=st.tolist()), rows=rows,
              pools={str(pin):[{k:v for k,v in c.items() if k != 'points'} for c in pool] for pin,pool in pools.items()},
              selected=[c['candidate_id'] for c in selected] if selected else None,
              selected_pairs=selected_pairs, pair_calls=pair_calls, search_nodes=search_nodes,
              node_limit=NODE_LIMIT, search_exhausted=search_nodes <= NODE_LIMIT,
              curves_sha256=sha(OUT/'curves.npz'), fixed_body_wires=14,
              wire_OD_mm=OD, minimum_analytic_radius_mm=7., clearance_mm=MARGIN,
              original_nominal_allocations_mm=[r['full_nominal_allocation_mm'] for r in lengths],
              self_clearance='NOT_TESTED', terminal_space_and_hands='NOT_TESTED',
              transition_from_settled='NOT_TESTED', continuous_assembly='NOT_TESTED',
              no_universal_impossibility_claim=True, main_applied=False,
              manufacturing_release=False, whole_harness='BLOCKED', elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_POSE_PACKING_DONE', args.label, report['status'], report['selected'],
      pair_calls, search_nodes, round(time.time()-started, 2), flush=True)
