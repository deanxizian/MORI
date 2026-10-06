"""Five current-body routes plus retained four CAM routes and local reservations.

Only an unselected wire-reference geometry study. No printed or electrical
source is edited. Accepted lower paths still do not reach USB/servo/speaker.
"""
from pathlib import Path
import json,sys,time,itertools,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/rearward_power_r65'
PEER=HERE/'remaining_routes/thermothin2622_peer'
LANE=HERE/'remaining_routes/servo_lane'
OLD=HERE/'remaining_routes/thermothin2622'
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from curve_clearance import prepared,pair,self_clear
from validate import rigidtr
ctx=Context();started=time.time();OD=1.1684;neck_error=.00001
pool=json.loads((OUT/'body_prefix_screen.json').read_text())
lower=json.loads((HERE/'front_lower_verification.json').read_text())
assert pool['status']==lower['status']=='PASS'
for report in [pool,lower]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in pool['inputs'].items():assert sha(PROJECT/p)==h,p
assert sha(OUT/'body_prefix_candidates.npz')==pool['curve_sha256']
assert sha(HERE/'front_lower_curves.npz')==lower['curve_sha256']
peer=np.load(OUT/'body_prefix_candidates.npz');original_prefix=np.load(OLD/'body_prefix_candidates.npz')
prior=json.loads((OLD/'lower_five_screen.json').read_text())
prior_pool=json.loads((OLD/'body_prefix_screen.json').read_text())
for f,h in prior['sources'].items():assert sha(PROJECT/f)==h,f
for f,h in prior['inputs'].items():assert sha(PROJECT/f)==h,f
previous_good={r['id'] for r in prior['trials'] if r['status']=='PASS'}
reused=[r for rr in prior_pool['pools'].values() for r in rr if r['id'] in previous_good]
assert len(reused)==41 and all(r['endpoint'].startswith('P_J18') for r in reused)
reuse_peer=json.loads((PEER/'lower_five_screen.json').read_text())
peer_pool=json.loads((PEER/'body_prefix_screen.json').read_text())
for report in [reuse_peer,peer_pool]:
    for f,h in {**report['sources'],**report['inputs']}.items():assert sha(PROJECT/f)==h,f
peer_good={r['id'] for r in reuse_peer['trials'] if r['status']=='PASS'}
peer_rows=[r for rr in peer_pool['pools'].values() for r in rr if r['id'] in peer_good]
assert len(peer_rows)==11
old_peer=np.load(PEER/'body_prefix_candidates.npz')
prefix={**{r['id']:original_prefix[r['id']] for r in reused},**{r['id']:old_peer[r['id']] for r in peer_rows},**{k:peer[k] for k in peer.files}}
reused+=peer_rows
reused_ids={r['id'] for r in reused}
base_neck=np.load(HERE/'front_neck_candidates.npz');neck={k:base_neck[k] for k in base_neck.files}
lane_report=json.loads((LANE/'neck_screen.json').read_text())
lane_row=next(r for r in lane_report['results'] if r['dip_mm']==1.2)
assert lane_row['status']=='PASS'
for f,h in {**lane_report['sources'],**lane_report['inputs']}.items():assert sha(PROJECT/f)==h,f
assert sha(LANE/'neck_candidates.npz')==lane_report['curve_sha256']
lane=np.load(LANE/'neck_candidates.npz');neck_error=max(neck_error,lane_row['chord_error_mm'])
for yaw in range(-60,61,10):neck[f'wire1_y{yaw}']=lane[f'dip1.2_wire1_y{yaw}']
cam=np.load(HERE/'front_lower_curves.npz')
rows=sorted(reused+[r for rr in pool['pools'].values() for r in rr],key=lambda r:r['analytic_length_mm'])
cam_error=max([lower['selected']['chord_error_mm']]+[r['chord_error_mm'] for r in lower['other_selected']])
reserve={(slot,y):prepared(neck[f'wire{slot}_y{y}'],OD/2 if slot==1 else .7112,neck_error) for slot in range(7) for y in range(-60,61,10)}
cam_items={(pin,y):prepared(cam[f'pin{pin}_y{y}'],.3302,cam_error) for pin in range(1,5) for y in range(-60,61,10)}
original=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
accepted=collections.defaultdict(list);trials=[];items={};pair_count=0;solid_count=0

# Previous solid checks can be reused, but every changed-lane relationship is rechecked.

def wire_check(row,points):
    global pair_count
    a=prepared(points,OD/2,row['chord_error_mm'])
    # Reject inexpensive zero-pose conflicts first, then all remaining yaws.
    for yaw in [0]+[v for v in range(-60,61,10) if v]:
        for pin in range(1,5):
            result=pair(a,cam_items[pin,yaw]);pair_count+=1
            if result['status']!='PASS':return dict(kind='CAM',pin=pin,yaw=yaw,**result)
        for slot in range(7):
            if slot==row['slot']:continue
            result=pair(a,reserve[slot,yaw]);pair_count+=1
            if result['status']!='PASS':return dict(kind='neck_reservation',slot=slot,yaw=yaw,**result)
    return None

