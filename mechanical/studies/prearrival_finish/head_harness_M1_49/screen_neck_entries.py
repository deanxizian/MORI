"""Screen higher body-side wire entry datums in the approved, unchanged neck.

Original Z130 proves local capacity, but a complete body prefix must approach
with adequate bend room above real PCB components. These are route candidates
only. No printed part, endpoint pin or main file is changed.
"""
from pathlib import Path
import sys,json,time,copy
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import P
from neck_capacity import local_curves
from validate import rigidtr
ctx=Context();start=time.time();targets=ctx.targets
group={n:s.group for n,s in ctx.ss.items()}
bygroup={g:{n:s for n,s in targets.items() if group.get(n,'body')==g or (g=='body' and group.get(n,'body') not in ['yaw','pitch'])} for g in ['body','yaw','pitch']}
results=[];saved={}
for z,r0 in [(136.,10.6),(138.,10.6),(139.5,10.6),(136.,10.45),(138.,10.45),(139.5,10.45),(138.,10.3),(139.5,10.3)]:
 q=copy.deepcopy(P['neck_harness_capacity']);q['curve_family']['z0']=z;q['curve_family']['r0']=r0
 pack,data,rows=local_curves(q);chord=max(r['chord_error_mm'] for r in rows)
 failures=[];checks=0
 for i,slot in enumerate(pack['selected']):
  for yaw in range(-60,61,10):
   p=data[f'wire{i}_y{yaw}']
   for g,t in bygroup.items():
    ctx.targets=t
    for pitch in (range(-20,26,5) if g=='pitch' else [0]):
     tr=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if g=='pitch' else 0)))
     pts=p if g=='body' else p@tr[:3,:3].T+tr[:3,3]
     checks+=1;hit=ctx.clear(pts,chord_error=chord,radius=slot['OD_mm']/2)
     if hit:
      failures.append(dict(wire=i,yaw=yaw,pitch=pitch,group=g,**hit));break
    if failures:break
   if failures:break
  if failures:break
 bend=min(r['minimum_sampled_bend_mm'] for r in rows)
 results.append(dict(body_entry_z_mm=z,body_entry_r_mm=r0,status='PASS' if not failures and bend>=14.224 else 'BLOCKED',checks=checks,hits=failures,minimum_sampled_bend_mm=bend,length_mm=rows[0]['length_mm'],max_chord_error_mm=chord))
 if not failures:
  saved.update({f'z{z}_r{r0}_{k}':v for k,v in data.items()})
 print('NECK_ENTRY',z,results[-1],flush=True)
ctx.targets=targets;ctx.assert_unchanged()
np.savez_compressed(HERE/'neck_entry_candidates.npz',**saved)
r=dict(status='PASS' if any(x['status']=='PASS' for x in results) else 'BLOCKED',scope='Higher entry route families against unchanged main native solids, mate allocations and existing fixed-wire candidates; not complete routes or wired assembly',sources=ctx.sources,results=results,wire_wire_clearance='NOT_TESTED',planning_bend_reserve_mm=14.224,planning_bend_scope='10x assumed1.4224mm OD, not selected wire dynamic-life qualification',main_changed=False,full_harness='BLOCKED',elapsed_s=time.time()-start)
(HERE/'neck_entry_screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
