"""Use the alternate left CAM departure for the same bounded flex search.

Preserve the earlier forward-only failed trial and its reproducible source.
The physical pin order, selected connector and main geometry stay untouched.
"""
from pathlib import Path
SIDE_SCRIPT=Path(__file__).resolve();SIDE_DIR=SIDE_SCRIPT.parent
SIDE_HELPER=SIDE_DIR/'plan_cam_pitch_flex.py'
__file__=str(SIDE_HELPER)
exec(compile(SIDE_HELPER.read_text().split('\nall_rows=[];saved={}',1)[0],str(SIDE_HELPER),'exec'),globals())
__file__=str(SIDE_SCRIPT)
OUT=SIDE_DIR/'cam_pitch_flex/side';OUT.mkdir(exist_ok=True)
family='left';endpoint_tangent=np.array([1.,0.,0.])
rng=np.random.default_rng(202610031)
search=SIDE_HELPER.read_text().split('all_rows=[];saved={}',1)[1].split('\nnp.savez_compressed',1)[0]
search='all_rows=[];saved={}'+search
search=search.replace('range(16000)','range(80000)')
search=search.replace('rng.uniform(-28,28),rng.uniform(-28,28),rng.uniform(217,255)',
    'rng.uniform(-35,22),rng.uniform(-27,23),rng.uniform(222,253)')
search=search.replace('rng.normal(0,8,3)','rng.normal(0,18,3)')
search=search.replace('rng.uniform(3,14,4)','rng.uniform(4,17,4)')
exec(compile(search,str(SIDE_HELPER),'exec'),globals())
np.savez_compressed(OUT/'flex_candidates.npz',**saved)
result={'status':'PASS' if all(r['candidates'] for r in all_rows) else 'BLOCKED',
    'scope':'Individual fixed-length left-departure continuation pools; no four-wire packing, actual pin mapping or anchor approval',
    'source_script_sha256':sha(SIDE_SCRIPT),'source_helper_sha256':sha(SIDE_HELPER),
    'source_main_sha256':source_hash,'source_candidate_sha256':sha(candidate/'candidate.blend'),
    'body_partial_sha256':sha(SIDE_DIR/'cam_pitch_port/lower_staging/body_partial_curves.npz'),
    'head_partial_sha256':sha(SIDE_DIR/'cam_pitch_port/departure_curves.npz'),
    'curves_sha256':sha(OUT/'flex_candidates.npz'),'family':family,'seed':202610031,'rows':all_rows,
    'required_radius_mm':REQUIRED_R,'wire_OD_mm':OD,'required_surface_gap_mm':.3,
    'physical_pin_map':'BLOCKED','wire_self_and_mutual_contacts':'NOT_TESTED','prefix_continuation_contacts':'NOT_TESTED',
    'continuous_motion':'NOT_TESTED','anchors':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
    'manufacturing_release':False,'elapsed_s':time.time()-t0}
(OUT/'flex_pool.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PITCH_FLEX_SIDE_DONE',result['status'],flush=True)
