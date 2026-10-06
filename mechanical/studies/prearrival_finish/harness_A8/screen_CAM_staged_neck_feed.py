"""Screen straight loose-contact feeding before the yaw internals are fitted.

Rigid continuous sweeps are exact for the stated fixed-orientation translation.
This is an assembly-order study, not permission to depin or change the harness.
All original source solids and the three prior unadopted prints are retained.
"""
from pathlib import Path
STAGED_SCRIPT = Path(__file__).resolve()
STAGED_HELPER = STAGED_SCRIPT.parent / 'screen_CAM_neck_contact_consistency.py'
__file__ = str(STAGED_HELPER)
exec(compile(STAGED_HELPER.read_text().split('\nallocations=', 1)[0], str(STAGED_HELPER), 'exec'), globals())
__file__ = str(STAGED_SCRIPT)
STAGED = OUT / 'staged_feed'
STAGED.mkdir(exist_ok=True)
started = time.time()
dims = np.array([1., 1.8, 4.1])
# Box padding is conservative in every direction, unlike a tessellated sphere.
# Its use cannot turn a failed nominal gap into a passing one.
contact = manifold.Manifold.cube((dims + .6).tolist(), center=True)
nominal = manifold.Manifold.cube(dims.tolist(), center=True)
body = fixture | upper
fixed_bridge = {'Yaw_Base', 'Yaw_Base_-1_Nut', 'Yaw_Base_1_Nut'}
reaction = {n for n in moving if n.startswith('Yaw_Reaction_')}
stages = {
    'bridge_bore_open': body | fixed_bridge,
    'bearing_installed': body | fixed_bridge | {'Yaw_Bearing'},
    'reaction_installed': body | fixed_bridge | {'Yaw_Bearing'} | reaction,
    'yoke_installed': body | fixed_bridge | {'Yaw_Bearing', 'Pitch_Yoke'},
}
extra_ids = {n for n in targets if n.startswith('fixed_wire_')}
rows = []
for stage, ids in stages.items():
    for radial in (0., 2., 3., 4., 5., 6., 6.8, 7.6):
        cases = []
        for phase in (45, 135, 225, 315):
            ph = math.radians(phase)
            er = np.array([math.cos(ph), math.sin(ph), 0.])
            et = np.array([-math.sin(ph), math.cos(ph), 0.])
            ez = np.array([0., 0., 1.])
            transforms = [np.column_stack([er, et, ez, radial * er + (z + dims[2] / 2) * ez])
                          for z in (136., 205.)]
            sweep = manifold.Manifold.batch_hull([contact.transform(t) for t in transforms])
            bb = np.asarray(sweep.bounding_box())
            hits = []
            for n in sorted(ids | extra_ids):
                tb = target_boxes[n]
                if np.any(bb[:3] > tb[3:]) or np.any(tb[:3] > bb[3:]):
                    continue
                volume = max(0., float((sweep ^ targets[n]).volume()))
                if volume > 1e-5:
                    hits.append(dict(obstacle=n, padded_sweep_intersection_mm3=volume))
            cases.append(dict(phase_deg=phase, status='BLOCKED' if hits else 'PASS', hits=hits,
                              start_transform=transforms[0].tolist(), end_transform=transforms[1].tolist()))
        row = dict(stage=stage, radial_mm=radial, status='PASS' if all(c['status'] == 'PASS' for c in cases) else 'BLOCKED', cases=cases)
        rows.append(row)
        print('STAGED_NECK_FEED', stage, radial, row['status'],
              sorted({h['obstacle'] for c in cases for h in c['hits']}), flush=True)

sections = {}
for z in (140., 143., 145., 147., 149., 153., 160., 180., 188.):
    sections[str(z)] = {n: [a.tolist() for a in solids[n].slice(z).to_polygons()]
                       for n in ('Yaw_Base', 'Yaw_Reaction_Link', 'Pitch_Yoke')}
(STAGED / 'sections.json').write_text(json.dumps(sections, ensure_ascii=False, indent=2) + '\n')
report = dict(status='PASS' if any(r['status'] == 'PASS' for r in rows) else 'BLOCKED',
              scope='Continuous straight bare-contact translation before stated yaw members; not attached-wire feeding or complete assembly',
              script_sha256=sha(STAGED_SCRIPT), helper_sha256=sha(STAGED_HELPER), source_main_sha256=source_hash,
              protected_sources=protected, substituted_unadopted_prints={n: dict(path=str(p.relative_to(PROJECT)), sha256=sha(p)) for n, p in replacements.items()},
              source_fixed_wires_sha256=sha(fixed_path), source_objects=len(solids),
              contact_dimensions_mm=dims.tolist(), contact_evidence='ASSUMED requested space, not maximum post-crimp dimensions',
              clearance_padding_mm=.3, padding_shape='Axis-aligned local box, an outer bound for Euclidean clearance',
              rear_z_range_mm=[136., 205.], stages={n: dict(present=sorted(ids), deferred=sorted(set(solids)-ids)) for n, ids in stages.items()},
              fixed_wire_count=len(extra_ids), rows=rows, contact_passing_cases=sum(r['status']=='PASS' for r in rows),
              trailing_wire='NOT_TESTED', entry_from_body_side='NOT_TESTED', wire_seating='NOT_TESTED',
              yaw_members_installation_after_feeding='NOT_TESTED', mating_allocations='NOT_TESTED',
              no_universal_impossibility_claim=True, candidate_structures_changed=False,
              main_applied=False, whole_harness='BLOCKED', manufacturing_release=False, elapsed_s=time.time()-started)
(STAGED / 'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
assert all(sha(PROJECT / p) == h for p, h in protected.items())
print('STAGED_NECK_FEED_DONE', report['status'], report['contact_passing_cases'], round(time.time()-started,2), flush=True)
