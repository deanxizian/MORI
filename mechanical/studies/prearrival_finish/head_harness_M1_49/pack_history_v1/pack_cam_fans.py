"""Select four simultaneous CAM fan connections without changing any solid."""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import np,sha
from common import P
from validate import rigidtr
from curve_clearance import prepared,pair,self_clear
from upper_pack_geometry import trimmed,refined
read=lambda n:json.loads((HERE/n).read_text());started=time.time()
lower=read('front_lower_verification.json');upper=read('cam_upper_screen.json');joint=read('upper_lower_pairs.json');front=read('front_route_screen.json')
assert lower['status']==upper['status']==joint['status']=='PASS'
for report in [lower,upper,joint]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in lower['inputs'].items():assert sha(HERE/p)==h,p
for p,h in joint['inputs'].items():assert sha(HERE/p)==h,p
low=np.load(HERE/'front_lower_curves.npz');neck=np.load(HERE/'front_neck_candidates.npz');up=np.load(HERE/'cam_upper_candidates.npz')
assert sha(HERE/'front_lower_curves.npz')==lower['curve_sha256']
assert sha(HERE/'cam_upper_candidates.npz')==upper['curve_sha256']
report_names=['upper_fan_front_pin1_screen.json','upper_fan_screen.json','upper_fan_front_screen.json']
curve_names=['upper_fan_front_pin1_candidates.npz','upper_fan_candidates.npz','upper_fan_front_candidates.npz']
options={i:[] for i in range(1,5)};native={};metadata={};all_inputs={}
for rn,cn in zip(report_names,curve_names):
    report=read(rn);arrays=np.load(HERE/cn)
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
    assert sha(HERE/cn)==report['curve_sha256']
    for p,h in report['inputs'].items():assert sha(HERE/p)==h,p
    all_inputs.update({rn:sha(HERE/rn),cn:sha(HERE/cn)})
    for block in report['rows']:
        pin=block['pin']
        for j,row in enumerate(block['candidates']):
            key=f'{rn.removesuffix("_screen.json")}_pin{pin}_{j}'
            native[key]=arrays[row['id']];metadata[key]=row;options[pin].append(key)
            assert np.linalg.norm(native[key][0]-low[f'pin{pin}_y0'][-1])<1e-6
original_options={p:len(v) for p,v in options.items()}
lower_rows={r['slot']:r for r in [lower['selected']]+lower['other_selected']}
lower_items={};lower_raw={}
for yaw in range(-60,61,10):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
    for i,spec in enumerate(P['neck_harness_capacity']['wire_allocations']):
        r=lower_rows.get(i);p=low[f'pin{r["pin"]}_y{yaw}'] if r else neck[f'wire{i}_y{yaw}']
        p=p@inv[:3,:3].T+inv[:3,3]
        error=max(front['local_chord_error_mm'],r['chord_error_mm']) if r else front['local_chord_error_mm']
        lower_items[i,yaw]=prepared(p,spec['OD_mm']/2,error);lower_raw[i,yaw]=p
upper_raw={};upper_items={}
for pin,pitch,trim in itertools.product(range(1,5),range(-20,26,5),[0.,2.,4.]):
    p=trimmed(up[f'slot{pin-1}_pitch{pitch}'],trim)
    upper_raw[pin,pitch,trim]=p
    upper_items[pin,pitch,trim]=prepared(refined(p),.3302,.0003)
fan_items={k:prepared(refined(p),.3302,metadata[k]['chord_error_mm']) for k,p in native.items()}
upper_self=[]
for pin,pitch in itertools.product(range(1,5),range(-20,26,5)):
    r=self_clear(upper_items[pin,pitch,0.])
    upper_self.append(dict(pin=pin,pitch=pitch,**r))
assert all(r['status']=='PASS' for r in upper_self),upper_self
print('CAM_UPPER_SELF',len(upper_self),'PASS',flush=True)
prefilter=[]
for pin in range(1,5):
    accepted=[];own_slot=next(i for i,r in lower_rows.items() if r['pin']==pin)
    for key in options[pin]:
        fan=native[key];m=metadata[key];trim=m['anchor_trim_mm'];a=fan_items[key]
        bad=None;proofs=[]
        # All other lower segments must coexist with this fixed-yaw fan.
        for yaw,i in itertools.product(range(-60,61,10),range(11)):
            if i==own_slot:continue
            result=pair(a,lower_items[i,yaw])
            if result['status']!='PASS':bad=dict(kind='other_lower',slot=i,yaw=yaw,**result);break
        if not bad:
            for yaw in range(-60,61,10):
                prefix=lower_raw[own_slot,yaw]
                curve=np.vstack([prefix,fan[1:]])
                error=max(a['error'],lower_items[own_slot,yaw]['error'])
                result=self_clear(prepared(curve,.3302,error),indices=range(len(prefix)-1,len(curve)))
                if result['status']!='PASS':bad=dict(kind='own_lower_self',yaw=yaw,**result);break
        if not bad:
            for pitch in range(-20,26,5):
                suffix=upper_raw[pin,pitch,trim]
                assert np.linalg.norm(fan[-1]-suffix[0])<1e-5
                curve=np.vstack([fan,suffix[1:]])
                result=self_clear(prepared(curve,.3302,max(a['error'],.0003)),indices=range(len(fan)))
                if result['status']!='PASS':bad=dict(kind='own_upper_self',pitch=pitch,**result);break
        prefilter.append(dict(id=key,status='BLOCKED' if bad else 'PASS',failure=bad))
        if not bad:accepted.append(key)
    options[pin]=sorted(accepted,key=lambda k:metadata[k]['length_mm']-metadata[k]['anchor_trim_mm'])
    print('CAM_FAN_PREFILTER',pin,len(accepted),'of',original_options[pin],flush=True)
