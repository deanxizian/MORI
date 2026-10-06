"""Refine the failed pair gaps locally without changing sources or allowances.

Retain two fully checked candidate curves, then search small geometric changes
to the other two. The original failed packing result is preserved unchanged.
"""
from pathlib import Path
BUNDLE_SCRIPT=Path(__file__).resolve();BUNDLE_DIR=BUNDLE_SCRIPT.parent
BUNDLE_HELPER=BUNDLE_DIR/'check_cam_pitch_flex_packing.py';__file__=str(BUNDLE_HELPER)
exec(compile(BUNDLE_HELPER.read_text().split('\nbody_samples={',1)[0],str(BUNDLE_HELPER),'exec'),globals())
__file__=str(BUNDLE_SCRIPT)
BASE_OUT=OUT;OUT=BUNDLE_DIR/'cam_pitch_flex/bundle';OUT.mkdir(exist_ok=True)
family='left';endpoint_tangent=np.array([1.,0.,0.]);rng=np.random.default_rng(202610032)
chosen={};cache={};logs=[];t0=time.time()
def register(pin,c):
    chosen[pin]=c
    for p in c['poses']:
        cs=[np.array(x) for x in p['controls_mm']];points,error=sampled(cs,400)
        tr=np.asarray(rigidtr(0,p['pitch_deg']));tail=head_curves[f'left_slot{pin-1}']@tr[:3,:3].T+tr[:3,3]
        joined=np.vstack([points,tail[-2::-1]])
        cache[pin,p['pitch_deg']]=(fine(joined),max(error,head_family['curve_error_bounds_mm'][pin-1]))
for pin,i in [(1,0),(3,5)]:register(pin,pool['rows'][pin-1]['candidates'][i])

for pin,original in [(2,2),(4,5)]:
    base=pool['rows'][pin-1]['candidates'][original];a=body_curves[f'pin{pin}_yaw0'][-1]
    b=head_curves[f'left_slot{pin-1}'][-1];counts=Counter();examples={};winner=None
    for trial in range(2500):
        counts['tried']+=1
        # Later trials widen only the local control envelope, not any obstacle
        # or gap/bend requirement. Hardware and connector datums do not move.
        spread=1.0 if trial<1000 else 2.0
        mid=np.array(base['parameters']['mid'])+rng.normal(0,1.4*spread,3)
        tangent=np.array(base['parameters']['tangent'])+rng.normal(0,.07*spread,3);tangent/=np.linalg.norm(tangent)
        handles=np.maximum(2.,np.array(base['parameters']['handles'])+rng.normal(0,.9*spread,4))
        params={'mid':mid.tolist(),'tangent':tangent.tolist(),'handles':handles.tolist()}
        pitch_data={};lower=[];upper=[]
        for pitch in range(-20,26,5):
            tr=np.asarray(rigidtr(0,pitch));bp=b@tr[:3,:3].T+tr[:3,3];tb=endpoint_tangent@tr[:3,:3].T
            ll=[sum(curve_length(c) for c in make(a,bp,tb,params,d)) for d in [0.,15.]]
            if ll[1]<=ll[0]:break
            pitch_data[pitch]=(bp,tb);lower.append(ll[0]);upper.append(ll[1])
        if len(pitch_data)!=10 or max(lower)+.1>min(upper):counts['length_rejected']+=1;continue
        target=max(lower)+.1;poses=[];reason=None
        for pitch,(bp,tb) in pitch_data.items():
            low,high=0.,15.
            for _ in range(32):
                delta=(low+high)/2;cs=make(a,bp,tb,params,delta)
                if sum(curve_length(c) for c in cs)<target:low=delta
                else:high=delta
            delta=(low+high)/2;cs=make(a,bp,tb,params,delta)
            radius=min(min_radius(c,np.linspace(0,1,513)) for c in cs)
            if radius<REQUIRED_R+.06:reason='curvature';break
            points,error=sampled(cs,400);tr=np.asarray(rigidtr(0,pitch))
            tail=head_curves[f'left_slot{pin-1}']@tr[:3,:3].T+tr[:3,3]
            joined=np.vstack([points,tail[-2::-1]]);s=fine(joined)
            err=max(error,head_family['curve_error_bounds_mm'][pin-1])
            for other_pin in chosen:
                other,oe=cache[other_pin,pitch];r=pair(s,other,err,oe)
                if r['status']!='PASS':reason='wire_pair';break
            if reason:break
            hit=geom_check(cs,pitch,True)
            if hit:reason=hit['obstacle'];examples.setdefault(reason,hit);break
            poses.append({'pitch_deg':pitch,'height_adjustment_mm':delta,'controls_mm':[c.tolist() for c in cs],
                'length_mm':sum(curve_length(c) for c in cs),'minimum_sampled_radius_mm':radius,'chord_error_bound_mm':error})
        if reason:counts[reason+'_rejected']+=1;continue
        winner={'pin':pin,'geometric_slot':pin-1,'trial':trial,'parameters':params,'constant_length_mm':target,'poses':poses}
        register(pin,winner);break
    logs.append({'pin':pin,'status':'PASS' if winner else 'BLOCKED','counts':dict(counts),'examples':examples})
    print('PITCH_BUNDLE_REFINE',pin,logs[-1]['status'],dict(counts),round(time.time()-t0,1),flush=True)
    if not winner:break

rows=[];saved={}
for pin in range(1,5):
    cs=[chosen[pin]] if pin in chosen else []
    rows.append({'pin':pin,'slot_index':pin-1,'status':'PASS' if cs else 'BLOCKED','candidates':cs})
    for i,c in enumerate(cs):
        for p in c['poses']:
            points,_=sampled([np.array(x) for x in p['controls_mm']],400)
            saved[f'pin{pin}_candidate{i}_pitch{p["pitch_deg"]}']=points
np.savez_compressed(OUT/'flex_candidates.npz',**saved)
result={'status':'PASS' if len(chosen)==4 else 'BLOCKED','scope':'Local four-wire pair refinement; whole prefix/self checks must be replayed',
    'source_script_sha256':sha(BUNDLE_SCRIPT),'source_helper_sha256':sha(BUNDLE_HELPER),'source_original_pool_sha256':sha(BASE_OUT/'flex_pool.json'),
    'source_original_packing_sha256':sha(BASE_OUT/'packing.json'),'source_main_sha256':source_hash,
    'source_candidate_sha256':sha(candidate/'candidate.blend'),'seed':202610032,'rows':rows,'refinement_log':logs,
    'curves_sha256':sha(OUT/'flex_candidates.npz'),'required_radius_mm':REQUIRED_R,'wire_OD_mm':OD,'required_surface_gap_mm':.3,
    'family':'left','physical_pin_map':'ASSUMED photo registration, not actual mating cavity view',
    'anchors':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-t0}
(OUT/'flex_pool.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PITCH_BUNDLE_REFINE_DONE',result['status'],flush=True)
