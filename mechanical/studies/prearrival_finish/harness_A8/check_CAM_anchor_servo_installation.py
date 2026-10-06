"""Independent assembly-path screen for the CAM anchor candidate.

Use the same removed prerequisites as the original pitch-servo installation.
No geometry is edited. Translation paths are finite samples, not a physical
assembly trial. Keep the failed straight path in the evidence record.
"""
from pathlib import Path
import sys, json, hashlib, itertools, time

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
PROJECT_DIR = A8.parents[3]
sys.path.insert(0, str(PROJECT_DIR / 'mechanical/scripts'))
from common import *
from validate import Solid

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
main = PROJECT_DIR / 'mechanical/mori_v1_2.blend'
main_hash = sha(main)
assert Path(bpy.data.filepath) == main
load_collections(); assembled(); bpy.context.view_layer.update()
solids = {o.name.removeprefix(PREFIX): Solid(o) for o in parts()
          if o.get('group') not in ['dock', 'coupon']}

def read_mesh(path):
    a = np.load(path)
    m = manifold.Manifold(manifold.Mesh64(a['vertices_mm'], a['triangles']))
    assert m.status() == manifold.Error.NoError
    return m

candidate = A8 / 'cam_anchors/candidate'
source_j3m = A8 / 'assembly_feed_v3/open_mouth/cleaned'
for name, path in [('Pitch_Yoke', candidate / 'Pitch_Yoke.npz'),
                   ('Yaw_Base', source_j3m / 'Yaw_Base.npz')]:
    solids[name].m = read_mesh(path)

moving_names = ['Pitch_Servo', 'Pitch_Output']
removed = {n for n, a in solids.items() if a.group == 'pitch'} | {
    'Yaw_Servo', 'Yaw_Output', 'Yaw_Lock_Screw', 'Head_Front', 'Head_Rear',
    'Body_Upper', 'Body_Lower'} | {
    n for n in solids if n.startswith(('Head_Pitch_Ear_', 'Head_Yaw_Ear_'))}
fixed = {n: a.m for n, a in solids.items()
         if n not in removed and n not in moving_names}
fixed_boxes = {n: np.array(m.bounding_box()) for n, m in fixed.items()}

def hits_at(delta):
    result = []
    for name in moving_names:
        moving = solids[name].m.translate(delta)
        b = np.array(moving.bounding_box())
        for n, target in fixed.items():
            t = fixed_boxes[n]
            if np.any(b[:3] > t[3:] + 1e-6) or np.any(t[:3] > b[3:] + 1e-6):
                continue
            v = max(0., float((moving ^ target).volume()))
            if v > 1e-5:
                result.append({'moving': name, 'obstacle': n, 'volume_mm3': v,
                               'translation_mm': list(map(float, delta))})
    return result

memo = {}
def evaluate(points, step=.5, stop_first=True):
    checks = 0; hits = []; minimum_gap = 10.
    for i, (p, q) in enumerate(zip(points, points[1:])):
        p, q = np.array(p, float), np.array(q, float)
        count = max(1, int(np.ceil(np.linalg.norm(q-p) / step)))
        for j in range(count+1):
            if i and not j: continue
            delta = p+(q-p)*j/count
            key = tuple(np.round(delta, 7))
            if key not in memo: memo[key] = hits_at(delta)
            checks += 1
            if memo[key]:
                hits.extend(memo[key])
                if stop_first:
                    return {'status':'BLOCKED', 'checked_samples': checks,
                            'hits': hits, 'waypoints_mm': points}
    return {'status': 'BLOCKED' if hits else 'PASS', 'checked_samples': checks,
            'hits': hits, 'waypoints_mm': points, 'maximum_step_mm': step}

rows = []; accepted = []; started = time.time()
straight = evaluate([[0,0,0],[35,0,0]], .5, False)
print('STRAIGHT', straight['status'], len(straight['hits']), flush=True)
# Withdraw the output from its bearing first, move the case clear of the
# integral grip bed, and then continue through the central bay.
for withdrawal, side_y, lower_z in itertools.product([4.,6.,8.,10.], [0.,6.5,9.,-12.], [0.,-3.,-4.]):
    if side_y == lower_z == 0: continue
    path = [[0.,0.,0.], [withdrawal,0.,0.],
            [withdrawal,side_y,lower_z], [35.,side_y,lower_z]]
    row = evaluate(path)
    rows.append(row)
    if row['status'] == 'PASS':
        accepted.append(row)
        print('ACCEPTED', path, row['checked_samples'], flush=True)
    elif len(rows) < 8:
        print('REJECTED', path, row['hits'][0], flush=True)

report = {'status': 'PASS' if accepted else 'BLOCKED',
          'scope': 'Finite rigid servo removal paths; reverse for installation',
          'source_main_sha256': main_hash, 'script_sha256': sha(SCRIPT),
          'candidate_yoke_sha256': sha(candidate / 'Pitch_Yoke.npz'),
          'candidate_yaw_base_sha256': sha(source_j3m / 'Yaw_Base.npz'),
          'moving': moving_names, 'removed_prerequisites': sorted(removed),
          'obstacles': sorted(fixed), 'straight': straight,
          'trials': rows, 'accepted': accepted,
          'intersection_threshold_mm3': 1e-5,
          'continuous_path': 'NOT_TESTED', 'physical_installation': 'NOT_TESTED',
          'whole_harness': 'BLOCKED', 'main_applied': False,
          'elapsed_s': time.time()-started}
(candidate / 'servo_installation.json').write_text(json.dumps(report, indent=2)+'\n')
assert sha(main) == main_hash
print('SERVO_INSTALLATION', report['status'], len(accepted), 'of', len(rows), flush=True)
