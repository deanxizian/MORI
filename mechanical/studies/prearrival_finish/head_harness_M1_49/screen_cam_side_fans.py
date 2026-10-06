"""Connect the checked side CAM loops to the neck without moving native solids."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/neck_side_tail_gentle';S=HERE/'remaining_routes/cam_side_following'
OUT=HERE/'remaining_routes/cam_side_fans';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from upper_curve_geometry import make
from curve_clearance import prepared,pair
from curve_self_partition import self_clear
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
nr=read(N/'join_screen.json');sr=read(S/'loop_screen.json')
for r in [nr,sr]:
    assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(N/'neck_curves.npz')==nr['neck_curve_sha256'] and sha(S/'curves.npz')==sr['curve_sha256']
nc=np.load(N/'neck_curves.npz');uc=np.load(S/'curves.npz')
mapping={1:9,2:8,3:7,4:10};yaws=range(-60,61,10);pitches=range(-20,26,5)
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
neck={};upper={};neck_local={}
for y in yaws:
    mat=np.linalg.inv(np.asarray(rigidtr(y,0)))
    for slot in range(11):
        p=nc[f'wire{slot}_y{y}']@mat[:3,:3].T+mat[:3,3];neck_local[slot,y]=p
        neck[slot,y]=prepared(refined(p,.01),nr['OD_mm'][slot]/2,.0003)
for pin,y,pitch in itertools.product(mapping,yaws,pitches):
    upper[pin,y,pitch]=prepared(refined(uc[f'pin{pin}_y{y}_p{pitch}'],.01),.3302,.0003)
pools={p:[] for p in mapping};attempts=[];fan_points={};fan_items={}
for pin,slot in mapping.items():
    leads=[0.,.5,1.,1.5,2.] if pin in [1,2] else [0.,1.,2.,4.,6.,8.,10.]
    start=nc[f'wire{slot}_y0'][-1];end=uc[f'pin{pin}_y0_p0'][0]
    for lead in leads:
        result=make(start,end,7.,lead=lead,step=.01)
        row=dict(pin=pin,lead_mm=lead,radius_mm=7.,status='BLOCKED',stage='geometry',hits=[],counts={})
        if result is None:attempts.append(row);continue
        p,length,error=result;item=prepared(p,.3302,max(error,.0003));row.update(exact_length_mm=float(length),chord_error_mm=error,start_mm=start.tolist(),end_mm=end.tolist())
        row['stage']='native';count=0
        for group,tg in targets.items():
            ctx.targets=tg
            for angle in (yaws if group=='body' else pitches if group=='pitch' else [0]):
                mat=np.asarray(rigidtr(angle,0)) if group=='body' else np.linalg.inv(np.asarray(rigidtr(0,angle))) if group=='pitch' else np.eye(4)
                hit=ctx.clear(p@mat[:3,:3].T+mat[:3,3],radius=.3302,chord_error=max(error,.0003));count+=1
                if hit:row['hits'].append(dict(group=group,angle=angle,**hit));break
            if row['hits']:break
        row['counts']['native']=count
        if not row['hits']:
            assert count==24;row['stage']='other_neck';count=0
            for y,s in itertools.product(yaws,range(11)):
                if s==slot:continue
                rr=pair_threshold(item,neck[s,y]);count+=1
                if rr['status']!='PASS':row['hits'].append(dict(slot=s,yaw=y,**rr));break
            row['counts']['other_neck']=count
        if not row['hits']:
            assert count==130;row['stage']='other_upper';count=0
            for y,pitch,other in itertools.product(yaws,pitches,mapping):
                if other==pin:continue
                rr=pair_threshold(item,upper[other,y,pitch]);count+=1
                if rr['status']!='PASS':row['hits'].append(dict(other_pin=other,yaw=y,pitch=pitch,**rr));break
            row['counts']['other_upper']=count
        if not row['hits']:
            assert count==390;row.update(status='PASS',stage='pool')
            key=f'pin{pin}_lead{lead:g}';row['key']=key;pools[pin].append(row);fan_points[key]=p;fan_items[key]=item
        attempts.append(row);print('SIDE_FAN',pin,lead,row['status'],row['stage'],row['hits'][:1],flush=True)
ctx.targets=native
pair_cache={};combos=[];selected=None;joined={};self_rows=[];pairs=[];join_errors=[];length_rows=[]
for combo in itertools.product(*(pools[p] for p in mapping)):
    keys=[r['key'] for r in combo];bad=[]
    for a,b in itertools.combinations(keys,2):
        key=(a,b)
        if key not in pair_cache:pair_cache[key]=pair(fan_items[a],fan_items[b])
        if pair_cache[key]['status']!='PASS':bad.append(dict(a=a,b=b,**pair_cache[key]))
    combos.append(dict(keys=keys,status='BLOCKED' if bad else 'PASS',conflicts=bad))
    if not bad:selected=combo;break
if selected:
    pack={}
    for spec in selected:
        pin=spec['pin'];slot=mapping[pin];fan=fan_points[spec['key']]
        for yaw,pitch in itertools.product(yaws,pitches):
            neckp=neck_local[slot,yaw];up=uc[f'pin{pin}_y{yaw}_p{pitch}']
            errors=[float(np.linalg.norm(neckp[-1]-fan[0])),float(np.linalg.norm(fan[-1]-up[0]))]
            assert max(errors)<1e-5,errors
            joinedp=np.vstack([neckp,fan[1:],up[1:]])
            join_errors.append(dict(pin=pin,yaw=yaw,pitch=pitch,errors_mm=errors))
            length_rows.append(dict(pin=pin,yaw=yaw,pitch=pitch,polygon_length_mm=float(np.linalg.norm(np.diff(joinedp,axis=0),axis=1).sum())))
            item=prepared(refined(joinedp,.01),.3302,.0003)
            srw=dict(pin=pin,yaw=yaw,pitch=pitch,**self_clear(item));self_rows.append(srw);pack[pin,yaw,pitch]=item
            joined[f'pin{pin}_y{yaw}_p{pitch}']=joinedp
        print('SIDE_FAN_JOIN_SELF',pin,sum(r['status']!='PASS' for r in self_rows),flush=True)
    for yaw,pitch in itertools.product(yaws,pitches):
        for a,b in itertools.combinations(mapping,2):pairs.append(dict(a=a,b=b,yaw=yaw,pitch=pitch,**pair_threshold(pack[a,yaw,pitch],pack[b,yaw,pitch])))
    assert len(self_rows)==520 and len(pairs)==780
lengths=[]
for pin in mapping:
    ls=[r['polygon_length_mm'] for r in length_rows if r['pin']==pin]
    if ls:lengths.append(dict(pin=pin,min_mm=min(ls),max_mm=max(ls),range_mm=max(ls)-min(ls)))
ok=selected is not None and all(r['status']=='PASS' for r in pairs+self_rows) and all(r['range_mm']<.01 for r in lengths)
ctx.assert_unchanged()
np.savez_compressed(OUT/'fan_candidates.npz',**fan_points)
if selected:np.savez_compressed(OUT/'joined_curves.npz',**joined)
inputs=[N/'join_screen.json',N/'neck_curves.npz',S/'loop_screen.json',S/'curves.npz',HERE/'upper_curve_geometry.py',HERE/'curve_clearance.py',HERE/'curve_self_partition.py',HERE/'upper_pack_geometry.py',HERE/'bounded_curve_checks.py',HERE/'remaining_routes/self_partition_verification.json']
r=dict(status='PASS' if ok else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},attempts=attempts,pool_counts={p:len(v) for p,v in pools.items()},
    combinations=combos,selected=selected,fan_pairs=[dict(a=a,b=b,**r) for (a,b),r in pair_cache.items()],self_checks=self_rows,joined_pairs=pairs,join_errors=join_errors,lengths=lengths,
    fan_curve_sha256=sha(OUT/'fan_candidates.npz'),joined_curve_sha256=sha(OUT/'joined_curves.npz') if selected else None,mapping=mapping,
    main_changed=False,C6_main_applied=False,full_harness='BLOCKED',supplier_drawing_release=False,
    scope='Four fixed-yaw fan connections; joined neck-to-CAM paths, all 130 motion samples. Body prefixes, other upper endpoints, strain relief, FPC/FFC and wired assembly remain absent.',
    inherited_checks=['Unchanged neck native and mutual checks from neck_side_tail_gentle.', 'Unchanged upper native, self, mutual and all neck/upper cross pairs from cam_side_following.'],
    limits=['7mm circular fan radii and +Z terminal tangents; adjacent self spans excluded below5mm under the separate bend checks.', 'Joined lengths are nominal sampled paths, not manufactured wire cut lengths.', 'Current connector and material allocations retain source limitations.'],
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'fan_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('CAM_SIDE_FANS_DONE',r['status'],r['pool_counts'],r['lengths'],r['elapsed_s'],flush=True)
