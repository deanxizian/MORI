"""Screen a yaw-servo-in-head layout without changing the released assembly.

Servo case belongs to yaw only; its downward output attaches to a body-fixed
reaction member. Mounts, bearing carrier and reaction member are not designed
by this placement study. Never interpret a clear servo envelope as assembly fit.
"""
import sys, hashlib, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *
from validate import Solid, intersect_volume, rigidtr

out = ROOT / 'studies/yaw_servo_in_head'
out.mkdir(parents=True, exist_ok=True)
source = ROOT / 'mori_v1_2.blend'
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.context.window.scene = bpy.data.scenes['MORI_V1_Assembly']
load_collections(); assembled()
solids = {o.name.removeprefix(PREFIX): Solid(o) for o in parts() if o.get('group') != 'dock'}
routes = [Solid(o) for o in bpy.context.scene.objects if o.get('role') == 'routing']
old_names = {'Yaw_Servo', 'Yaw_Output', 'Yaw_Horn', 'Yaw_Lock_Screw'}
redesign = {'Pitch_Yoke', 'Yaw_Turntable', 'Yaw_Base', 'Body_Top_Shroud'}
old_tip = Vector((0, 0, float(solids['Yaw_Output'].hi[2])))
tol = float(P['validation']['collision_volume_tolerance_mm3'])

def transform(tip_z, clock_deg):
    return (Matrix.Translation(Vector((0, 0, tip_z))) @
            Matrix.Rotation(math.radians(clock_deg), 4, 'Z') @
            Matrix.Rotation(math.pi, 4, 'X') @ Matrix.Translation(-old_tip))

def sample(tip_z, clock_deg, yaw_values):
    tr = transform(tip_z, clock_deg)
    bases = [Solid(solids[n].o, solids[n], tr) for n in ['Yaw_Servo', 'Yaw_Output']]
    hard, interface, wires = [], [], []
    nearest = {'gap_mm_capped_at_10': 10.0}
    for yaw in yaw_values:
        # Case rotates with the yaw platform; spline/output remains body-fixed.
        moved = [Solid(bases[0].o, bases[0], rigidtr(yaw, 0)), bases[1]]
        for pitch in range(-20, 26, 5):
            for n, base in solids.items():
                if n in old_names: continue
                target = Solid(base.o, base, rigidtr(yaw, pitch if base.group == 'pitch' else 0)) if base.group in ['yaw', 'pitch'] else base
                for a in moved:
                    v = intersect_volume(a, target)
                    if v > tol:
                        row = {'yaw_deg':yaw, 'pitch_deg':pitch, 'servo_part':a.name, 'target':n, 'overlap_mm3':round(v, 2)}
                        (interface if n in redesign else hard).append(row)
                    if n not in redesign and np.all(a.hi + 10 >= target.lo) and np.all(target.hi + 10 >= a.lo):
                        gap = float(a.m.min_gap(target.m, 10))
                        if gap < nearest['gap_mm_capped_at_10']:
                            nearest = {'gap_mm_capped_at_10':round(gap, 3), 'servo_part':a.name, 'target':n, 'yaw_deg':yaw, 'pitch_deg':pitch}
            for base in routes:
                target = Solid(base.o, base, rigidtr(yaw, pitch if base.group == 'pitch' else 0)) if base.group in ['yaw', 'pitch'] else base
                for a in moved:
                    v = intersect_volume(a, target)
                    if v > tol: wires.append({'yaw_deg':yaw, 'pitch_deg':pitch, 'servo_part':a.name, 'route':base.name, 'overlap_mm3':round(v, 2)})
    lo = np.min([a.lo for a in bases], axis=0); hi = np.max([a.hi for a in bases], axis=0)
    return {'tip_ground_z_mm':tip_z, 'tip_from_head_center_mm':tip_z-D['head_z'], 'clock_deg':clock_deg,
            'bounds_xyz_mm':[[round(float(a),2),round(float(b),2)] for a,b in zip(lo,hi)],
            'hard_conflicts':hard, 'existing_support_conflicts_requiring_redesign':interface,
            'existing_route_conflicts':wires, 'nearest_existing_nonreplacement_part':nearest,
            'poses':len(yaw_values)*10}

