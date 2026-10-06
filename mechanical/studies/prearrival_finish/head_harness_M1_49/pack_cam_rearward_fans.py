"""Jointly pack four rearward CAM transitions, loops and current neck curves.

All reuse is guarded by hashes. This is an independent route study. C6 is
still unapproved and no printed geometry is substituted in this upper check.
"""
from pathlib import Path
import argparse,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['rear3','rear5','rear7'],default='rear3')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
CASE=args.case;BASE=HERE/'remaining_routes/cam_rearward_fans'/CASE;OUT=BASE/'local_join';OUT.mkdir(exist_ok=True)
LOOP=HERE/'remaining_routes/cam_rearward_loops';LANE=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import trimmed,refined
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
fr=read(BASE/'fan_screen.json');nr=read(LANE/'neck_screen.json');lr=read(LOOP/'loop_screen.json');pr=read(LOOP/'refined_pairs.json')
for report in [fr,nr,lr,pr]:
    for name,h in {**report['sources'],**report['inputs']}.items():
        root=ROOT if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE
        assert sha(root/name)==h,name
assert fr['status']==nr['status']==pr['status']=='PASS'
loop_proof=next(r for r in lr['results'] if r['id']==CASE);pair_proof=next(r for r in pr['results'] if r['id']==CASE)
assert not loop_proof['hits'] and loop_proof['native_checks']==600
assert len(loop_proof['self_checks'])==40 and all(r['status']=='PASS' for r in loop_proof['self_checks'])
assert pair_proof['status']=='PASS' and len(pair_proof['mutual'])==60
for folder,name,r in [(BASE,'fan_candidates.npz',fr),(LANE,'neck_candidates.npz',nr),(LOOP,'curves.npz',lr)]:assert sha(folder/name)==r['curve_sha256']
fans=np.load(BASE/'fan_candidates.npz');neck=np.load(LANE/'neck_candidates.npz');loops=np.load(LOOP/'curves.npz')
lane=next(r for r in nr['results'] if r['status']=='PASS');slot_for={1:9,2:8,3:7,4:10}
raw_low={};low_items={};local_self=[]
for yaw in range(-60,61,10):
    inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
    for slot in range(11):
        p=neck[f'z149.0_dip0.6_wire{slot}_y{yaw}'];p=p@inv[:3,:3].T+inv[:3,3]
        raw_low[slot,yaw]=p;low_items[slot,yaw]=prepared(p,nr['OD_mm'][slot]/2,lane['chord_error_mm'])
    local_self.append(dict(yaw=yaw,**self_clear(low_items[0,yaw])))
assert all(r['status']=='PASS' for r in local_self)
raw_up={};up_items={}
for pin,pitch,trim in itertools.product(range(1,5),range(-20,26,5),[0.,2.,4.]):
    p=trimmed(loops[f'{CASE}_pin{pin}_pitch{pitch}'],trim)
    raw_up[pin,pitch,trim]=p;up_items[pin,pitch,trim]=prepared(refined(p),.3302,.0003)
upper_lower=[]
for yaw,pin,pitch,slot in itertools.product(range(-60,61,10),range(1,5),range(-20,26,5),range(11)):
    upper_lower.append(dict(yaw=yaw,pin=pin,pitch=pitch,slot=slot,**pair_threshold(up_items[pin,pitch,0.],low_items[slot,yaw])))
upper_lower_ok=all(r['status']=='PASS' for r in upper_lower)
print('REARWARD_UPPER_LOWER',CASE,upper_lower_ok,len(upper_lower),flush=True)
metadata={r['id']:r for block in fr['rows'] for r in block['candidates']}
options={pin:sorted([k for k,r in metadata.items() if r['pin']==pin],key=lambda k:metadata[k]['length_mm']-metadata[k]['anchor_trim_mm']) for pin in range(1,5)}
fan_items={k:prepared(refined(fans[k]),.3302,r['chord_error_mm']) for k,r in metadata.items()}
prefilter={};cache={};cross={};nodes=0
def ready(key):
    if key in prefilter:return prefilter[key]['status']=='PASS'
    fan=fans[key];m=metadata[key];pin=m['pin'];trim=m['anchor_trim_mm'];own=slot_for[pin];bad=None
    for pitch in range(-20,26,5):
        u=raw_up[pin,pitch,trim];assert np.linalg.norm(fan[-1]-u[0])<1e-5
        q=np.vstack([fan,u[1:]])
        r=self_clear(prepared(q,.3302,max(m['chord_error_mm'],.0003)),indices=range(len(fan)))
        if r['status']!='PASS':bad=dict(kind='own_upper_self',pitch=pitch,**r);break
    if not bad:
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
    prefilter[key]=dict(status='BLOCKED' if bad else 'PASS',failure=bad)
    if len(prefilter)%10==0:print('REARWARD_PREFILTER',CASE,len(prefilter),sum(r['status']=='PASS' for r in prefilter.values()),flush=True)
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
def choose(chosen,remaining):
    global nodes
    nodes+=1
    if not remaining:return chosen
    viable={pin:[k for k in keys if all(compatible(k,c) for c in chosen)] for pin,keys in remaining.items()}
    pin=min(viable,key=lambda p:len(viable[p]))
    for key in viable[pin]:
        if ready(key):
            result=choose(chosen+[key],{p:v for p,v in viable.items() if p!=pin})
            if result:return result
    return None
