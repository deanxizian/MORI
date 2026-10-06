"""Check ordered CAM fans and pitch loops against the eleven local neck curves.

This intentionally excludes body prefixes. Each electrical pin retains its
own upper loop. Existing proofs are reused only with matching source hashes.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/cam_cross_order_upper';OUT=BASE/'local_join'
OUT.mkdir(parents=True,exist_ok=True)
LANE=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import trimmed,refined
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
fr=read(BASE/'fan_screen.json');nr=read(LANE/'neck_screen.json')
ur=read(HERE/'cam_upper_screen.json');old=read(HERE/'cam_joined_verification.json')
mutual=read(HERE/'upper_lower_pairs.json')
for report in [fr,nr,ur,old,mutual]:
    assert report['status']=='PASS'
    for name,h in report['sources'].items():assert sha(ROOT/name)==h,name
    for name,h in report['inputs'].items():
        root=ROOT if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE
        assert sha(root/name)==h,name
for folder,name,report in [(BASE,'fan_candidates.npz',fr),(LANE,'neck_candidates.npz',nr),(HERE,'cam_upper_candidates.npz',ur)]:
    assert sha(folder/name)==report['curve_sha256']
fans=np.load(BASE/'fan_candidates.npz');neck=np.load(LANE/'neck_candidates.npz');upper=np.load(HERE/'cam_upper_candidates.npz')
lane=next(r for r in nr['results'] if r['status']=='PASS');slot_for={1:7,2:10,3:9,4:8}
raw_low={};low_items={};local_self=[]
for yaw in range(-60,61,10):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
    for slot in range(11):
        p=neck[f'z149.0_dip0.6_wire{slot}_y{yaw}'];p=p@inv[:3,:3].T+inv[:3,3]
        raw_low[slot,yaw]=p;low_items[slot,yaw]=prepared(p,nr['OD_mm'][slot]/2,lane['chord_error_mm'])
    # All local shapes differ only by a Z rotation; the largest radius bounds
    # every other conductor's self approach at this yaw sample.
    local_self.append(dict(yaw=yaw,**self_clear(low_items[0,yaw])))
assert all(r['status']=='PASS' for r in local_self)
assert len(old['upper_self'])==40 and all(r['status']=='PASS' for r in old['upper_self'])
assert len(mutual['upper_mutual'])==60 and all(r['status']=='PASS' for r in mutual['upper_mutual'])
raw_up={};up_items={}
for pin,pitch,trim in itertools.product(range(1,5),range(-20,26,5),[0.,2.,4.]):
    p=trimmed(upper[f'slot{pin-1}_pitch{pitch}'],trim)
    raw_up[pin,pitch,trim]=p;up_items[pin,pitch,trim]=prepared(refined(p),.3302,.0003)
upper_lower=[]
for yaw,pin,pitch,slot in itertools.product(range(-60,61,10),range(1,5),range(-20,26,5),range(11)):
    r=pair_threshold(up_items[pin,pitch,0.],low_items[slot,yaw])
    upper_lower.append(dict(yaw=yaw,pin=pin,pitch=pitch,slot=slot,**r))
    if r['status']!='PASS':print('ORDER_UPPER_LOWER_HIT',upper_lower[-1],flush=True)
upper_lower_ok=all(r['status']=='PASS' for r in upper_lower)
print('ORDER_UPPER_LOWER_DONE',upper_lower_ok,len(upper_lower),flush=True)
metadata={r['id']:r for block in fr['rows'] for r in block['candidates']}
options={pin:sorted([k for k,r in metadata.items() if r['pin']==pin],key=lambda k:metadata[k]['length_mm']-metadata[k]['anchor_trim_mm']) for pin in range(1,5)}
fan_items={k:prepared(refined(fans[k]),.3302,r['chord_error_mm']) for k,r in metadata.items()}
prefilter={};cache={};cross={}
def ready(key):
    if key in prefilter:return prefilter[key]['status']=='PASS'
    fan=fans[key];m=metadata[key];pin=m['pin'];trim=m['anchor_trim_mm'];own=slot_for[pin];bad=None
    for yaw,slot in itertools.product(range(-60,61,10),range(11)):
        if slot==own:continue
        r=pair_threshold(fan_items[key],low_items[slot,yaw])
        if r['status']!='PASS':bad=dict(kind='other_local',yaw=yaw,slot=slot,**r);break
    if not bad:
        for yaw in range(-60,61,10):
            p=raw_low[own,yaw];assert np.linalg.norm(p[-1]-fan[0])<1e-5
            q=np.vstack([p,fan[1:]])
            r=self_clear(prepared(q,.3302,max(lane['chord_error_mm'],m['chord_error_mm'])),indices=range(len(p)-1,len(q)))
            if r['status']!='PASS':bad=dict(kind='own_lower_self',yaw=yaw,**r);break
    if not bad:
        for pitch in range(-20,26,5):
            u=raw_up[pin,pitch,trim];assert np.linalg.norm(fan[-1]-u[0])<1e-5
            q=np.vstack([fan,u[1:]])
            r=self_clear(prepared(q,.3302,max(m['chord_error_mm'],.0003)),indices=range(len(fan)))
            if r['status']!='PASS':bad=dict(kind='own_upper_self',pitch=pitch,**r);break
    prefilter[key]=dict(status='BLOCKED' if bad else 'PASS',failure=bad)
    print('ORDER_UPPER_PREFILTER',key,prefilter[key]['status'],flush=True)
    return not bad
def against_upper(key,pin,trim):
    k=key,pin,trim
    if k not in cross:
        rows=[]
        for pitch in range(-20,26,5):
            r=pair_threshold(fan_items[key],up_items[pin,pitch,trim]);rows.append(dict(pitch=pitch,**r))
            if r['status']!='PASS':break
        cross[k]=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',checks=rows)
    return cross[k]
def compatible(a,b):
    k=tuple(sorted([a,b]))
    if k not in cache:
        ra=metadata[a];rb=metadata[b];r=pair_threshold(fan_items[a],fan_items[b])
        if r['status']=='PASS':
            x=against_upper(a,rb['pin'],rb['anchor_trim_mm']);y=against_upper(b,ra['pin'],ra['anchor_trim_mm'])
            cache[k]=dict(status='PASS' if x['status']==y['status']=='PASS' else 'BLOCKED',fans=r,a_to_upper_b=x,b_to_upper_a=y)
        else:cache[k]=dict(status='BLOCKED',fans=r)
    return cache[k]['status']=='PASS'
def choose(chosen):
    if len(chosen)==4:return chosen
    for key in options[len(chosen)+1]:
        if all(compatible(key,previous) for previous in chosen) and ready(key):
            result=choose(chosen+[key])
            if result:return result
    return None
selected=choose([]) if upper_lower_ok else None
joined={};joins=[];lengths=[]
if selected:
    for key in selected:
        row=metadata[key];pin=row['pin'];fan=fans[key];values=[]
        for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
            l=raw_low[slot_for[pin],yaw];u=raw_up[pin,pitch,row['anchor_trim_mm']]
            q=np.vstack([l,fan[1:],u[1:]]);tr=np.asarray(rigidtr(yaw,0))
            joined[f'pin{pin}_y{yaw}_p{pitch}']=q@tr[:3,:3].T+tr[:3,3]
            values.append(float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()))
            errors=[float(np.linalg.norm(l[-1]-fan[0])),float(np.linalg.norm(fan[-1]-u[0]))]
            assert max(errors)<1e-5
            joins.append(dict(pin=pin,yaw=yaw,pitch=pitch,errors_mm=errors))
        lengths.append(dict(pin=pin,polygon_min_mm=min(values),polygon_max_mm=max(values),not_supplier_cut_length=True))
    np.savez_compressed(OUT/'cam_local_joined.npz',**joined)
ctx.assert_unchanged()
inputs=[BASE/'fan_screen.json',BASE/'fan_candidates.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz',HERE/'cam_upper_screen.json',HERE/'cam_upper_candidates.npz',HERE/'cam_joined_verification.json',HERE/'upper_lower_pairs.json',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py',HERE/'upper_pack_geometry.py']
report=dict(status='PASS' if selected else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    local_self=local_self,upper_self=old['upper_self'],upper_mutual=mutual['upper_mutual'],upper_lower=upper_lower,
    options={pin:len(rows) for pin,rows in options.items()},prefilter=[dict(id=k,**r) for k,r in prefilter.items()],
    compatibility=[dict(a=k[0],b=k[1],**r) for k,r in cache.items()],
    selected=[metadata[k] for k in selected] if selected else [],joins=joins,lengths=lengths,
    curve_sha256=sha(OUT/'cam_local_joined.npz') if selected else None,
    proof_reuse='Only unchanged upper loop self/mutual proofs reused after source and input hashes match. New local self, upper/local, fan interactions and junction remote-self checks are explicit.',
    join_arithmetic_tolerance_mm=1e-5,
    scope='Four CAM upper connections and eleven Z149 balanced neck curves only; mechanical slots 7/10/9/8 by logical pin1/2/3/4, no body prefixes included',
    lower_nine='NOT_TESTED here',full_harness='BLOCKED',wire_selection='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    main_changed=False,physical_qualification='NOT_TESTED',supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'local_join_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORDER_UPPER_PACK_DONE',report['status'],report['elapsed_s'],flush=True)
