"""Check four fixed lower-neck corridors against 130 native head poses.

The wire ends remain unconnected: no yaw/pitch service loop is claimed here.
Curve segments have continuous clearance bounds at each discrete head pose.
"""
from pathlib import Path
import hashlib,json,math,sys,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path(bpy.data.filepath);before=sha(source)
prior=json.loads((HERE/'outer_corridor_screen.json').read_text())
assert before==prior['source_main_sha256']
lowest='--lowest-upper-bend' in sys.argv
upper_start=160. if lowest else 162. if '--lower-upper-bend' in sys.argv else 164.
outer_radius=37.6 if lowest else 37.
output_name='outer_corridor_motion_lowest.json' if lowest else 'outer_corridor_motion_lower.json' if upper_start==162. else 'outer_corridor_motion.json'
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
cache=np.load(HERE/'outer_corridor_curves.npz')
selected=[next(r for r in prior['passing'] if r['angle_deg']==a and r['outer_radius_mm']==outer_radius
               and r['lower_z_mm']==137. and r['upper_bend_start_z_mm']==upper_start) for a in [45,135,225,315]]
paths={r['angle_deg']:cache[r['curve_key']] for r in selected}
allpoints=np.concatenate(list(paths.values()))
bound=.6604/2+.3+max(np.linalg.norm(np.diff(p,axis=0),axis=1).max() for p in paths.values())/2+8*(1-math.cos(math.pi/400))+1e-4
lo=allpoints.min(0)-bound;hi=allpoints.max(0)+bound
moving={n:s for n,s in ss.items() if s.group in ['yaw','pitch']}
corners={n:np.array(list(__import__('itertools').product(*zip(s.lo,s.hi)))) for n,s in moving.items()}

def hits(p,s):
    ids=np.flatnonzero(np.all(p>=s.lo-bound,axis=1)&np.all(p<=s.hi+bound,axis=1))
    tree=s.bvh()
    for i in ids:
        dist=float(tree.find_nearest(Vector(p[i]))[3])
        if dist<bound:return dict(part=s.name,point_mm=p[i].tolist(),surface_distance_mm=dist,required_bound_mm=float(bound))
    starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
    for i in starts:
        v=p[i]
        if np.all(v>=s.lo) and np.all(v<=s.hi):
            q=manifold.Manifold.sphere(.005,12).translate(v.tolist())
            if (q^s.m).volume()>q.volume()/2:return dict(part=s.name,point_mm=v.tolist(),inside=True)
    return None

rows=[];failures=[];examined=set();start=time.time()
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        transforms={g:rigidtr(yaw,pitch if g=='pitch' else 0) for g in ['yaw','pitch']}
        near={}
        for n,s in moving.items():
            t=np.asarray(transforms[s.group]);bb=corners[n]@t[:3,:3].T+t[:3,3]
            if np.any(bb.max(0)<lo) or np.any(bb.min(0)>hi):continue
            near[n]=Solid(s.o,s,transforms[s.group]);examined.add(n)
        bad=[]
        for a,p in paths.items():
            for n,s in near.items():
                hit=hits(p,s)
                if hit:bad.append(dict(angle_deg=a,**hit))
        row=dict(yaw_deg=yaw,pitch_deg=pitch,status='FAIL' if bad else 'PASS',failures=bad,
                 nearby_moving_parts=sorted(near))
        rows.append(row)
        if bad:failures.append(row)
    print('OUTER_CORRIDOR_POSE_YAW',yaw,'failures',len(failures),flush=True)
# For rays 90 or 180 degrees apart and r>=29, the distance is >=29*sqrt(2).
# This lower bound applies to every pair of continuous analytic curves.
pair_bound=(outer_radius-8.)*math.sqrt(2.)
report=dict(status='FAIL' if failures else 'PASS',scope='Four body-fixed local corridors vs sampled head solids only',
    revision=P['revision'],source_main_sha256=before,script_sha256=sha(__file__),
    source_static_screen_sha256=sha(HERE/'outer_corridor_screen.json'),
    source_curve_sha256=sha(HERE/'outer_corridor_curves.npz'),selected=selected,
    poses=len(rows),rows=rows,failures=failures,moving_parts_considered=len(moving),
    nearby_moving_parts=sorted(examined),wire_clearance_bound_mm=float(bound),
    continuous_interwire_distance_lower_bound_mm=pair_bound,
    interwire_required_centreline_distance_mm=.6604+.3,
    fixed_parts_coverage='Continuous curve clearance from outer_corridor_screen.json at unchanged transforms',
    whole_harness='BLOCKED',PCB_roots='NOT_TESTED',upper_moving_loop='NOT_TESTED',terminal_threading='NOT_TESTED',
    unsampled_head_poses='NOT_TESTED',retention_and_hands='NOT_TESTED',
    main_applied=False,manufacturing_release=False,elapsed_s=time.time()-start)
assert sha(source)==before;report['main_unchanged']=True
(HERE/output_name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('OUTER_CORRIDOR_MOTION_DONE',report['status'],report['poses'],len(failures),flush=True)
