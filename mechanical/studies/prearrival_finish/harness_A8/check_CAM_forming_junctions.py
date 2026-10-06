"""Check identical states at every boundary of the revised four-wire motion.

This does not replace the separate continuous interval receipts. It verifies
that their prescribed endpoints match the static wires/contacts retained by
the next stage, without teleporting or removing another conductor.
"""
from pathlib import Path

CJ_SCRIPT = Path(__file__).resolve()
CJ_ROOT = CJ_SCRIPT.parent
CJ_HELPER = CJ_ROOT / 'check_CAM_sequential_continuous.py'
__file__ = str(CJ_HELPER)
exec(compile(CJ_HELPER.read_text().split('\n# Static mixed states', 1)[0],
             str(CJ_HELPER), 'exec'), globals())
__file__ = str(CJ_SCRIPT)
CJ_OUT = TC_OUT / 'negative_complete'
CJ_OUT.mkdir(exist_ok=True)
cj_last_file = TC_OUT / 'negative_tail/screen.json'
cj_last = json.loads(cj_last_file.read_text())
assert cj_last['status'] == 'PASS' and cj_last['complete_last_wire_coverage']
assert cj_last['source_main_sha256'] == source_hash
assert cj_last['helper_sha256'] == sha(CJ_HELPER)
cj_paths = [s['path'] for s in sc_path['stages'][:3]] + [cj_last['path']]
cj_rows = []
for stage, path in enumerate(cj_paths):
    slot = da_order[stage]
    for phase, edge in [(0., (path[0], path[1])),
                        (1., (path[-2], path[-1]))]:
        points, material, error = sc_curve(stage, edge, phase)
        fixed, fixed_u, fixed_error, _ = oe_static[slot, phase]
        reference = np.column_stack([
            np.interp(material, fixed_u, fixed[:, axis]) for axis in range(3)
        ])
        distance = float(np.linalg.norm(points - reference, axis=1).max())
        _, transform = ft_frame(phase, points[-1])
        contact = ft_box.transform(transform)
        static_contact = tc_static[slot, phase][2]
        difference = max(0., float((contact - static_contact).volume()))
        difference += max(0., float((static_contact - contact).volume()))
        endpoint_check = sc_test(stage, edge, phase, phase)
        good = distance < 1e-8 and difference < 1e-7 and endpoint_check is None
        cj_rows.append(dict(stage=stage, geometric_slot=slot, fraction=phase,
                            status='PASS' if good else 'FAIL',
                            wire_to_static_maximum_error_mm=distance,
                            contact_symmetric_difference_mm3=difference,
                            nominal_endpoint_failure=endpoint_check))

# Three static wires coexist during the last stage. Reuse their original
# complete pair receipts only because their geometry and source are unchanged.
cj_static_file = TC_OUT / 'continuous/screen.json'
cj_static_source = json.loads(cj_static_file.read_text())
assert cj_static_source['source_main_sha256'] == source_hash
assert cj_static_source['helper_sha256'] == sha(SC_HELPER)
cj_static = [row for row in cj_static_source['static_wire_pairs'] if row['stage'] == 3]
assert len(cj_static) == 3 and all(row['status'] == 'PASS' for row in cj_static)
cj_contact_file = TC_SOURCE / 'contacts.json'
cj_contacts = json.loads(cj_contact_file.read_text())
cj_static_contacts = next(row for row in cj_contacts['rows']
                         if row['stage'] == 3 and row['fraction'] == 0.)
assert cj_static_contacts['nominal_nonpenetration'] == 'PASS'
report = dict(
    status='PASS' if all(row['status'] == 'PASS' for row in cj_rows) else 'FAIL',
    scope='Eight stage endpoints match retained static wire/contact states; not a complete process proof',
    source_main_sha256=source_hash, script_sha256=sha(CJ_SCRIPT),
    helper_sha256=sha(CJ_HELPER),
    source_original_path_sha256=sha(TC_OUT / 'screen.json'),
    source_last_wire_sha256=sha(cj_last_file),
    source_static_proof_sha256=sha(cj_static_file),
    source_static_contacts_sha256=sha(cj_contact_file),
    wire_order=list(da_order), endpoints=cj_rows,
    last_stage_static_wire_pairs=cj_static,
    last_stage_static_contacts=cj_static_contacts,
    forming_curve_parameters=dict(
        planar_segments_mm=[float(value) for value in fr_lengths],
        planar_arclength_mm=float(fc_end), upper_radius_mm=float(fc_R),
        lower_radius_mm=float(fc_r), lateral_quintic_shift_mm=1.8875,
        lateral_quintic_span_mm=16.,
        note='Parameters read from the identical forming helper; the quintic uses fixed material coordinates'),
    all_conductors_retained=True, generic_0_3mm_contact_packing='BLOCKED',
    feed_to_start='NOT_TESTED', terminal_insertion='NOT_TESTED', ties='NOT_TESTED',
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False)
(CJ_OUT / 'junctions.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
assert sha(source) == source_hash
print('FORMING_JUNCTIONS_DONE', report['status'], len(cj_rows), flush=True)
