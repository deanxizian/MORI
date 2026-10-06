"""Verify nine-conductor lower options allowing a CAM1/2 mechanical lane swap while keeping logical pins.

The two speaker slots remain local references. Upper servo/USB terminals,
anchors and installation remain outside this finite lower-geometry check.
"""
from pathlib import Path
import json,sys,time,itertools,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
BASE=HERE/'remaining_routes/nine_higher';EXTRA=HERE/'remaining_routes/higher_cam_directed';STAGGER=HERE/'remaining_routes/higher_cam_stagger';LIFT=HERE/'remaining_routes/cam_root_lift';SWAP=HERE/'remaining_routes/cam_lane_swap';OUT=HERE/'remaining_routes/nine_lane_swap/combined';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
from validate import rigidtr
ctx=Context();start=time.time();source=json.loads((BASE/'body_prefix_screen.json').read_text())
assert source['status']=='PASS'
for f,h in {**source['sources'],**source['inputs']}.items():assert sha(PROJECT/f)==h,f
prefix=dict(np.load(BASE/'body_prefix_candidates.npz'));assert sha(BASE/'body_prefix_candidates.npz')==source['curve_sha256']
extra=json.loads((EXTRA/'body_prefix_screen.json').read_text());assert extra['status']=='PASS'
for f,h in {**extra['sources'],**extra['inputs']}.items():assert sha(PROJECT/f)==h,f
more=dict(np.load(EXTRA/'body_prefix_candidates.npz'));assert sha(EXTRA/'body_prefix_candidates.npz')==extra['curve_sha256']
assert not set(prefix).intersection(more);prefix.update(more)
stagger=json.loads((STAGGER/'body_prefix_screen.json').read_text());assert stagger['status']=='PASS'
for f,h in {**stagger['sources'],**stagger['inputs']}.items():assert sha(PROJECT/f)==h,f
more=dict(np.load(STAGGER/'body_prefix_candidates.npz'));assert sha(STAGGER/'body_prefix_candidates.npz')==stagger['curve_sha256']
assert not set(prefix).intersection(more);prefix.update(more)
lift=json.loads((LIFT/'body_prefix_screen.json').read_text());assert lift['status']=='PASS'
for f,h in {**lift['sources'],**lift['inputs']}.items():assert sha(PROJECT/f)==h,f
more=dict(np.load(LIFT/'body_prefix_candidates.npz'));assert sha(LIFT/'body_prefix_candidates.npz')==lift['curve_sha256']
assert not set(prefix).intersection(more);prefix.update(more)
swap=json.loads((SWAP/'body_prefix_screen.json').read_text());assert swap['status']=='PASS'
for f,h in {**swap['sources'],**swap['inputs']}.items():assert sha(PROJECT/f)==h,f
more=dict(np.load(SWAP/'body_prefix_candidates.npz'));assert sha(SWAP/'body_prefix_candidates.npz')==swap['curve_sha256']
assert not set(prefix).intersection(more);prefix.update(more)
lane_base=HERE/'remaining_routes/higher_entry';lane_report=json.loads((lane_base/'neck_screen.json').read_text())
lane=next(r for r in lane_report['results'] if r['z0_mm']==source['z0_mm']);assert lane['status']=='PASS'
neck_data=np.load(lane_base/'neck_candidates.npz');assert sha(lane_base/'neck_candidates.npz')==lane_report['curve_sha256']
neck={f'wire{i}_y{y}':neck_data[f'z{source["z0_mm"]}_wire{i}_y{y}'] for i in range(11) for y in range(-60,61,10)}
identities=[r['endpoint'] for r in source['functions']];rows=[r for report in [source,extra,stagger,lift,swap] for rr in report['pools'].values() for r in rr]
pool={key:sorted([r for r in rows if r['endpoint']==key],key=lambda r:r.get('length_sort_mm',r.get('analytic_length_mm'))) for key in identities}
items={r['id']:prepared(prefix[r['id']],r['OD_mm']/2,r['chord_error_mm']) for r in rows}
reserve={(s,y):prepared(neck[f'wire{s}_y{y}'],.5842 if s<7 else .3302,lane['chord_error_mm']) for s in range(11) for y in range(-60,61,10)}
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
previous=json.loads((HERE/'remaining_routes/nine_higher_lift/combined/lower_nine_screen.json').read_text())
for f,h in {**previous['sources'],**previous['inputs']}.items():assert sha(PROJECT/f)==h,f
comparisons={(r['a'],r['b']):{k:v for k,v in r.items() if k not in ['a','b']} for r in previous['prefix_pair_checks']};nodes=0;failure_states=set();rejected=set();verified=set();trials=[];attempts=[];solid_checks=0;wire_checks=0
# Complete the tightly coupled servo group first; forward propagation still
# tests all remaining groups, and memoization avoids repeating independent work.
priority={k:i for i,k in enumerate(['P_J9_3','P_J9_1','P_J9_2','CAM_1','CAM_2','CAM_3','CAM_4','P_J18_1','P_J18_2'])}
def compatible(a,b):
    if a['slot']==b['slot']:return False
    key=tuple(sorted([a['id'],b['id']]))
    if key not in comparisons:comparisons[key]=pair_threshold(items[key[0]],items[key[1]])
    return comparisons[key]['status']=='PASS'
def search(chosen,remaining=None):
    global nodes
    if remaining is None:remaining={k:[r for r in pool[k] if r['id'] not in rejected] for k in identities}
    nodes+=1
    if nodes%1000==0:print('NINE_SEARCH',nodes,len(comparisons),len(failure_states),flush=True)
    if not remaining:return chosen
    state=tuple((k,tuple(r['id'] for r in remaining[k])) for k in sorted(remaining))
    if state in failure_states:return None
    ident=min(remaining,key=lambda k:priority[k]);others=sorted((k for k in remaining if k!=ident),key=lambda k:priority[k])
    for row in remaining[ident]:
        next_remaining={};good=True
        for key in others:
            options=[r for r in remaining[key] if compatible(row,r)]
            if not options:good=False;break
            next_remaining[key]=options
        if good:
            result=search(chosen+[row],next_remaining)
            if result:return result
    failure_states.add(state);return None
