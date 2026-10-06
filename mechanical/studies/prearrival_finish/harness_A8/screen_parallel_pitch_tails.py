"""Screen a narrow family of forward CAM tails for the parallel-plane study.

No hardware, printed solid or clearance limit is changed. The original R11
failure remains in parallel_pitch.log. These are independent allocations.
"""
from pathlib import Path
TAIL_SCRIPT = Path(__file__).resolve()
TAIL_ROOT = TAIL_SCRIPT.parent
TAIL_HELPER = TAIL_ROOT / 'plan_cam_pitch_flex.py'
__file__ = str(TAIL_HELPER)
exec(compile(TAIL_HELPER.read_text().split('\nall_rows=[];saved={}', 1)[0], str(TAIL_HELPER), 'exec'), globals())
__file__ = str(TAIL_SCRIPT)
OUT = TAIL_ROOT / 'cam_parallel_pitch'
OUT.mkdir(exist_ok=True)
rows = []
for radius in [10.9, 10.75, 10.5, 10.25, 10., 9.75]:
    paths, radii, lengths, errors = make_case('forward', radius, 20.)
    hit = check_paths(paths, errors, True)
    row = {'radius_mm': radius, 'extension_mm': 20.,
           'status': 'PASS' if hit is None else 'BLOCKED', 'hit': hit,
           'endpoints_mm': [p[-1].tolist() for p in paths],
           'analytic_lengths_mm': lengths, 'curve_error_bounds_mm': errors}
    if hit is None:
        row['pair_surface_gap_bound_mm'] = pair_gap(paths, errors)
        assert row['pair_surface_gap_bound_mm'] >= .3
    rows.append(row)
    print('PARALLEL_TAIL', radius, row['status'], hit, flush=True)
result = {'status': 'PASS' if any(r['status'] == 'PASS' for r in rows) else 'BLOCKED',
          'rows': rows, 'source_main_sha256': source_hash,
          'script_sha256': sha(TAIL_SCRIPT), 'helper_sha256': sha(TAIL_HELPER),
          'wire_OD_mm': OD, 'required_surface_gap_mm': .3,
          'actual_mating_and_photo_uncertainty': 'NOT_TESTED',
          'scope': 'Pitch-fixed tails only; no service loops, anchors or full harness',
          'main_applied': False}
(OUT / 'tail_screen.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
assert sha(source) == source_hash
