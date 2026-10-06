"""Test an empty housing's straight approach after the proved wire forming.

Only external approach clearance is evaluated. Internal cavities, terminal
lances, polarity/keying, insertion force and manipulation remain unresolved;
the catalogue box must not be treated as an exact populated connector CAD.
"""
from pathlib import Path

HA_SCRIPT = Path(__file__).resolve()
HA_ROOT = HA_SCRIPT.parent
HA_HELPER = HA_ROOT / 'check_CAM_sequential_continuous.py'
__file__ = str(HA_HELPER)
exec(compile(HA_HELPER.read_text().split('\n# Static mixed states', 1)[0],
             str(HA_HELPER), 'exec'), globals())
__file__ = str(HA_SCRIPT)
HA_OUT = TC_OUT / 'housing_approach'
HA_OUT.mkdir(exist_ok=True)
ha_forming_path = TC_OUT / 'negative_complete/screen.json'
ha_forming = json.loads(ha_forming_path.read_text())
assert ha_forming['status'] == 'PASS' and ha_forming['complete_four_wire_forming_coverage']
assert ha_forming['source_main_sha256'] == source_hash
assert ha_forming['helper_sha256'] == sha(HA_HELPER)
ha_final = bl_plug.translate([0., 0., 2.])
ha_initial = ha_final.translate([0., 0., 8.])
ha_hull = manifold.Manifold.batch_hull([ha_initial, ha_final])
assert abs(ha_final.hull().volume() - ha_final.volume()) < 1e-8
ha_target = pw_obstacle('housing_complete_straight_sweep', 'moving', ha_hull)
ha_rigid = []
for name, group, solid, lo, hi, tree in fm_targets:
    volume = max(0., float((ha_hull ^ solid).volume()))
    gap = float(ha_hull.min_gap(solid, .301))
    ha_rigid.append(dict(object=name, intersection_mm3=volume,
                         gap_capped_at_mm=.301, gap_mm=gap,
                         status='PASS' if volume < 1e-7 and gap >= .3001 else 'BLOCKED'))
ha_wires = []
for stage in ha_forming['stages']:
    slot = stage['active_slot']
    points, material, error = sc_curve(stage['stage'], tuple(stage['path'][-2:]), 1.)
    mask = material <= fc_end - 2. + 1e-10
    hit = fc_wire_check(points[mask], error, np.zeros(mask.sum()), ha_target, .3)
    ha_wires.append(dict(kind='formed_wire_outside_crimp_zone', slot=slot,
                         excluded_material_interval_mm=[fc_end - 2., fc_end],
                         status='PASS' if hit is None else 'BLOCKED', failure=hit))
    for kind, samples, bound in [
            ('yaw_fan', pw_fans[slot], pw_fan_errors[slot]),
            ('body_prefix', body_samples[slot + 1, 0], body_error)]:
        hit = fc_wire_check(samples[0], bound, np.zeros(len(samples[0])), ha_target, .3)
        ha_wires.append(dict(kind=kind, slot=slot, status='PASS' if hit is None else 'BLOCKED',
                             failure=hit))
good = all(row['status'] == 'PASS' for row in ha_rigid + ha_wires)
cache(HA_OUT / 'initial.npz', ha_initial)
cache(HA_OUT / 'final.npz', ha_final)
cache(HA_OUT / 'sweep.npz', ha_hull)
report = dict(
    status='PASS' if good else 'BLOCKED',
    scope='External straight approach of the empty catalogue housing only, after the proved four-wire forming',
    source_main_sha256=source_hash, script_sha256=sha(HA_SCRIPT),
    helper_sha256=sha(HA_HELPER), source_forming_sha256=sha(ha_forming_path),
    initial_bounds_mm=list(ha_initial.bounding_box()), final_bounds_mm=list(ha_final.bounding_box()),
    approach_vector_mm=[0., 0., -8.], sweep='Exact convex hull of the two endpoints of a convex translating housing box',
    ordinary_margin_mm=.3, rigid_checks=ha_rigid, wire_checks=ha_wires,
    housing_shape_evidence='ASSUMED catalogue-span box, not exact CAM mate identification',
    intended_terminal_interface='Four matching loose contact boxes and their final2mm wire crimp zones are outside this external-approach proof; internal passage is BLOCKED, not waived',
    terminal_cavity_and_lance_fit='BLOCKED', terminal_keying_and_polarity='BLOCKED',
    contact_insertion_process='NOT_TESTED', manipulation_and_force='NOT_TESTED',
    initial_feed='NOT_TESTED', ties='NOT_TESTED',
    source_fixtures=[row['object'] for row in ha_rigid],
    uninstalled_CAM_board=True, uninstalled_other_pitch_parts=wi_excluded,
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False)
(HA_OUT / 'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
assert sha(source) == source_hash
print('HOUSING_APPROACH_DONE', report['status'],
      [row for row in ha_rigid + ha_wires if row['status'] != 'PASS'], flush=True)
