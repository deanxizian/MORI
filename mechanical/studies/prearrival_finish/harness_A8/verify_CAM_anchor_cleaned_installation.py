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

candidate = A8 / 'cam_anchors/candidate_v3/cleaned'
source_j3m = A8 / 'assembly_feed_v3/open_mouth/cleaned'
for name, path in [('Pitch_Yoke', candidate / 'Pitch_Yoke.npz'),
                   ('Yaw_Base', candidate / 'Yaw_Base.npz')]:
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
            if v > 1e-3:
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

# Distinguish original float mesh contact at the installed datum from the
# real several-mm3 obstacle. Keep both values in the report.
old_yoke = read_mesh(source_j3m / 'Pitch_Yoke.npz')
contact = {'baseline_mm3': float((solids['Pitch_Servo'].m ^ old_yoke).volume()),
           'candidate_mm3': float((solids['Pitch_Servo'].m ^ solids['Pitch_Yoke'].m).volume())}
assert max(contact.values()) < 1e-3, contact
rows = []; accepted = []; started = time.time()
straight = evaluate([[0,0,0],[35,0,0]], .5, False)
print('STRAIGHT', straight['status'], len(straight['hits']), flush=True)
# Withdraw the output from its bearing first, move the case clear of the
# integral grip bed, and then continue through the central bay.
for offset in ([0.,-3.], [6.5,0.]):
    yy,zz = offset
    path = [[0.,0.,0.], [6.,0.,0.], [6.,yy,zz], [35.,yy,zz], [35.,yy,65.]]
    row = evaluate(path, .1, False)
    row['segment_clearances'] = []
    for segment, (p,q) in enumerate(zip(path,path[1:])):
        p,q=np.array(p),np.array(q)
        count=int(np.ceil(np.linalg.norm(q-p)/.1)); closest={'gap_mm':10.}
        for j in range(count+1):
            delta=p+(q-p)*j/count
            for name in moving_names:
                moving=solids[name].m.translate(delta.tolist())
                box0=np.array(moving.bounding_box())
                for n,target in fixed.items():
                    box1=fixed_boxes[n]
                    if np.any(box0[:3]>box1[3:]+1.) or np.any(box1[:3]>box0[3:]+1.):continue
                    gap=float(moving.min_gap(target,1.))
                    if gap<closest['gap_mm']:
                        closest={'gap_mm':gap,'moving':name,'obstacle':n,'translation_mm':delta.tolist()}
        actual_step=float(np.linalg.norm(q-p)/count)
        row['segment_clearances'].append({'segment':segment,**closest,'step_mm':actual_step,
            'continuous_gap_lower_bound_mm':max(0.,closest['gap_mm']-actual_step/2),
            'scope':'1-Lipschitz translation bound on stored solids; intended starting seat contact is separate'})
    accepted.append(row) if row['status']=='PASS' else None
    rows.append(row)
    print('FULL_PATH',row,flush=True)

report = {'status': 'PASS' if accepted else 'BLOCKED',
          'scope': 'Finite rigid servo removal paths; reverse for installation',
          'source_main_sha256': main_hash, 'script_sha256': sha(SCRIPT),
          'candidate_yoke_sha256': sha(candidate / 'Pitch_Yoke.npz'),
          'candidate_yaw_base_sha256': sha(candidate / 'Yaw_Base.npz'),
          'installed_mesh_contact_within_numerical_volume_threshold': contact, 'moving': moving_names, 'removed_prerequisites': sorted(removed),
          'obstacles': sorted(fixed), 'straight': straight,
          'trials': rows, 'accepted': accepted,
          'intersection_threshold_mm3': 1e-3,
          'continuous_path': 'See per-segment translation distance bounds; initial intended seat contact has no positive gap claim', 'physical_installation': 'NOT_TESTED',
          'whole_harness': 'BLOCKED', 'main_applied': False,
          'elapsed_s': time.time()-started}
(candidate / 'servo_installation_replay.json').write_text(json.dumps(report, indent=2)+'\n')
assert sha(main) == main_hash
print('SERVO_INSTALLATION', report['status'], len(accepted), 'of', len(rows), flush=True)