started = time.time(); cases = []
for offset in [-38, -36, -34, -32, -30]:
    for angle in [0, 90, 180, 270]:
        r = sample(D['head_z'] + offset, angle, [0]); cases.append(r)
        print('SCREEN',offset,angle,len(r['hard_conflicts']),len(r['existing_support_conflicts_requiring_redesign']),len(r['existing_route_conflicts']),flush=True)
# Prefer the cleanest real-part placement. Existing printed interfaces may need
# redesign, but are recorded, never waived as a collision-free assembly.
best = min(cases, key=lambda r:(len(r['hard_conflicts']),len(r['existing_route_conflicts']),len(r['existing_support_conflicts_requiring_redesign']),-r['nearest_existing_nonreplacement_part']['gap_mm_capped_at_10']))
full = sample(best['tip_ground_z_mm'], best['clock_deg'], range(-60, 61, 10))
mass = json.loads((ROOT/'reports/mass_budget.json').read_text())
items = mass['density_and_component_mass_assumptions']; total = sum(v['mass_g'] for v in items)
tr = transform(best['tip_ground_z_mm'], best['clock_deg']); delta = 0; relocated_mass = 0
for v in items:
    if v['id'] in ['Yaw_Servo','Yaw_Output']:
        c = Vector(v['com_mm']); after = tr @ c
        delta += v['mass_g']*(after.z-c.z); relocated_mass += v['mass_g']
result = {'study':'Yaw servo inverted in lower head, on yaw-only frame', 'source_revision':P['revision'],
          'source_model_sha256':source_sha, 'source_model_modified':False,
          'status':'PLACEMENT_ONLY_ASSEMBLY_BLOCKED', 'candidate_sweep':cases, 'selected_full_sampling':full,
          'method':'Actual triangulated Manifold solids, containment included; AABB only for broad phase. Original-size servo case and output rotated rigidly. Final130 poses at yaw10deg/pitch5deg; finite sampling, not continuous proof. Existing LCD connector proxies retain their original limitations.',
          'kinematics':{'servo_case':'yaw frame, not pitch frame','servo_output':'body-fixed reaction member','head_yaw_relation':'head yaw is opposite shaft rotation relative to case; calibrate actual sign and zero','load_path':'Dedicated yaw bearing and bilateral pitch bearings retained; servo spline is not the head load-bearing support'},
          'removed_from_body_case_bounds_xyz_mm':[[float(a),float(b)] for a,b in zip(solids['Yaw_Servo'].lo,solids['Yaw_Servo'].hi)],
          'new_pcb_fitting_space_mm':None,
          'mass_only_estimate':{'data_status':'ASSUMED','relocated_mass_g':round(relocated_mass,1),'whole_COM_rise_mm_unchanged_other_parts':round(delta/total,1),'limits':'Same prior masses. New supports and eventual PCB relocation not included. Not measured, not a complete revised COM.'},
          'blockers':['Body-fixed reaction member and horn locking access not designed','New yaw bearing support and servo-ear attachment not designed; existing support conflicts are explicit','New routing and connector approach not designed','S3 power PCB dimensions/installed height/holes unknown; no claim a complete power board now fits','Head/yaw inertia, strength, print fit and real balance not qualified'],
          'elapsed_s':round(time.time()-started,1)}
save_json(out/'placement_study.json',result)
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
print('HEAD_YAW_STUDY_COMPLETE',json.dumps({'selected':{k:full[k] for k in ['tip_ground_z_mm','clock_deg','bounds_xyz_mm','nearest_existing_nonreplacement_part']},'hard_conflicts':len(full['hard_conflicts']),'support_conflicts':len(full['existing_support_conflicts_requiring_redesign']),'route_conflicts':len(full['existing_route_conflicts']),'mass_only_estimate':result['mass_only_estimate']},ensure_ascii=False),flush=True)
