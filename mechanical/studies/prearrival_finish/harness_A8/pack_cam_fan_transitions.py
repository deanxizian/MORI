"""Compose the checked pieces by testing every transition-to-transition pair."""
from pathlib import Path
PACK_FAN_SCRIPT=Path(__file__).resolve();PACK_FAN_ROOT=PACK_FAN_SCRIPT.parent
PACK_FAN_HELPER=PACK_FAN_ROOT/'plan_cam_yaw_fan_v4.py';__file__=str(PACK_FAN_HELPER)
exec(compile(PACK_FAN_HELPER.read_text().split('\nrng=np.random.default_rng',1)[0],str(PACK_FAN_HELPER),'exec'),globals())
__file__=str(PACK_FAN_SCRIPT)
OUT=PACK_FAN_ROOT/'cam_fan_in/four_bend_transition'
pool=json.loads((OUT/'pool.json').read_text());assert pool['status']=='PASS'
math_report=json.loads((OUT/'math_bounds.json').read_text());assert math_report['status']=='PASS'
arrays=np.load(OUT/'curves.npz');samples={};pairs=[];compat={};started=time.time();individual=[]
for row in pool['rows']:
    for i,c in enumerate(row['candidates']):
        points=arrays[f'pin{row["pin"]}_candidate{i}'];sample=fine(points,step=.01);error=c['curve_error_bound_mm']
        # Earlier search control flow checked these, but its record overwrote
        # the connection summary with a null source-hit result. Re-run all
        # evidence here instead of treating that null as a passing summary.
        self_result=self_check(sample,error);connections=local_connections(sample,error,row['pin'])
        source_hit=fixed_yaw_source(points,error)
        good=self_result['status']=='PASS' and connections['status']=='PASS' and source_hit is None
        individual.append({'pin':row['pin'],'candidate':i,'status':'PASS' if good else 'BLOCKED',
            'self':self_result,'connections':connections,'source_hit':source_hit})
        samples[row['pin'],i]=(sample,error)
        print('FAN_REPLAY',row['pin'],i,individual[-1]['status'],flush=True)
for a,b in itertools.combinations(range(1,5),2):
    for ia,ib in itertools.product(range(len(pool['rows'][a-1]['candidates'])),range(len(pool['rows'][b-1]['candidates']))):
        aa,ea=samples[a,ia];bb,eb=samples[b,ib];pr=pair(aa,bb,ea,eb)
        pairs.append({'pins':[a,b],'candidates':[ia,ib],**pr});compat[a,ia,b,ib]=pr['status']=='PASS'
    print('FAN_PAIR',a,b,'failed',sum(r['status']!='PASS' for r in pairs),flush=True)
assignments=[]
for choice in itertools.product(*(range(len(r['candidates'])) for r in pool['rows'])):
    if all(r['status']=='PASS' for r in individual if choice[r['pin']-1]==r['candidate']) and all(compat[a,choice[a-1],b,choice[b-1]] for a,b in itertools.combinations(range(1,5),2)):
        assignments.append(list(choice))
result={'status':'PASS' if assignments else 'BLOCKED','source_script_sha256':sha(PACK_FAN_SCRIPT),
    'source_helper_sha256':sha(PACK_FAN_HELPER),'source_pool_sha256':sha(OUT/'pool.json'),
    'source_curves_sha256':sha(OUT/'curves.npz'),'source_math_sha256':sha(OUT/'math_bounds.json'),
    'source_CAM_bundle_sha256':sha(upper/'packing.json'),'source_main_sha256':source_hash,
    'individual_replay':individual,'pairs':pairs,'assignments':assignments,'elapsed_s':time.time()-started,
    'scope':'All four fixed-yaw transitions mutually packed; each also passed source solids, all moving CAM loops and all body prefixes. This closes nominal prescribed four-wire path connectivity only.',
    'head_poses':130,'main_applied':False,'anchors':'NOT_TESTED','whole_harness':'BLOCKED',
    'continuous_collision':'NOT_TESTED','manufacturing_release':False}
(OUT/'packing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FOUR_WIRE_FAN_PACK',result['status'],len(assignments),flush=True)
