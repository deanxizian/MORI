"""Joint packing of four thin and seven larger allocated neck conductors.

The upper staging plane is Z200, below the arbitrary Z206 plane used in the
first search. Neither plane is a connector. Tests do not assert completed
fan-out, clip design, print strength, or end-to-end installed harness.
"""
from pathlib import Path
import sys, json, time, math, itertools
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
sys.path.insert(0,str(HERE))
from native_context import Context, np, sha
from validate import rigidtr
from mathutils import Vector
from mathutils.kdtree import KDTree
from neck_family import family, upper, rotate

ctx=Context();started=time.time();original=ctx.targets.copy()
hosts={'Yaw_Base','Pitch_Yoke'}
groups={n:s.group for n,s in ctx.ss.items()}
targets_by_group={group:{n:t for n,t in original.items() if n not in hosts and
    (groups.get(n,'body') if groups.get(n,'body') in ['yaw','pitch'] else 'body')==group}
    for group in ['body','yaw','pitch']}
sizes={'signal':.6604,'power_sample':1.4224}
counts={'signal':4,'power_sample':7}
middle=family(z0=130.,z1=175.,radius=7.2)
tip,te=upper(end_z=200.)
curves={r['yaw_deg']:np.vstack([r['points'],rotate(tip,r['yaw_deg'])[1:]]) for r in middle}
errors={r['yaw_deg']:max(r['chord_error_mm'],te) for r in middle}
inverse={(group,yaw,pitch):np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
    for group in ['yaw','pitch'] for yaw in range(-60,61,10) for pitch in range(-20,26,5)}
rows=[]
for kind,od in sizes.items():
    for angle in range(0,360,5):
        hit=None;tested=0
        for yaw in range(-60,61,10):
            p=rotate(curves[yaw],angle)
            for group,targets in targets_by_group.items():
                ctx.targets=targets
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=inverse[(group,yaw,pitch)] if group in ['yaw','pitch'] else np.eye(4)
                    local=p@tr[:3,:3].T+tr[:3,3]
                    check=ctx.clear(local,errors[yaw],radius=od/2)
                    tested+=1
                    if check:
                        hit=dict(yaw_deg=yaw,pitch_deg=pitch,point_frame=group+'_zero_pose',**check)
                        break
                if hit:break
            if hit:break
        rows.append(dict(kind=kind,angle_deg=angle,status='BLOCKED' if hit else 'PASS',relative_group_checks=tested,hit=hit))
        if angle%90==0:print('PACK_SCREEN',kind,angle,'passes',sum(r['status']=='PASS' for r in rows if r['kind']==kind),'s',round(time.time()-started,1),flush=True)

# Common radial family: rotating both curves by the same angle preserves their
# distance. Cover every curve-to-curve segment pair using nearest sampled
# vertices minus both half-step bounds and both analytic chord errors.
pairs=[]
trees={}
for yaw,p in curves.items():
    tree=KDTree(len(p))
    for i,v in enumerate(p):tree.insert(Vector(v),i)
    tree.balance();trees[yaw]=tree
for delta in range(5,181,5):
    lower=math.inf;witness=None
    for yaw,p in curves.items():
        other=rotate(p,delta)
        sample_min=min(float(trees[yaw].find(Vector(v))[2]) for v in other)
        step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())
        bound=sample_min-step-2*errors[yaw]-1e-4
        if bound<lower:lower=bound;witness=yaw
    pairs.append(dict(delta_angle_deg=delta,minimum_centreline_distance_lower_bound_mm=lower,worst_sample_yaw_deg=witness))
pair_lookup={r['delta_angle_deg']:r['minimum_centreline_distance_lower_bound_mm'] for r in pairs}
pair_lookup[0]=0.
nodes=[dict(kind=r['kind'],angle_deg=r['angle_deg'],OD_mm=sizes[r['kind']]) for r in rows if r['status']=='PASS']
def compatible(a,b):
    d=abs(a['angle_deg']-b['angle_deg']);d=min(d,360-d)
    return pair_lookup[d]-(a['OD_mm']+b['OD_mm'])/2>=.3