def check(row):
    global solid_checks,wire_checks
    p=prefix[row['id']];a=items[row['id']]
    for yaw in [0]+[y for y in range(-60,61,10) if y]:
        for slot in range(11):
            if slot==row['slot']:continue
            result=pair_threshold(a,reserve[slot,yaw]);wire_checks+=1
            if result['status']!='PASS':return dict(kind='neck',yaw=yaw,slot=slot,**result)
    # Sources use different sampling steps. Find the actual straight-stem end
    # instead of applying the original .06 mm sample count to lifted curves.
    n=int(np.flatnonzero(np.linalg.norm(p[:,:2]-p[0,:2],axis=1)>1e-8)[0])
    assert abs(np.linalg.norm(p[n-1]-p[0])-row['lead_mm'])<1e-7
    for group,t in targets.items():
        ctx.targets=t
        for yaw in ([0] if group=='body' else range(-60,61,10)):
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                for label,q in [('stem',p[:n]),('tail',p[n-1:])]:
                    hit=ctx.clear(q@tr[:3,:3].T+tr[:3,3],chord_error=row['chord_error_mm'],radius=row['OD_mm']/2,
                        ignore=['Plug_'+row['port']] if label=='stem' else [])
                    solid_checks+=1
                    if hit:ctx.targets=native;return dict(kind='solid',group=group,yaw=yaw,pitch=pitch,section=label,**hit)
    ctx.targets=native
    for yaw in range(-60,61,10):
        p_full=np.vstack([p,neck[f'wire{row["slot"]}_y{yaw}'][1:]])
        result=self_clear(prepared(p_full,row['OD_mm']/2,max(row['chord_error_mm'],lane['chord_error_mm'])))
        if result['status']!='PASS':return dict(kind='self',yaw=yaw,**result)
    return None
selected=None
while True:
    failure_states.clear();proposal=search([])
    if proposal is None:break
    attempts.append([r['id'] for r in proposal]);valid=True
    print('NINE_PROPOSAL',len(attempts),attempts[-1],flush=True)
    for row in proposal:
        if row['id'] in verified:continue
        failure=check(row);trials.append(dict(id=row['id'],status='BLOCKED' if failure else 'PASS',failure=failure))
        print('NINE_VERIFY',row['id'],trials[-1],flush=True)
        if failure:rejected.add(row['id']);valid=False;break
        verified.add(row['id'])
    if valid:selected=proposal;break
curves={};pairs=[];joins=[]
if selected:
    lookup={r['slot']:r for r in selected}
    for yaw in range(-60,61,10):
        pieces={}
        for slot in range(11):
            row=lookup.get(slot)
            if row:
                a=prefix[row['id']];b=neck[f'wire{slot}_y{yaw}'];error=float(np.linalg.norm(a[-1]-b[0]));assert error<1e-8
                p=np.vstack([a,b[1:]]);curves[row['endpoint']+f'_y{yaw}']=p;joins.append(dict(endpoint=row['endpoint'],yaw=yaw,error_mm=error))
                pieces[row['endpoint']]=prepared(p,row['OD_mm']/2,max(row['chord_error_mm'],lane['chord_error_mm']))
            else:pieces['SPK_reservation_'+str(slot)]=reserve[slot,yaw]
        for a,b in itertools.combinations(pieces,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(pieces[a],pieces[b])))
        print('NINE_FINAL',yaw,sum(r['status']!='PASS' for r in pairs),flush=True)
ctx.targets=native;ctx.assert_unchanged()
success=selected is not None and len(pairs)==715 and all(r['status']=='PASS' for r in pairs)
if success:np.savez_compressed(OUT/'lower_nine_candidates.npz',**curves)
report=dict(status='PASS' if success else 'BLOCKED',sources=ctx.sources,selected=selected,scope='Nine continuous lower routes and two local speaker reservations; finite native checks only',
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [BASE/'body_prefix_screen.json',BASE/'body_prefix_candidates.npz',EXTRA/'body_prefix_screen.json',EXTRA/'body_prefix_candidates.npz',STAGGER/'body_prefix_screen.json',STAGGER/'body_prefix_candidates.npz',LIFT/'body_prefix_screen.json',LIFT/'body_prefix_candidates.npz',SWAP/'body_prefix_screen.json',SWAP/'body_prefix_candidates.npz',HERE/'remaining_routes/nine_higher_lift/combined/lower_nine_screen.json',lane_base/'neck_screen.json',lane_base/'neck_candidates.npz',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']},
    candidate_counts={k:len(v) for k,v in pool.items()},trials=trials,attempts=attempts,backtrack_nodes=nodes,
    prefix_pair_checks=[dict(a=k[0],b=k[1],**v) for k,v in comparisons.items()],whole_pairs=pairs,joins=joins,
    solid_checks=solid_checks,individual_wire_checks=wire_checks,curve_sha256=sha(OUT/'lower_nine_candidates.npz') if success else None,
    z0_mm=source['z0_mm'],upper_CAM_loops='NOT_TESTED',full_harness='BLOCKED',remote_endpoints='BLOCKED',
    anchors='NOT_TESTED',wired_assembly='NOT_TESTED',physical_qualification='NOT_TESTED',main_changed=False,
    supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'lower_nine_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('NINE_COMBINED_DONE',report['status'],report['elapsed_s'],flush=True)