cache={};cross_cache={}
def fan_upper(key,pin,trim):
    k=(key,pin,trim)
    if k not in cross_cache:
        failures=[];bounds=[]
        for pitch in range(-20,26,5):
            r=pair(fan_items[key],upper_items[pin,pitch,trim]);bounds.append(r['gap_lower_bound_mm'])
            if r['status']!='PASS':failures.append(dict(pitch=pitch,**r));break
        cross_cache[k]=dict(status='BLOCKED' if failures else 'PASS',minimum_gap_bound_mm=min(bounds),failures=failures)
    return cross_cache[k]
def compatible(a,b):
    k=tuple(sorted([a,b]))
    if k not in cache:
        ra=metadata[a];rb=metadata[b];r=pair(fan_items[a],fan_items[b])
        if r['status']=='PASS':
            x=fan_upper(a,rb['pin'],rb['anchor_trim_mm']);y=fan_upper(b,ra['pin'],ra['anchor_trim_mm'])
            cache[k]=dict(status='PASS' if x['status']==y['status']=='PASS' else 'BLOCKED',fans=r,a_to_upper_b=x,b_to_upper_a=y)
        else:cache[k]=dict(status='BLOCKED',fans=r)
    return cache[k]['status']=='PASS'
def choose(chosen):
    if len(chosen)==4:return chosen
    for key in options[len(chosen)+1]:
        if all(compatible(key,old) for old in chosen):
            result=choose(chosen+[key])
            if result:return result
    return None
selected=choose([]);joined={};joins=[];lengths=[]
if selected:
    for key in selected:
        row=metadata[key];pin=row['pin'];fan=native[key];vals=[]
        for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
            tr=np.asarray(rigidtr(yaw,0));suffix=upper_raw[pin,pitch,row['anchor_trim_mm']]
            f=fan@tr[:3,:3].T+tr[:3,3];u=suffix@tr[:3,:3].T+tr[:3,3];l=low[f'pin{pin}_y{yaw}']
            join_errors=[float(np.linalg.norm(l[-1]-f[0])),float(np.linalg.norm(f[-1]-u[0]))]
            assert max(join_errors)<1e-5
            p=np.vstack([l,f[1:],u[1:]])
            joined[f'pin{pin}_y{yaw}_p{pitch}']=p
            vals.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
            joins.append(dict(pin=pin,yaw=yaw,pitch=pitch,errors_mm=join_errors))
        lengths.append(dict(pin=pin,minimum_polygon_length_mm=min(vals),maximum_polygon_length_mm=max(vals),variation_mm=max(vals)-min(vals),not_supplier_cut_length=True))
    np.savez_compressed(HERE/'cam_joined_candidates.npz',**joined)
result=dict(status='PASS' if selected else 'BLOCKED',source_blend_sha256=lower['source_blend_sha256'],sources=lower['sources'],
    inputs={**all_inputs,**{n:sha(HERE/n) for n in ['front_lower_verification.json','front_lower_curves.npz','front_neck_candidates.npz','cam_upper_screen.json','cam_upper_candidates.npz','upper_lower_pairs.json','curve_clearance.py','upper_pack_geometry.py']}},
    prefilter=prefilter,upper_self=upper_self,option_counts={p:len(v) for p,v in options.items()},
    selected=[dict(metadata[k],key=k) for k in selected] if selected else [],
    compatibility_checks=[dict(a=a,b=b,**r) for (a,b),r in cache.items()],
    joins=joins,lengths=lengths,curve_sha256=sha(HERE/'cam_joined_candidates.npz') if selected else None,
    proof_composition='Each fan was checked against current solids; revised lower wire/self checks, upper mutual and upper/lower checks are input proofs. New fan/self/lower/upper/fan interactions checked here.',
    scope='Four continuous CAM curves with finite13yaw/10pitch geometry, plus seven local capacity wires; crimp ends remain assumptions',
    main_changed=False,full_harness='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',physical_behavior='NOT_TESTED',
    supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(HERE/'cam_joined_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_FAN_PACK_DONE',result['status'],len(cache),lengths,flush=True)
