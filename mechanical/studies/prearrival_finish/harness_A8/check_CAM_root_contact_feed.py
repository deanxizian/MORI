"""Do not infer terminal feedability from the final tight tie's wire clearance.

This deliberately tests the simple vertical contact passage through the
closed final root clamp. A bounding-box collision rejects this *modelled*
route, not every possible assembly route or the unidentified real terminal.
"""
from pathlib import Path

RF_SCRIPT = Path(__file__).resolve()
RF_ROOT = RF_SCRIPT.parent
RF_HELPER = RF_ROOT / 'check_CAM_sequential_continuous.py'
__file__ = str(RF_HELPER)
exec(compile(RF_HELPER.read_text().split('\n# Static mixed states', 1)[0],
             str(RF_HELPER), 'exec'), globals())
__file__ = str(RF_SCRIPT)
RF_OUT = TC_OUT / 'root_tie_access'
RF_OUT.mkdir(exist_ok=True)
rf_rows = []
st_angle_max = 0.
for slot in range(4):
    p, u, error, _ = oe_static[slot, 0.]
    root = p[0].copy()
    endpoint_solids = []
    for dz in [-2., 6.]:
        _, tr = ft_frame(0., root + [0., 0., dz])
        endpoint_solids.append(ft_box.transform(tr))
    sweep = manifold.Manifold.batch_hull(endpoint_solids)
    checks = []
    for name, group, solid, *_ in fm_targets:
        volume = max(0., float((sweep ^ solid).volume()))
        if volume > 1e-7:
            checks.append(dict(object=name, intersection_mm3=volume))
    # Preserve an actual stationary witness, not just a swept-volume hit.
    _, tr = ft_frame(0., root)
    contact = ft_box.transform(tr)
    witness = []
    for name, group, solid, *_ in fm_targets:
        volume = max(0., float((contact ^ solid).volume()))
        if volume > 1e-7:
            witness.append(dict(object=name, intersection_mm3=volume))
    rf_rows.append(dict(geometric_slot=slot, root_mm=root.tolist(),
                        translation_range_relative_root_mm=[-2., 6.],
                        status='BLOCKED' if checks else 'PASS', sweep_intersections=checks,
                        witness_contact_rear_mm=root.tolist(), witness_intersections=witness))
    cache(RF_OUT / f'root_contact_{slot}.npz', contact)

report = dict(
    status='BLOCKED' if any(row['status']=='BLOCKED' for row in rf_rows) else 'PASS',
    scope='One vertical nominal contact-box path through the already closed final root-tie assembly only',
    source_main_sha256=source_hash, script_sha256=sha(RF_SCRIPT), helper_sha256=sha(RF_HELPER),
    source_forming_sha256=sha(TC_OUT/'negative_complete/screen.json'),
    contact_dimensions_mm=list(ft_dims), contact_evidence='ASSUMED catalogue span box, not exact crimped contact CAD',
    rows=rf_rows, all_fixture_ids=[row[0] for row in fm_targets],
    wire_or_tie_removed_to_force_pass=False,
    required_followup='Keep the root tie open or loose while positioning wires; design the complete feed-and-seating operation before tightening. No closure path is proved by this screen.',
    real_terminal_collision='NOT_TESTED', all_alternative_routes='NOT_TESTED',
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False)
(RF_OUT/'contact_feed.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert sha(source) == source_hash
print('ROOT_CONTACT_FEED', report['status'], rf_rows, flush=True)
