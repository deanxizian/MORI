"""Check an early R7 S bend for the identified first-wire/last-tail conflict.

This replaces only the first8mm of an unadopted routing continuation. It does
not connect to the earlier full loops or fix their other wire-pair failures.
"""
from pathlib import Path
EARLY_SCRIPT=Path(__file__).resolve();EARLY_DIR=EARLY_SCRIPT.parent
EARLY_HELPER=EARLY_DIR/'check_cam_pitch_flex_packing.py';__file__=str(EARLY_HELPER)
exec(compile(EARLY_HELPER.read_text().split('\nbody_samples={',1)[0],str(EARLY_HELPER),'exec'),globals())
__file__=str(EARLY_SCRIPT);OUT=EARLY_DIR/'cam_pitch_flex/early_turn';OUT.mkdir(exist_ok=True)
a=body_curves['pin1_yaw0'][-1];R=7.;shift=-8.-a[0]
theta=math.acos(1-shift/(2*R));t=np.linspace(0,theta,161)
first=a+np.c_[R*(1-np.cos(t)),np.zeros(len(t)),R*np.sin(t)]
m=first[-1]
second=m+np.c_[R*(np.cos(theta-t)-math.cos(theta)),np.zeros(len(t)),R*(math.sin(theta)-np.sin(theta-t))]
points=np.vstack([first,second[1:]])
error=R*(1-math.cos(theta/320));sample=fine(points)
hits=[];pair_rows=[]
for pitch in range(-20,26,5):
    inv=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
    for name,group,solid,lo,hi,tree in ob:
        yaws=range(-60,61,10) if group=='body' else [0]
        for yaw in yaws:
            if group=='pitch':q=points@inv[:3,:3].T+inv[:3,3]
            elif group=='body':
                tr=np.asarray(rigidtr(yaw,0));q=points@tr[:3,:3].T+tr[:3,3]
            else:q=points
            hit=check_one(q,error,lo,hi,solid,tree)
            if hit:hits.append({'pitch_deg':pitch,'yaw_deg':yaw,'obstacle':name,**hit})
    tr=np.asarray(rigidtr(0,pitch))
    for i in range(4):
        tail=head_curves[f'left_slot{i}']@tr[:3,:3].T+tr[:3,3]
        row=pair(sample,fine(tail),error,head_family['curve_error_bounds_mm'][i])
        pair_rows.append({'pitch_deg':pitch,'head_slot':i,**row})
for yaw in range(-60,61,10):
    tr=np.asarray(rigidtr(yaw,0));q=points@tr[:3,:3].T+tr[:3,3];qsample=fine(q)
    for pin in range(1,5):
        bs=fine(body_curves[f'pin{pin}_yaw{yaw}'])
        row=own_prefix_check(qsample,bs,error,body_error) if pin==1 else pair(qsample,bs,error,body_error)
        pair_rows.append({'yaw_deg':yaw,'body_pin':pin,**row})
np.savez_compressed(OUT/'early_turn.npz',points=points)
result={'status':'PASS' if not hits and all(r['status']=='PASS' for r in pair_rows) else 'BLOCKED',
    'scope':'Local first-wire S bend versus source solids and both existing partial halves; remaining flex continuation absent',
    'source_script_sha256':sha(EARLY_SCRIPT),'source_helper_sha256':sha(EARLY_HELPER),'source_main_sha256':source_hash,
    'source_candidate_sha256':sha(candidate/'candidate.blend'),'source_pair_diagnostic_sha256':sha(EARLY_DIR/'cam_pitch_flex/side/full_pair_diagnostic.json'),
    'curve_sha256':sha(OUT/'early_turn.npz'),'start_mm':a.tolist(),'end_mm':points[-1].tolist(),
    'radius_mm':R,'arc_angle_deg_each':math.degrees(theta),'analytic_length_mm':2*R*theta,
    'curve_error_bound_mm':error,'minimum_head_tail_gap_bound_mm':min(r['gap_bound_mm'] for r in pair_rows if 'head_slot' in r),
    'tangent_start_and_end':[0.,0.,1.],'radius_vs_straight_curvature_jumps':'Piecewise curvature, continuous tangent; physical bend shape unqualified',
    'hits':hits,'pair_checks':pair_rows,'full_rejoined_curve':'NOT_TESTED','anchors':'NOT_TESTED',
    'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('EARLY_S_TURN',result['status'],result['minimum_head_tail_gap_bound_mm'],len(hits),flush=True)
