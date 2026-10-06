"""Check saved route seams and prove the shortened tail is an unchanged subset.

These are nominal candidate paths, not natural wire shapes or cut lengths.
"""
from pathlib import Path
import hashlib, json, math
import numpy as np

SCRIPT = Path(__file__).resolve()
HERE = SCRIPT.parent
OUT = HERE / 'cam_fan_in'
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

old = np.load(HERE / 'cam_parallel_pitch/shifted_tails.npz')
new = np.load(OUT / 'short_tail_v2/tails.npz')
loops = np.load(OUT / 'short_tail_v2/curves.npz')
fans = np.load(OUT / 'four_bend_transition/curves.npz')
prefixes = np.load(HERE / 'cam_pitch_port/lower_staging/body_partial_curves.npz')
packing = read(OUT / 'four_bend_transition/packing.json')
tail_math = read(HERE / 'cam_parallel_pitch/tail_math_bounds.json')
assert packing['status'] == tail_math['status'] == 'PASS'
choice = packing['assignments'][0]

trim_rows = []
for slot in range(4):
    a, b = old[f'slot{slot}'], new[f'slot{slot}']
    # No earlier point was removed or moved. Only the final +Y straight was cut.
    assert np.array_equal(a[:len(b)-1], b[:-1])
    removed = a[len(b)-2:]
    assert np.max(np.abs(removed[:, [0, 2]] - a[-1, [0, 2]])) < 1e-12
    assert np.all(np.diff(removed[:, 1]) > 0)
    assert a[len(b)-2, 1] < b[-1, 1] < a[len(b)-1, 1]
    assert np.allclose(a[-1] - b[-1], [0, 2.5, 0], atol=1e-12, rtol=0)
    trim_rows.append({'slot': slot, 'status': 'PASS', 'trimmed_straight_mm': 2.5,
                      'unchanged_leading_vertices': len(b)-1,
                      'original_endpoint_mm': a[-1].tolist(), 'endpoint_mm': b[-1].tolist()})

def transform(yaw, pitch):
    y, p = np.deg2rad([yaw, pitch])
    cy, sy, cp, sp = np.cos(y), np.sin(y), np.cos(p), np.sin(p)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1.]])
    rx = np.array([[1., 0, 0], [0, cp, -sp], [0, sp, cp]])
    r = rz @ rx
    centre = np.array([0., 0., 222.])
    return r, centre - r @ centre

def moved(points, yaw, pitch):
    r, t = transform(yaw, pitch)
    return points @ r.T + t

def seam(a, b):
    av, bv = a[-1] - a[-2], b[1] - b[0]
    angle = math.degrees(math.acos(float(np.clip(np.dot(av, bv) / np.linalg.norm(av) / np.linalg.norm(bv), -1, 1))))
    return float(np.linalg.norm(a[-1] - b[0])), angle

seams = []
for yaw in range(-60, 61, 10):
    for pitch in range(-20, 26, 5):
        for pin in range(1, 5):
            slot = pin - 1
            pieces = [prefixes[f'pin{pin}_yaw{yaw}'],
                      moved(fans[f'pin{pin}_candidate{choice[slot]}'], yaw, 0),
                      moved(loops[f'candidate0_slot{slot}_pitch{pitch}'], yaw, 0),
                      moved(new[f'slot{slot}'][::-1], yaw, pitch)]
            for label, a, b in zip(['body_to_fan', 'fan_to_pitch_loop', 'pitch_loop_to_CAM_tail'], pieces[:-1], pieces[1:]):
                distance, angle = seam(a, b)
                # float32 Blender transforms account for micrometre-scale noise.
                assert distance < 3e-5, (pin, yaw, pitch, label, distance)
                assert angle < .3, (pin, yaw, pitch, label, angle)
                seams.append({'pin': pin, 'yaw_deg': yaw, 'pitch_deg': pitch, 'seam': label,
                              'endpoint_error_mm': distance, 'sampled_tangent_error_deg': angle})

sources = [HERE/'cam_parallel_pitch/shifted_tails.npz', HERE/'cam_parallel_pitch/tail_math_bounds.json',
           OUT/'short_tail_v2/tails.npz', OUT/'short_tail_v2/curves.npz', OUT/'short_tail_v2/screen.json',
           OUT/'four_bend_transition/curves.npz', OUT/'four_bend_transition/packing.json',
           HERE/'cam_pitch_port/lower_staging/body_partial_curves.npz']
result = {'status': 'PASS', 'script_sha256': sha(SCRIPT), 'source_main_sha256': packing['source_main_sha256'],
          'scope': 'Saved route endpoint consistency and unchanged tail-subset proof only',
          'trim_rows': trim_rows, 'tail_length_lower_mm': tail_math['length_lower_mm']-2.5,
          'tail_length_upper_mm': tail_math['length_upper_mm']-2.5,
          'tail_radius_lower_mm': tail_math['minimum_curvature_radius_lower_bound_mm'],
          'fan_assignment': choice, 'head_pose_count': 130, 'checked_seams': len(seams),
          'maximum_endpoint_error_mm': max(x['endpoint_error_mm'] for x in seams),
          'maximum_sampled_tangent_error_deg': max(x['sampled_tangent_error_deg'] for x in seams),
          'tangent_scope': 'Saved polyline tangent consistency; mathematical families separately specify C1 joins',
          'continuous_collision': 'NOT_TESTED', 'anchors': 'NOT_TESTED', 'whole_harness': 'BLOCKED',
          'main_applied': False, 'manufacturing_release': False,
          'files': {str(p.relative_to(ROOT)): sha(p) for p in sources}}
assert sha(ROOT/'mechanical/mori_v1_2.blend') == result['source_main_sha256']
(OUT/'joins.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status', 'checked_seams', 'maximum_endpoint_error_mm', 'maximum_sampled_tangent_error_deg']}))