power=[n for n in nodes if n['kind']=='power_sample']
signal=[n for n in nodes if n['kind']=='signal']
calls=0;limit=2000000;solution=None
def pick_signal(options,chosen,needed):
    global calls
    calls+=1
    if calls>limit:return None
    if needed==0:return chosen
    if len(options)<needed:return None
    for i,a in enumerate(options):
        found=pick_signal([b for b in options[i+1:] if compatible(a,b)],chosen+[a],needed-1)
        if found is not None:return found
    return None
def pick_power(options,signals,chosen,needed):
    global calls,solution
    calls+=1
    if calls>limit or len(options)<needed or len(signals)<4:return False
    if needed==0:
        found=pick_signal(signals,[],4)
        if found is not None:solution=chosen+found;return True
        return False
    for i,a in enumerate(options):
        if pick_power([b for b in options[i+1:] if compatible(a,b)],
                      [b for b in signals if compatible(a,b)],chosen+[a],needed-1):return True
    return False
pick_power(power,signal,[],7)
selected_pairs=[];outputs={}
if solution:
    assert len(solution)==11
    for a,b in itertools.combinations(solution,2):
        d=abs(a['angle_deg']-b['angle_deg']);d=min(d,360-d)
        gap=pair_lookup[d]-(a['OD_mm']+b['OD_mm'])/2
        assert gap>=.3
        selected_pairs.append(dict(a=a,b=b,surface_gap_lower_bound_mm=gap))
    for i,n in enumerate(solution):
        n['allocation_id']=f'{n["kind"]}_{i}'
        for yaw,p in curves.items():outputs[f'wire{i}_y{yaw}']=rotate(p,n['angle_deg'])
    np.savez_compressed(HERE/'packed_curves.npz',**outputs)
ctx.targets=original;ctx.assert_unchanged()
out=dict(status='PASS' if solution else 'BLOCKED',
    scope='Eleven allocated common-neck local paths simultaneously, excluding two prospective channel hosts',
    source_main_sha256=ctx.source_hash,sources=ctx.sources,script_sha256=sha(__file__),helper_sha256=sha(HERE/'neck_family.py'),
    rows=rows,pair_bounds=pairs,selected=solution,selected_pairs=selected_pairs,
    candidate_counts={k:sum(r['kind']==k and r['status']=='PASS' for r in rows) for k in sizes},
    search_nodes=calls,search_node_limit=limit,search_exhausted=calls<=limit,
    wire_sizes_mm=sizes,wire_size_evidence='Signal uses A8 Alpha2841/7 catalogue maximum; other7 use inherited22AWG diameter solely as unselected space allocation',
    native_parts=209,mates=29,fixed_candidate_wires=14,head_poses=130,
    prospective_channel_hosts=sorted(hosts),host_cuts='NOT_TESTED',
    curve_middle_z_mm=[130.,175.],curve_end_z_mm=200.,common_middle_radius_mm=7.2,
    common_middle_length_mm=middle[0]['model_length_mm'],sampled_middle_min_radius_mm=min(r['sampled_min_radius_mm'] for r in middle),
    upper_analytic_min_radius_mm=15.,required_thick_wire_radius_screen_mm=14.224+1.4224/2,
    simultaneous_pair_checks=len(selected_pairs)*13,
    output_curves_sha256=sha(HERE/'packed_curves.npz') if solution else None,
    whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,
    actual_wire_selection='BLOCKED',connector_fanouts='NOT_TESTED',retention='NOT_TESTED',installation='NOT_TESTED',strength='NOT_TESTED',
    limitations=['Signal/power labels are mechanical slots; no electrical pin assignment is changed or inferred.',
      'The signal four use a changed central law, so the earlier four full CAM paths cannot be combined with this candidate without redesigning both approaches.',
      'UpperZ200 and lowerZ130 are staging planes, not real endpoints; this is not an end-to-end harness.',
      'The two named host solids are still present in main and were excluded only to screen prospective channels.',
      'No source hardware was moved, scaled or removed. All checks are nominal finite geometry.'],elapsed_s=time.time()-started)
(HERE/'packing.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('COMMON_NECK_PACKED',out['status'],out['candidate_counts'],'search',calls,'selected',solution,'seconds',round(time.time()-started,1),flush=True)