selected=choose([],options) if upper_lower_ok else None
joined={};joins=[];lengths=[];whole_pairs=[]
if selected:
    selected=sorted(selected,key=lambda k:metadata[k]['pin'])
    for key in selected:
        row=metadata[key];pin=row['pin'];fan=fans[key];values=[]
        for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
            l=raw_low[slot_for[pin],yaw];u=raw_up[pin,pitch,row['anchor_trim_mm']]
            q=np.vstack([l,fan[1:],u[1:]]);tr=np.asarray(rigidtr(yaw,0))
            joined[f'pin{pin}_y{yaw}_p{pitch}']=q@tr[:3,:3].T+tr[:3,3]
            values.append(float(np.linalg.norm(np.diff(q,axis=0),axis=1).sum()))
            errors=[float(np.linalg.norm(l[-1]-fan[0])),float(np.linalg.norm(fan[-1]-u[0]))];assert max(errors)<1e-5
            joins.append(dict(pin=pin,yaw=yaw,pitch=pitch,errors_mm=errors))
        lengths.append(dict(pin=pin,polygon_min_mm=min(values),polygon_max_mm=max(values),not_supplier_cut_length=True))
    error=max(lane['chord_error_mm'],.0003,max(metadata[k]['chord_error_mm'] for k in selected))
    for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
        items={pin:prepared(refined(joined[f'pin{pin}_y{yaw}_p{pitch}']),.3302,error) for pin in range(1,5)}
        for a,b in itertools.combinations(items,2):whole_pairs.append(dict(yaw=yaw,pitch=pitch,a=a,b=b,**pair(items[a],items[b])))
        if pitch==25:print('REARWARD_WHOLE_PAIRS',CASE,yaw,len(whole_pairs),flush=True)
    np.savez_compressed(OUT/'cam_local_joined.npz',**joined)
ctx.assert_unchanged()
inputs=[BASE/'fan_screen.json',BASE/'fan_candidates.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz',LOOP/'loop_screen.json',LOOP/'refined_pairs.json',LOOP/'curves.npz',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py',HERE/'upper_pack_geometry.py']
r=dict(status='PASS' if selected and len(whole_pairs)==780 and all(r['status']=='PASS' for r in whole_pairs) else 'BLOCKED',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},loop_case=CASE,local_self=local_self,
    upper_self=loop_proof['self_checks'],upper_mutual=pair_proof['mutual'],upper_lower=upper_lower,
    options={pin:len(keys) for pin,keys in options.items()},prefilter=[dict(id=k,**r) for k,r in prefilter.items()],
    compatibility=[dict(a=k[0],b=k[1],**r) for k,r in cache.items()],nodes=nodes,
    selected=[metadata[k] for k in selected] if selected else [],whole_pairs=whole_pairs,joins=joins,lengths=lengths,
    curve_sha256=sha(OUT/'cam_local_joined.npz') if selected else None,
    proof_reuse='Hash-verified native loop/individual fan screens and refined loop mutual results; all new local joins, transition crosses and780 complete four-wire pairs are explicit',
    scope='Four connected local neck to actual CAM endpoint reference routes across13yaw by10pitch poses; excludes lower body prefixes and other upper endpoints',
    lower_nine='NOT_TESTED here',full_harness='BLOCKED',wire_selection='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    main_changed=False,C6_main_applied=False,physical_qualification='NOT_TESTED',supplier_cut_lengths_released=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'local_join_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('REARWARD_PACK_DONE',CASE,r['status'],r['elapsed_s'],flush=True)
