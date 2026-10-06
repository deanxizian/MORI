"""Check two disjoint harness halves with a lower provisional joining datum.

The previous Z206 point was a temporary routing endpoint, not hardware. Trim
only its final vertical13mm toZ193; the missing service loop is NOT supplied
or approved by this test. All source files and model geometry stay unchanged.
"""
from pathlib import Path
NEW_SCRIPT=Path(__file__).resolve();NEW_DIR=NEW_SCRIPT.parent
HELPER=NEW_DIR/'check_cam_departure_coexistence.py';__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nrows=[];limits=[]',1)[0],str(HELPER),'exec'),globals())
__file__=str(NEW_SCRIPT)
ORIGINAL_OUT=OUT;OUT=ORIGINAL_OUT/'lower_staging';OUT.mkdir(exist_ok=True)
original=body;body={};subset=[]
for name in original.files:
    p=original[name];assert abs(p[-1,2]-206)<1e-8
    ids=np.flatnonzero(p[:,2]>=193.);i=int(ids[0]);assert i>0
    assert np.allclose(p[i-1:,:2],p[-1,:2],rtol=0,atol=1e-10)
    assert np.all(np.diff(p[i-1:,2])>0)
    u=(193-p[i-1,2])/(p[i,2]-p[i-1,2]);end=p[i-1]+u*(p[i]-p[i-1])
    body[name]=np.vstack([p[:i],end])
    subset.append({'array':name,'unchanged_prefix_points':i,'last_original_segment':[i-1,i],
        'end_interpolation_parameter':float(u),'old_end_mm':p[-1].tolist(),'new_end_mm':end.tolist(),
        'removed_final_straight_length_mm':13.,'new_cut_length_released':False})
np.savez_compressed(OUT/'body_partial_curves.npz',**body)
rows=[];limits=[]
# Use exactly the former pair-distance calculation; all earlier failed curves
# and results remain at their original paths with their original hashes.
loop=HELPER.read_text().split('rows=[];limits=[]',1)[1].split('\nresult={',1)[0]
exec(compile(loop,str(HELPER),'exec'),globals())
result={'status':'PASS' if all(r['status']=='PASS' for r in limits) else 'BLOCKED',
    'scope':'Two disjoint partial harness halves, lower temporary yaw datumZ193; no connecting service loop, anchor, crimp or cutting release',
    'source_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),'source_script_sha256':sha(NEW_SCRIPT),'source_pair_checker_sha256':sha(HELPER),
    'source_original_body_curves_sha256':sha(NEW_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'source_head_curves_sha256':sha(ORIGINAL_OUT/'departure_curves.npz'),
    'source_head_screen_sha256':sha(ORIGINAL_OUT/'departure_screen.json'),
    'source_original_coexistence_failure_sha256':sha(ORIGINAL_OUT/'coexistence_screen.json'),
    'candidate_body_curves_sha256':sha(OUT/'body_partial_curves.npz'),
    'subset_proof':subset,'datum_change_mm':[206.,193.],'head_pose_count':130,'pair_count':len(rows),
    'families':limits,'rows':rows,'source_geometry_preserved':True,
    'new_fixed_anchors':'NOT_TESTED','missing_service_loop':'NOT_TESTED','physical_pin_view':'BLOCKED',
    'photo_uncertainties':'NOT_TESTED','main_applied':False,'manufacturing_release':False,'whole_harness':'BLOCKED'}
(OUT/'coexistence_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_LOWER_STAGING_DONE',result['status'],len(rows),flush=True)
