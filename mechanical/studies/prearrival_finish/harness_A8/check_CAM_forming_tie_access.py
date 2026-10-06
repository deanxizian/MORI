"""Join the earlier root-tie cutter study to the full forming-stage fixture.

The old study used a detached yoke and 45 mm local leads. This retains every
current forming fixture, four complete free leads with contacts, yaw fans and
body prefixes. It checks the same conservative tool allocation, including its
whole straight approach, before any free lead is formed. A tool-volume result
does not qualify the actual jaws, hands, tightening or flexible threading.
"""
from pathlib import Path

TA_SCRIPT = Path(__file__).resolve()
TA_ROOT = TA_SCRIPT.parent
TA_HELPER = TA_ROOT / 'check_CAM_sequential_continuous.py'
__file__ = str(TA_HELPER)
exec(compile(TA_HELPER.read_text().split('\n# Static mixed states', 1)[0],
             str(TA_HELPER), 'exec'), globals())
__file__ = str(TA_SCRIPT)
TA_OUT = TC_OUT / 'root_tie_access'
TA_OUT.mkdir(exist_ok=True)
ta_start = time.time()
ta_forming_file = TC_OUT / 'negative_complete/screen.json'
ta_forming = json.loads(ta_forming_file.read_text())
assert ta_forming['status'] == 'PASS' and ta_forming['complete_four_wire_forming_coverage']
ta_bench_file = TA_ROOT / 'cam_tie_install/bench_access.json'
ta_bench = json.loads(ta_bench_file.read_text())
assert ta_bench['status'] == 'PASS' and ta_bench['source_main_sha256'] == source_hash


def ta_stored(path):
    a = np.load(path)
    solid = manifold.Manifold(manifold.Mesh64(a['vertices_mm'], a['triangles']))
    assert solid.status() == manifold.Error.NoError and solid.volume() > 1.
    return solid


ta_tool_file = TA_ROOT / 'cam_tie_install/cutter_allocation.npz'
ta_sweep_file = TA_ROOT / 'cam_tie_install/cutter_swept.npz'
ta_head_file = TA_ROOT / 'cam_tie_install/oriented_head.npz'
ta_tool, ta_sweep, ta_head = map(ta_stored, [ta_tool_file, ta_sweep_file, ta_head_file])
ta_head_bounds = np.array(ta_head.bounding_box())
ta_pivot = np.array([ta_head_bounds[0] + 2.6, ta_head_bounds[4] + .25, 232. - 2.7 / 2.])
# Prove that the saved approach is the union of the two boxes swept along
# their complete 60 mm translation, rather than trusting its filename.
cx, front, tip = ta_pivot
ta_expected_tool = box([cx-6.5, front, tip], [cx+6.5, front+7.5, tip+10.]) + box(
    [cx-31., front, tip+10.], [cx+31., front+20., tip+125.])
ta_expected_sweep = box([cx-6.5, front, tip], [cx+6.5, front+7.5, tip+70.]) + box(
    [cx-31., front, tip+10.], [cx+31., front+20., tip+185.])
ta_storage = []
for name, stored_solid, expected in [('tool', ta_tool, ta_expected_tool), ('sweep', ta_sweep, ta_expected_sweep)]:
    difference = max(0., float((stored_solid-expected).volume())) + max(0., float((expected-stored_solid).volume()))
    assert difference < 1e-7, (name, difference)
    ta_storage.append(dict(solid=name, symmetric_difference_mm3=difference, status='PASS'))
ta_tie_target = next(solid for name, group, solid, *_ in fm_targets if name == 'CAM_Tie_Head')
assert max(0., float((ta_tie_target-ta_head).volume())) + max(0., float((ta_head-ta_tie_target).volume())) < 1e-7
ta_paths = []
for slot in range(4):
    p, u, error, _ = oe_static[slot, 0.]
    ta_paths += [('free', slot, p, error),
                 ('yaw_fan', slot, pw_fans[slot][0], pw_fan_errors[slot]),
                 ('body', slot, body_samples[slot + 1, 0][0], body_error)]


