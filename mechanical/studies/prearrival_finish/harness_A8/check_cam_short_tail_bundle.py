"""Validate the complete four CAM-side loop/tail assemblies together.

The lower body prefixes are still disjoint: their fan-in is absent. A PASS
here must never be reported as a complete robot harness or cutting drawing.
"""
from pathlib import Path
BUNDLE_SCRIPT=Path(__file__).resolve();BUNDLE_ROOT=BUNDLE_SCRIPT.parent
BUNDLE_HELPER=BUNDLE_ROOT/'plan_cam_following_arc.py';__file__=str(BUNDLE_HELPER)
exec(compile(BUNDLE_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(BUNDLE_HELPER),'exec'),globals())
__file__=str(BUNDLE_SCRIPT)
from mathutils.kdtree import KDTree
PACK_HELPER_PATH=BUNDLE_ROOT/'check_cam_pitch_flex_packing.py'
exec(compile('def fine'+PACK_HELPER_PATH.read_text().split('def fine',1)[1].split('\nbody_samples=',1)[0],str(PACK_HELPER_PATH),'exec'),globals())
OUT=BUNDLE_ROOT/'cam_fan_in/short_tail_v2'
tails=[np.load(OUT/'tails.npz')[f'slot{i}'] for i in range(4)]
pool_path=OUT/'screen.json';pool=json.loads(pool_path.read_text());assert pool['status']=='PASS'
saved=np.load(OUT/'curves.npz');body=np.load(BUNDLE_ROOT/'cam_pitch_port/lower_staging/body_partial_curves.npz')
body_meta=json.loads((BUNDLE_ROOT/'body_prefix_v2/body_to_yaw_motion.json').read_text())
body_error=max(r['curve_error_bound_mm'] for r in body_meta['rows'])
tail_error=tr['selected']['curve_error_bound_mm']
body_bounds={(pin,yaw):(body[f'pin{pin}_yaw{yaw}'].min(0),body[f'pin{pin}_yaw{yaw}'].max(0)) for pin in range(1,5) for yaw in range(-60,61,10)}
body_samples={};reports=[];started=time.time()
for idx,record in enumerate(pool['selected']):
    rows=[];pairs=[];prefix_rows=[];cached={};failures=[]
    for p in record['poses']:
        pitch=p['pitch_deg'];mat=np.asarray(rigidtr(0,pitch));err=max(tail_error,p['curve_error_bound_mm'])
        for slot in range(4):
            core=saved[f'candidate{idx}_slot{slot}_pitch{pitch}']
            tail=tails[slot]@mat[:3,:3].T+mat[:3,3]
            assert np.linalg.norm(core[-1]-tail[-1])<1e-5
            joined=np.vstack([core,tail[-2::-1]])
            sample=fine(joined,step=.01);cached[slot]=(sample,err)
            self_result=self_check(sample,err)
            rows.append({'slot':slot,'pitch_deg':pitch,**self_result})
            if self_result['status']!='PASS':failures.append({'type':'self','slot':slot,'pitch_deg':pitch,**self_result})
            for yaw in range(-60,61,10):
                ytr=np.asarray(rigidtr(yaw,0));q=sample[0]@ytr[:3,:3].T+ytr[:3,3]
                low=q.min(0);high=q.max(0)
                for pin in range(1,5):
                    blo,bhi=body_bounds[pin,yaw]
                    box_gap=float(np.linalg.norm(np.maximum(np.maximum(blo-high,low-bhi),0.)))-OD-err-body_error-1e-4
                    if box_gap>=.3:pr={'status':'PASS','gap_bound_mm':box_gap,'method':'Exact curve-point AABBs minus both chord errors and wire diameter'}
                    else:
                        if (pin,yaw) not in body_samples:body_samples[pin,yaw]=fine(body[f'pin{pin}_yaw{yaw}'],step=.01)
                        pr=pair((q,sample[1],None,sample[3]),body_samples[pin,yaw],err,body_error)
                    prefix_rows.append({'slot':slot,'pin':pin,'yaw_deg':yaw,'pitch_deg':pitch,**pr})
                    if pr['status']!='PASS':failures.append({'type':'prefix','slot':slot,'pin':pin,'yaw_deg':yaw,'pitch_deg':pitch,**pr})
        for a,b in itertools.combinations(range(4),2):
            sa,ea=cached[a];sb,eb=cached[b];row=pair(sa,sb,ea,eb)
            pairs.append({'slots':[a,b],'pitch_deg':pitch,**row})
            if row['status']!='PASS':failures.append({'type':'mutual','slots':[a,b],'pitch_deg':pitch,**row})
        print('PAR_BUNDLE_POSE',idx,pitch,'failures',len(failures),round(time.time()-started,1),flush=True)
        if failures:break
    reports.append({'candidate':idx,'status':'PASS' if not failures else 'BLOCKED','failures':failures,
        'self_checks':rows,'mutual_checks':pairs,'body_prefix_checks':prefix_rows,
        'minimum_mutual_gap_bound_mm':min((r['gap_bound_mm'] for r in pairs),default=None),
        'minimum_prefix_gap_bound_mm':min((r['gap_bound_mm'] for r in prefix_rows),default=None)})
result={'status':'PASS' if any(r['status']=='PASS' for r in reports) else 'BLOCKED',
    'source_script_sha256':sha(BUNDLE_SCRIPT),'source_helper_sha256':sha(BUNDLE_HELPER),
    'source_pack_helper_sha256':sha(PACK_HELPER_PATH),'source_pool_sha256':sha(pool_path),
    'source_curves_sha256':sha(OUT/'curves.npz'),'source_main_sha256':source_hash,
    'source_body_prefix_sha256':sha(BUNDLE_ROOT/'cam_pitch_port/lower_staging/body_partial_curves.npz'),
    'source_tail_curves_sha256':sha(OUT/'tails.npz'),'rows':reports,
    'scope':'Whole four CAM-side loops/tails; disjoint body prefixes are obstacles. Fixed-yaw fan-in is not yet designed.',
    'continuous_motion':'NOT_TESTED','anchors':'NOT_TESTED','whole_harness':'BLOCKED',
    'main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PAR_BUNDLE_DONE',result['status'],flush=True)