def solid_check(row,p):
    global solid_count
    n=int(np.ceil(row['lead_mm']/.06))+1
    for group,t in targets.items():
        ctx.targets=t
        for yaw in ([0] if group=='body' else range(-60,61,10)):
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                for section,q in [('stem',p[:n]),('tail',p[n-1:])]:
                    hit=ctx.clear(q@tr[:3,:3].T+tr[:3,3],chord_error=row['chord_error_mm'],
                        radius=OD/2,ignore=['Plug_'+row['port']] if section=='stem' else [])
                    solid_count+=1
                    if hit:
                        ctx.targets=original
                        return dict(yaw=yaw,pitch=pitch,group=group,section=section,**hit)
    ctx.targets=original
    return None

for row in rows:
    p=prefix[row['id']];trial=dict(id=row['id'],endpoint=row['endpoint'],status='BLOCKED')
    hit=wire_check(row,p)
    if hit:trial['wire_hit']=hit
    else:
        hit=None if row['id'] in reused_ids else solid_check(row,p)
        if hit:trial['solid_hit']=hit
        else:
            for yaw in range(-60,61,10):
                joined=np.vstack([p,neck[f'wire{row["slot"]}_y{yaw}'][1:]])
                result=self_clear(prepared(joined,OD/2,max(row['chord_error_mm'],neck_error)))
                if result['status']!='PASS':hit=dict(yaw=yaw,**result);break
            if hit:trial['self_hit']=hit
            else:
                trial['status']='PASS';accepted[row['endpoint']].append(row)
                items[row['id']]=prepared(p,OD/2,row['chord_error_mm'])
    trials.append(trial)
    print('POWER_FILTER',row['id'],trial['status'],flush=True)

identities=['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2']
order=sorted(identities,key=lambda k:len(accepted[k]));comparisons={};nodes=0
def search(chosen):
    global nodes
    nodes+=1
    if len(chosen)==5:return chosen
    for row in accepted[order[len(chosen)]]:
        if any(row['slot']==r['slot'] for r in chosen):continue
        good=True
        for prev in chosen:
            key=tuple(sorted([row['id'],prev['id']]))
            if key not in comparisons:comparisons[key]=pair(items[key[0]],items[key[1]])
            if comparisons[key]['status']!='PASS':good=False;break
        if good:
            result=search(chosen+[row])
            if result:return result
    return None
selected=search([]) if all(accepted[k] for k in identities) else None
arrays={};whole_pairs=[]
if selected:
    # Explicit complete lower all-pair recheck including unassigned large neck slots.
    lookup={r['slot']:r for r in selected}
    for yaw in range(-60,61,10):
        parts={}
        for slot in range(7):
            row=lookup.get(slot)
            points=np.vstack([prefix[row['id']],neck[f'wire{slot}_y{yaw}'][1:]]) if row else neck[f'wire{slot}_y{yaw}']
            key=row['endpoint'] if row else 'unassigned_'+str(slot)
            parts[key]=prepared(points,OD/2 if row else .7112,max(row['chord_error_mm'],neck_error) if row else neck_error)
            if row:arrays[key+f'_y{yaw}']=points
        parts.update({'CAM_'+str(pin):cam_items[pin,yaw] for pin in range(1,5)})
        for a,b in itertools.combinations(parts,2):whole_pairs.append(dict(yaw=yaw,a=a,b=b,**pair(parts[a],parts[b])))
    assert len(whole_pairs)==715
ctx.targets=original;ctx.assert_unchanged()
success=selected is not None and all(r['status']=='PASS' for r in whole_pairs)
if success:np.savez_compressed(OUT/'lower_five_candidates.npz',**arrays)
result=dict(status='PASS' if success else 'BLOCKED',scope='Five body-to-neck lower routes plus four CAM lower routes and two unassigned neck samples; revised slot1; finite13yaw/10pitch native checks',
    sources=ctx.sources,selected=selected,accepted_counts={k:len(accepted[k]) for k in identities},
    trials=trials,solid_checks=solid_count,individual_wire_checks=pair_count,backtrack_nodes=nodes,
    body_pair_checks=[dict(a=k[0],b=k[1],**v) for k,v in comparisons.items()],whole_pair_checks=whole_pairs,
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [OUT/'body_prefix_screen.json',OUT/'body_prefix_candidates.npz',
        OLD/'lower_five_screen.json',OLD/'body_prefix_candidates.npz',OLD/'body_prefix_screen.json',
        HERE/'front_lower_verification.json',HERE/'front_lower_curves.npz',HERE/'front_neck_candidates.npz',HERE/'curve_clearance.py',
        PEER/'lower_five_screen.json',PEER/'body_prefix_screen.json',PEER/'body_prefix_candidates.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz']},
    curve_sha256=sha(OUT/'lower_five_candidates.npz') if success else None,
    reused_finite_checks={'count':len(reused),'report_sha256':sha(OLD/'lower_five_screen.json'),'source_and_input_hashes_verified':True,'scope':'Native solid checks only; wire and self relationships rechecked','peer_report_sha256':sha(PEER/'lower_five_screen.json')},
    wire_reference='Unselected Alpha2622,22AWG catalogue reference; no BOM/contract change',
    OD_mm=OD,minimum_prefix_centerline_radius_mm=6.5,changed_neck_lane=lane_row,remote_endpoints='BLOCKED',
    anchors='NOT_TESTED',wired_assembly='NOT_TESTED',physical_qualification='NOT_TESTED',
    full_harness='BLOCKED',supplier_cut_lengths_released=False,main_changed=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'lower_five_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('POWER_PACK_DONE',result['status'],result['accepted_counts'],'nodes',nodes,'seconds',result['elapsed_s'],flush=True)