def ta_rotate(solid, angle):
    return solid.translate((-ta_pivot).tolist()).rotate([0., angle, 0.]).translate(ta_pivot.tolist())


ta_rows = []
for angle in [0., -15., 15., -30., 30., -60., 60., -90., 90., 180.]:
    tool = ta_rotate(ta_tool, angle)
    sweep = ta_rotate(ta_sweep, angle)
    target = pw_obstacle('complete_cutter_approach', 'moving_tool', sweep)
    lo, hi = np.array(sweep.bounding_box()).reshape(2, 3)
    rigid = []
    for name, group, solid, lower, upper, tree in fm_targets:
        if np.any(lo > upper + .301) or np.any(hi < lower - .301):
            volume, gap = 0., .301
        else:
            volume = max(0., float((sweep ^ solid).volume()))
            gap = float(sweep.min_gap(solid, .301))
        rigid.append(dict(object=name, intersection_mm3=volume,
                          gap_mm=gap, gap_capped_at_mm=.301,
                          nominal_nonpenetration='PASS' if volume < 1e-7 else 'FAIL',
                          general_0_3mm_allowance='PASS' if gap >= .3001 else 'BLOCKED'))
    contacts = []
    for slot in range(4):
        m = tc_static[slot, 0.][2]
        volume = max(0., float((sweep ^ m).volume()))
        gap = float(sweep.min_gap(m, .301))
        contacts.append(dict(slot=slot, intersection_mm3=volume, gap_mm=gap,
                             gap_capped_at_mm=.301,
                             status='PASS' if volume < 1e-7 and gap >= .3001 else 'BLOCKED'))
    wires = []
    for kind, slot, p, error in ta_paths:
        hit = fc_wire_check(p, error, np.zeros(len(p)), target, .3)
        wires.append(dict(kind=kind, slot=slot, status='PASS' if hit is None else 'BLOCKED', failure=hit))
    collision_free = all(r['nominal_nonpenetration'] == 'PASS' for r in rigid)
    collision_free = collision_free and all(r['status'] == 'PASS' for r in contacts + wires)
    row = dict(angle_about_tail_axis_deg=angle,
               nominal_tool_sweep='PASS' if collision_free else 'BLOCKED',
               general_0_3mm_allowance='PASS' if all(r['general_0_3mm_allowance'] == 'PASS' for r in rigid) and collision_free else 'BLOCKED',
               rigid_checks=rigid, wire_checks=wires, contact_checks=contacts,
               approach_axis=(np.array([[math.cos(math.radians(angle)), 0., math.sin(math.radians(angle))],
                                        [0., 1., 0.],
                                        [-math.sin(math.radians(angle)), 0., math.cos(math.radians(angle))]]) @ np.array([0., 0., 1.])).tolist())
    ta_rows.append(row)
    print('FORMING_TIE_TOOL', angle, row['nominal_tool_sweep'],
          [(r['object'], r['intersection_mm3']) for r in rigid if r['nominal_nonpenetration'] != 'PASS'],
          [(r['kind'], r['slot']) for r in wires if r['status'] != 'PASS'], flush=True)
    if angle == 0. or collision_free:
        cache(TA_OUT / f'tool_{angle:g}.npz', tool)
        cache(TA_OUT / f'sweep_{angle:g}.npz', sweep)

accepted = [row['angle_about_tail_axis_deg'] for row in ta_rows if row['nominal_tool_sweep'] == 'PASS']
ta_tail_file = TA_ROOT / 'cam_tie_install/tail_corridor.npz'
ta_tail = ta_stored(ta_tail_file)
ta_tail_target = pw_obstacle('tie_free_tail_work_corridor', 'work_allocation', ta_tail)
ta_tail_rigid = []
for name, group, solid, *_ in fm_targets:
    volume = max(0., float((ta_tail ^ solid).volume()))
    gap = float(ta_tail.min_gap(solid, .301))
    ta_tail_rigid.append(dict(object=name, intersection_mm3=volume, gap_mm=gap,
                              gap_capped_at_mm=.301, nominal_nonpenetration='PASS' if volume < 1e-7 else 'FAIL',
                              expected_boundary_at_tail_exit=name in ['CAM_Tie_Head', 'CAM_Tie_Band']))
