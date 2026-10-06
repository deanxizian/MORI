"""Select a whole five-wire lower arrangement, then verify every chosen member.

Only independent unselected-wire candidates are written. Native solids,
electrical pin assignments and main model are unchanged.
"""
from pathlib import Path
import json,sys,time,itertools,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/five_before_cam_reroute';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
from validate import rigidtr
ctx=Context();start=time.time();OD=1.1684;inputs={};rows=[];prefix={}
def receive(path):
    inputs[str(path.relative_to(PROJECT))]=sha(path)
    return json.loads(path.read_text())
for folder in ['servo_parallel','power_parallel','rearward_power_all','thermothin2622_r65','thermothin2622_peer','thermothin2622']:
    base=HERE/'remaining_routes'/folder;report=receive(base/'body_prefix_screen.json')
    assert report['status']=='PASS'
    for f,h in {**report['sources'],**report['inputs']}.items():assert sha(PROJECT/f)==h,f
    data=np.load(base/'body_prefix_candidates.npz');assert sha(base/'body_prefix_candidates.npz')==report['curve_sha256']
    inputs[str((base/'body_prefix_candidates.npz').relative_to(PROJECT))]=sha(base/'body_prefix_candidates.npz')
    for rr in report['pools'].values():
        for r in rr:
            # Old slot1 means phase22, while the new slot1 is phase-10.75.
            if folder.startswith('thermothin') and r['slot']==1:continue
            row=dict(r,id=folder+':'+r['id'],source_row_id=r['id'],pool=folder)
            rows.append(row);prefix[row['id']]=data[r['id']]
lower=receive(HERE/'front_lower_verification.json');assert lower['status']=='PASS'
for f,h in lower['sources'].items():assert sha(PROJECT/f)==h,f
cam=np.load(HERE/'front_lower_curves.npz');assert sha(HERE/'front_lower_curves.npz')==lower['curve_sha256']
base=np.load(HERE/'front_neck_candidates.npz');neck={k:base[k] for k in base.files}
lane_report=receive(HERE/'remaining_routes/servo_lane/neck_screen.json')
for f,h in {**lane_report['sources'],**lane_report['inputs']}.items():assert sha(PROJECT/f)==h,f
lane_row=next(r for r in lane_report['results'] if r['dip_mm']==1.2);assert lane_row['status']=='PASS'
lane=np.load(HERE/'remaining_routes/servo_lane/neck_candidates.npz')
assert sha(HERE/'remaining_routes/servo_lane/neck_candidates.npz')==lane_report['curve_sha256']
neck_error=max(.00001,lane_row['chord_error_mm'])
for yaw in range(-60,61,10):neck[f'wire1_y{yaw}']=lane[f'dip1.2_wire1_y{yaw}']
for f in [HERE/'front_lower_curves.npz',HERE/'front_neck_candidates.npz',HERE/'remaining_routes/servo_lane/neck_candidates.npz',HERE/'bounded_curve_checks.py',HERE/'curve_clearance.py']:
    inputs[str(f.relative_to(PROJECT))]=sha(f)
cam_error=max([lower['selected']['chord_error_mm']]+[r['chord_error_mm'] for r in lower['other_selected']])
reserve={(s,y):prepared(neck[f'wire{s}_y{y}'],(OD/2 if s==1 else .7112) if s<7 else .3302,neck_error) for s in range(11) for y in range(-60,61,10)}
cam_items={(pin,y):prepared(cam[f'pin{pin}_y{y}'],.3302,cam_error) for pin in range(1,5) for y in range(-60,61,10)}
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
identities=['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2']
pool={k:sorted([r for r in rows if r['endpoint']==k],key=lambda r:r['analytic_length_mm']) for k in identities}
items={r['id']:prepared(prefix[r['id']],OD/2,r['chord_error_mm']) for r in rows}
order=sorted(identities,key=lambda k:len(pool[k]));comparisons={};nodes=0;rejected=set();verified=set();trials=[];attempts=[]
solid_checks=0;wire_checks=0
failure_states=set()
priority={key:i for i,key in enumerate(['P_J9_3','P_J9_1','P_J9_2','P_J18_1','P_J18_2'])}
def compatible(a,b):
    if a['slot']==b['slot']:return False
    key=tuple(sorted([a['id'],b['id']]))
    if key not in comparisons:comparisons[key]=pair_threshold(items[key[0]],items[key[1]])
    return comparisons[key]['status']=='PASS'
def search(chosen,remaining=None):
    global nodes
    if remaining is None:
        remaining={k:[r for r in pool[k] if r['id'] not in rejected] for k in identities}
    nodes+=1
    if nodes%1000==0:print('PARALLEL_SEARCH',nodes,'pair_cache',len(comparisons),'failed_states',len(failure_states),flush=True)
    if not remaining:return chosen if any(r['slot']==1 for r in chosen) else None
    used1=any(r['slot']==1 for r in chosen)
    state=(used1,tuple((k,tuple(r['id'] for r in remaining[k])) for k in sorted(remaining)))
    if state in failure_states:return None
    ident=min(remaining,key=lambda k:priority[k])
    others=sorted((k for k in remaining if k!=ident),key=lambda k:priority[k])
    for row in remaining[ident]:
        next_remaining={};good=True
        for k in others:
            options=[r for r in remaining[k] if compatible(row,r)]
            if not options:good=False;break
            next_remaining[k]=options
        if good:
            result=search(chosen+[row],next_remaining)
            if result:return result
    failure_states.add(state)
    return None

