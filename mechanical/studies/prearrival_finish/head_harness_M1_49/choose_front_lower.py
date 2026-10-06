"""Verify the complete revised lower 11-wire arrangement on current solids."""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from curve_clearance import prepared,pair,self_clear
from common import P
from validate import rigidtr
ctx=Context();started=time.time();read=lambda n:json.loads((HERE/n).read_text())
base=read('current_source_verification.json');front=read('front_route_screen.json');pool=read('front_body_pin1_screen.json')
assert base['status']==pool['status']=='PASS'
assert not front['neck_hits'] and len(front['neck_pair_checks'])==715 and all(r['status']=='PASS' for r in front['neck_pair_checks'])
for report in [base,front,pool]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in base['inputs'].items():assert sha(HERE/p)==h,p
for p,h in pool['additional_inputs'].items():assert sha(PROJECT/p)==h,p
neck=np.load(HERE/'front_neck_candidates.npz');prefixes=np.load(HERE/'front_body_pin1_candidates.npz')
old=np.load(HERE/'body_layered_four_candidates.npz');old_rows=read('body_layered_four_screen.json')['selected']
assert sha(HERE/'front_body_pin1_candidates.npz')==pool['curve_sha256']
assert sha(HERE/'front_neck_candidates.npz')==front['curve_files']['front_neck_candidates.npz']
err=front['local_chord_error_mm'];original=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
other={};other_rows={r['slot']:r for r in old_rows if r['pin']!=1}
for yaw in range(-60,61,10):
    for i,allocation in enumerate(P['neck_harness_capacity']['wire_allocations']):
        if i==10:continue
        row=other_rows.get(i);p=old[f'pin{row["pin"]}_y{yaw}'] if row else neck[f'wire{i}_y{yaw}']
        other[i,yaw]=prepared(p,allocation['OD_mm']/2,max(err,row['chord_error_mm']) if row else err)
unchanged=[]
for yaw in range(-60,61,10):
    for i,j in itertools.combinations(range(10),2):
        unchanged.append(dict(yaw=yaw,a=i,b=j,**pair(other[i,yaw],other[j,yaw])))
assert len(unchanged)==585
print('OTHER_REVISED_LOWER',sum(r['status']!='PASS' for r in unchanged),flush=True)
trials=[];selected=None;selected_pairs=[];selected_self=[];selected_curves={};checks=0
if all(r['status']=='PASS' for r in unchanged):
    candidates=sorted([row for rows in pool['pools'].values() for row in rows],key=lambda r:r['length_mm'])
    for row in candidates:
        p=prefixes[row['id']];error=row['chord_error_mm'];lead_points=int(np.ceil(row['lead_mm']/.06))+1
        issue=None
        for group,t in targets.items():
            ctx.targets=t
            for yaw in ([0] if group=='body' else range(-60,61,10)):
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    for section,pts in [('stem',p[:lead_points]),('tail',p[lead_points-1:])]:
                        issue=ctx.clear(pts@tr[:3,:3].T+tr[:3,3],chord_error=error,ignore=['Plug_motion_J5'] if section=='stem' else [])
                        checks+=1
                        if issue:issue=dict(group=group,yaw=yaw,pitch=pitch,section=section,**issue);break
                    if issue:break
                if issue:break
            if issue:break
        ctx.targets=original
        result=dict(id=row['id'],status='BLOCKED',solid_hit=issue)
        if issue:trials.append(result);continue
        comparisons=[];selfrows=[];curves={}
        for yaw in range(-60,61,10):
            curve=np.vstack([p,neck[f'wire10_y{yaw}'][1:]])
            item=prepared(curve,.3302,max(err,error));curves[f'pin1_y{yaw}']=curve
            for i in range(10):comparisons.append(dict(yaw=yaw,a=10,b=i,**pair(item,other[i,yaw])))
            if any(r['status']!='PASS' for r in comparisons):break
            selfrows.append(dict(yaw=yaw,**self_clear(item)))
            if selfrows[-1]['status']!='PASS':break
        result['wire_hits']=[r for r in comparisons if r['status']!='PASS'];result['self_hits']=[r for r in selfrows if r['status']!='PASS']
        if result['wire_hits'] or result['self_hits']:trials.append(result);continue
        result['status']='PASS';trials.append(result);selected=dict(row,body_entry_angle_deg=42)
        selected_pairs=comparisons;selected_self=selfrows;selected_curves=curves;break
ctx.targets=original;ctx.assert_unchanged()
if selected:
    selected_curves.update({k:old[k] for k in old.files if not k.startswith('pin1_')})
    np.savez_compressed(HERE/'front_lower_curves.npz',**selected_curves)
report=dict(status='PASS' if selected else 'BLOCKED',source_blend_sha256=ctx.source_hash,sources=ctx.sources,
    selected=selected,other_selected=[r for r in old_rows if r['pin']!=1],trials=trials,
    pair_checks=unchanged+selected_pairs,self_checks=selected_self,solid_checks=checks,
    inputs={name:sha(HERE/name) for name in ['current_source_verification.json','front_route_screen.json','front_neck_candidates.npz','front_body_pin1_screen.json','front_body_pin1_candidates.npz','body_layered_four_candidates.npz','body_layered_four_screen.json','curve_clearance.py']},
    curve_sha256=sha(HERE/'front_lower_curves.npz') if selected else None,
    scope='Revised 11-wire lower arrangement, current solids and finite-pose all-pair distances; full head endings still incomplete',
    main_changed=False,full_harness='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(HERE/'front_lower_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FRONT_LOWER_DONE',report['status'],len(trials),len(report['pair_checks']),flush=True)
