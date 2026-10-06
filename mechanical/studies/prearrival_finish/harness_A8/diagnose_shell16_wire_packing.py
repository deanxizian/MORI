"""Locate the actual closest wire points before changing the feed recipe.

This is a read-only study of source solids, with no changed acceptance margin,
wire diameter, hardware transforms or main-model writes.
"""
from pathlib import Path
DIAG16_SCRIPT = Path(__file__).resolve()
DIAG16_HELPER = DIAG16_SCRIPT.parent / 'merge_shell16_back20_wires.py'
__file__ = str(DIAG16_HELPER)
exec(compile(DIAG16_HELPER.read_text().split('\nfor k in range(21):', 1)[0],
             str(DIAG16_HELPER), 'exec'), globals())
__file__ = str(DIAG16_SCRIPT)
OUT = ORDER_OUT / 'shell16_packing_diagnosis'
OUT.mkdir(exist_ok=True)
baseline_path = ORDER_OUT / 'shell16_back20_merged/screen.json'
baseline = json.loads(baseline_path.read_text())
assert baseline['script_sha256'] == sha(DIAG16_HELPER)
original_current = {int(p): dict(q) for p, q in baseline['records'][-1]['parameters'].items()}
assert baseline['records'][-1]['bridge_y_mm'] == -2.
diagnoses = []
arrays = {}


def closest_details(ca, cb):
    pa, pb = ca['points'], cb['points']
    kd = KDTree(len(pb))
    for j, q in enumerate(pb):
        kd.insert(q, j)
    kd.balance()
    distance, i, j = min((float(hit[2]), i, int(hit[1]))
                         for i, q in enumerate(pa) for hit in [kd.find(q)])
    row = dict(sampled_center_distance_mm=distance,
               sampled_surface_distance_mm=distance-OD,
               positions_mm=[pa[i].tolist(), pb[j].tolist()], indices=[i, j])
    row['arclength_from_body_mm'] = [float(np.linalg.norm(np.diff(p[:k+1], axis=0), axis=1).sum())
                                    for p, k in [(pa, i), (pb, j)]]
    row['tangents'] = []
    for p, k in [(pa, i), (pb, j)]:
        delta = p[min(k+1, len(p)-1)]-p[max(0, k-1)]
        row['tangents'].append((delta/np.linalg.norm(delta)).tolist())
    return row


for label, p4angle in [('original', None), ('fourth_rear_7_5', -7.5)]:
    current = {p: dict(q) for p, q in original_current.items()}
    if p4angle is not None:
        current[4].update(entry_azimuth_deg=p4angle, planar_radius_mm=8.)
    for ordering in ['simultaneous', (2, 3), (3, 2)]:
        for step, parameters in enumerate(snapshots_at_hold(2, ordering)):
            f, curves, pairrows = evaluate(2., parameters)
            if f:
                detail = dict(label=label, order=ordering, step=step,
                              parameters=parameters, failure=f, pairs=pairrows)
                if f['kind'] == 'CAM_mutual_coarse_clearance':
                    detail['closest'] = closest_details(curves[f['a']], curves[f['b']])
                for pin, curve in curves.items():
                    arrays[f'case{len(diagnoses)}_pin{pin}'] = curve['points']
                diagnoses.append(detail)
                print('PACKING_DIAG', label, ordering, step, detail, flush=True)
                break

np.savez_compressed(OUT/'curves.npz', **arrays)
report = dict(status='PASS', scope='Reproduced and located known finite wire packing failures only',
              script_sha256=sha(DIAG16_SCRIPT), helper_sha256=sha(DIAG16_HELPER),
              source_files={str(baseline_path.relative_to(PROJECT)):sha(baseline_path),
                            **baseline['source_files']}, protected_sources=protected,
              wire_od_mm=OD, required_surface_margin_mm=MARGIN,
              diagnoses=diagnoses, curves_sha256=sha(OUT/'curves.npz'),
              complete_attached_assembly='BLOCKED', main_applied=False,
              manufacturing_release=False)
(OUT/'diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PACKING_DIAG_DONE', len(diagnoses), flush=True)