def check(row):
    global solid_checks,wire_checks
    p=prefix[row['id']];a=items[row['id']]
    for yaw in [0]+[v for v in range(-60,61,10) if v]:
        # Old CAM body prefixes are explicitly deferred for rerouting.
        for slot in range(11):
            if slot==row['slot']:continue
            result=pair_threshold(a,reserve[slot,yaw]);wire_checks+=1
            if result['status']!='PASS':return dict(kind='neck',yaw=yaw,slot=slot,**result)
    n=int(np.ceil(row['lead_mm']/.06))+1
    for group,t in targets.items():
        ctx.targets=t
        for yaw in ([0] if group=='body' else range(-60,61,10)):
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                for label,q in [('stem',p[:n]),('tail',p[n-1:])]:
                    hit=ctx.clear(q@tr[:3,:3].T+tr[:3,3],chord_error=row['chord_error_mm'],radius=OD/2,
                        ignore=['Plug_'+row['port']] if label=='stem' else [])
                    solid_checks+=1
                    if hit:
                        ctx.targets=native
                        return dict(kind='solid',group=group,yaw=yaw,pitch=pitch,section=label,**hit)
    ctx.targets=native
    for yaw in range(-60,61,10):
        joined=np.vstack([p,neck[f'wire{row["slot"]}_y{yaw}'][1:]])
        result=self_clear(prepared(joined,OD/2,max(row['chord_error_mm'],neck_error)))
        if result['status']!='PASS':return dict(kind='self',yaw=yaw,**result)
    return None
selected=None
while True:
    failure_states.clear()
    proposed=search([])
    if proposed is None:break
    attempts.append([r['id'] for r in proposed]);valid=True
    print('PARALLEL_PROPOSAL',len(attempts),attempts[-1],flush=True)
    for row in proposed:
        if row['id'] in verified:continue
        failure=check(row)
        trials.append(dict(id=row['id'],status='BLOCKED' if failure else 'PASS',failure=failure))
        print('PARALLEL_VERIFY',row['id'],trials[-1]['status'],flush=True)
        if failure:rejected.add(row['id']);valid=False;break
        verified.add(row['id'])
    if valid:selected=proposed;break
arrays={};whole=[];joins=[]
if selected:
    lookup={r['slot']:r for r in selected}
    assert 1 in lookup,'The smaller-OD revised lane must be an assigned reference wire.'
    for yaw in range(-60,61,10):
        pieces={}
        for slot in range(7):
            row=lookup.get(slot);end=neck[f'wire{slot}_y{yaw}']
            if row:
                beg=prefix[row['id']];join=float(np.linalg.norm(beg[-1]-end[0]));assert join<1e-8
                points=np.vstack([beg,end[1:]]);key=row['endpoint'];arrays[key+f'_y{yaw}']=points
                joins.append(dict(endpoint=key,yaw=yaw,error_mm=join))
                pieces[key]=prepared(points,OD/2,max(row['chord_error_mm'],neck_error))
            else:pieces['unassigned_'+str(slot)]=reserve[slot,yaw]
        pieces.update({'CAM_neck_'+str(slot):reserve[slot,yaw] for slot in range(7,11)})
        for a,b in itertools.combinations(pieces,2):whole.append(dict(yaw=yaw,a=a,b=b,**pair(pieces[a],pieces[b])))
        print('PARALLEL_FINAL',yaw,sum(r['status']!='PASS' for r in whole),flush=True)
ctx.targets=native;ctx.assert_unchanged()
for f,h in inputs.items():assert sha(PROJECT/f)==h,f
success=selected is not None and len(whole)==715 and all(r['status']=='PASS' for r in whole)
if success:np.savez_compressed(OUT/'lower_five_candidates.npz',**arrays)
report=dict(status='PASS' if success else 'BLOCKED',scope='Five proposed body-to-Z200 routes plus six local neck strands only; previous four CAM body prefixes explicitly excluded for redesign',
    sources=ctx.sources,inputs=inputs,selected=selected,candidate_counts={k:len(v) for k,v in pool.items()},
    trials=trials,attempts=attempts,backtrack_nodes=nodes,solid_checks=solid_checks,individual_wire_checks=wire_checks,
    prefix_pair_checks=[dict(a=k[0],b=k[1],**v) for k,v in comparisons.items()],whole_pairs=whole,joins=joins,
    curve_sha256=sha(OUT/'lower_five_candidates.npz') if success else None,changed_neck_lane=lane_row,
    OD_mm=OD,wire_reference='Unselected Alpha2622 maximum-OD reference, no electrical approval or crimp qualification',
    full_harness='BLOCKED',deferred_CAM_body_prefixes=True,current_CAM_body_coexistence='BLOCKED',remote_endpoints='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    main_changed=False,supplier_cut_lengths_released=False,physical_qualification='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'lower_five_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('PARALLEL_DONE',report['status'],'seconds',report['elapsed_s'],flush=True)