ta_tail_wires = []
for kind, slot, p, error in ta_paths:
    hit = fc_wire_check(p, error, np.zeros(len(p)), ta_tail_target, .3)
    ta_tail_wires.append(dict(kind=kind, slot=slot, status='PASS' if hit is None else 'BLOCKED', failure=hit))
ta_tail_contacts = []
for slot in range(4):
    m = tc_static[slot, 0.][2]
    volume = max(0., float((ta_tail ^ m).volume()))
    gap = float(ta_tail.min_gap(m, .301))
    ta_tail_contacts.append(dict(slot=slot, intersection_mm3=volume, gap_mm=gap,
                                gap_capped_at_mm=.301, status='PASS' if volume < 1e-7 and gap >= .3001 else 'BLOCKED'))
ta_tail_good = all(row['nominal_nonpenetration'] == 'PASS' for row in ta_tail_rigid)
ta_tail_good = ta_tail_good and all(row['status'] == 'PASS' for row in ta_tail_wires + ta_tail_contacts)
cache(TA_OUT / 'tail_corridor.npz', ta_tail)
report = dict(
    status='PASS' if accepted else 'BLOCKED',
    scope='Same nominal cutter allocation on the complete current forming fixture and all twelve wire portions, before forming; not actual tie installation',
    source_main_sha256=source_hash, script_sha256=sha(TA_SCRIPT), helper_sha256=sha(TA_HELPER),
    source_forming_sha256=sha(ta_forming_file), source_bench_sha256=sha(ta_bench_file),
    source_tool_sha256=sha(ta_tool_file), source_sweep_sha256=sha(ta_sweep_file),
    source_tie_head_sha256=sha(ta_head_file),
    source_tail_corridor_sha256=sha(ta_tail_file), tool_sweep_construction_checks=ta_storage,
    ordinary_wire_margin_mm=.3, nominal_rigid_overlap_tolerance_mm3=1e-7,
    rigid_margin_reported_separately=True,
    rotation_pivot_mm=ta_pivot.tolist(), straight_approach_mm=60.,
    free_wire_state='All four unformed endpoints of the completed continuous forming proof',
    source_fixture_ids=[x[0] for x in fm_targets], source_fixture_count=len(fm_targets),
    uninstalled_other_pitch_parts=wi_excluded,
    wire_portions=len(ta_paths), free_contact_count=4,
    initial_tool_angle_deg=0., nominal_clear_angles_deg=accepted, trials=ta_rows,
    tail_corridor=dict(status='PASS' if ta_tail_good else 'BLOCKED',
                       scope='Previously allocated outward tail volume against full current forming fixture; flexible threading and actual latch remain unverified',
                       rigid_checks=ta_tail_rigid, wire_checks=ta_tail_wires, contact_checks=ta_tail_contacts),
    tool_shape_evidence='ASSUMED conservative boxes based on KNIPEX 79 22 125 catalogue dimensions',
    tail_axis_evidence='ASSUMED T18R latch-channel allocation from prior study',
    tool_closure_and_cut='NOT_TESTED', manipulation_and_force='NOT_TESTED',
    flexible_tie_threading_and_tightening='NOT_TESTED', complete_initial_feed='NOT_TESTED',
    actual_cutter_grasp='NOT_TESTED', all_anchors='NOT_TESTED',
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False,
    elapsed_s=time.time()-ta_start)
(TA_OUT / 'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert sha(source) == source_hash
print('FORMING_TIE_TOOL_DONE', report['status'], accepted, flush=True)
