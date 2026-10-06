"""Raise the temporary CAM-loop anchor to create room for yaw-fixed fan-in.

Independent comparison only. Existing M1.47/J3M solids and documented wire
size/clearance criteria stay unchanged. Anchors are still geometric datums.
"""
from pathlib import Path
UPPER_SCRIPT=Path(__file__).resolve();UPPER_ROOT=UPPER_SCRIPT.parent
UPPER_HELPER=UPPER_ROOT/'plan_cam_following_arc.py';__file__=str(UPPER_HELPER)
exec(compile(UPPER_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(UPPER_HELPER),'exec'),globals())
__file__=str(UPPER_SCRIPT)
OUT=UPPER_ROOT/'cam_fan_in/short_tail_anchor';OUT.mkdir(parents=True,exist_ok=True)
# The existing tail ends in a straight +Y span. Trim only its final 1.5 mm.
original_tails=[q.copy() for q in tails]
tails=[np.vstack([q[q[:,1]<10.5], np.array([q[-1,0],10.5,q[-1,2]])]) for q in tails]
assert all(np.allclose(q[-1], old[-1]-[0.,1.5,0.]) for q,old in zip(tails,original_tails))
np.savez_compressed(OUT/'tails.npz',**{f'slot{i}':q for i,q in enumerate(tails)})
stored={};selected=[];trials=[];started=time.time()
order=[0,-20,25,-15,20,-10,15,-5,10,5]
for az in [228.,230.]:
    ay=-.5;rb=7.5;end_length=.5;bases=[following(ay,az,rb,end_length,p) for p in order]
    assert all(b is not None for b in bases)
    target=max(b[1] for b in bases)+.02;rows=[];curves={};failure=None
    for pitch in order:
        built=following(ay,az,rb,end_length,pitch,target)
        if built is None:failure={'type':'span','pitch_deg':pitch};break
        points,row=built
        for slot,x in enumerate(xx):
            q=points+[x-xc,0.,0.];hit=check_curve(q,row['curve_error_bound_mm'],pitch,True)
            if hit:failure={'slot':slot,**hit};break
            curves[slot,pitch]=q
        if failure:break
        rows.append(row)
    trials.append({'anchor_z_mm':az,'status':'BLOCKED' if failure else 'PASS','failure':failure})
    if not failure:
        idx=len(selected)
        for (slot,pitch),points in curves.items():stored[f'candidate{idx}_slot{slot}_pitch{pitch}']=points
        selected.append({'parameters':{'anchor_y_mm':ay,'anchor_z_mm':az,'lower_radius_mm':rb,'terminal_straight_mm':end_length},
            'anchor_slots_mm':[[float(x),ay,az] for x in xx],'exact_length_mm':target,'poses':sorted(rows,key=lambda r:r['pitch_deg'])})
    print('UPPER_ANCHOR',az,trials[-1],round(time.time()-started,1),flush=True)
np.savez_compressed(OUT/'curves.npz',**stored)
result={'status':'PASS' if selected else 'BLOCKED','source_main_sha256':source_hash,'script_sha256':sha(UPPER_SCRIPT),
    'helper_sha256':sha(UPPER_HELPER),'source_arc_helper_sha256':sha(UPPER_ROOT/'plan_cam_parallel_arcs.py'),
    'tail_curves_sha256':sha(OUT/'tails.npz'),'original_tail_curves_sha256':sha(UPPER_ROOT/'cam_parallel_pitch/shifted_tails.npz'),'tail_trim_mm':1.5,
    'tail_report_sha256':sha(UPPER_ROOT/'cam_parallel_pitch/shifted_tail_screen.json'),'curves_sha256':sha(OUT/'curves.npz'),
    'selected':selected,'trials':trials,'wire_OD_mm':OD,'minimum_radius_required_mm':REQUIRED_R,'surface_gap_required_mm':.3,
    'scope':'Raised temporary anchor, finite-pose source clearance only; no fan-in or physical anchor yet',
    'joint_angle_samples':130,'whole_partial_wire_self_and_mutual':'NOT_TESTED','body_prefix_coexistence':'NOT_TESTED',
    'fan_in':'NOT_TESTED','anchors':'NOT_TESTED','continuous_joint_motion':'NOT_TESTED','physical_wire_behavior':'NOT_TESTED',
    'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('UPPER_ANCHOR_DONE',result['status'],flush=True)
