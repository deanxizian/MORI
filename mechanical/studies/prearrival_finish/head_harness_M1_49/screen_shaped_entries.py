"""No print changes: all11 local routes checked at higher body datums."""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import P
from validate import rigidtr
from route_family import family,rotate
ctx=Context();start=time.time();targets=ctx.targets
group={n:s.group for n,s in ctx.ss.items()}
bygroup={g:{n:s for n,s in targets.items() if group.get(n,'body')==g or (g=='body' and group.get(n,'body') not in ['yaw','pitch'])} for g in ['body','yaw','pitch']}
results=[];saved={};slots=P['neck_harness_capacity']['wire_allocations']
for z,dip in [(136.,.15),(138.,.2),(138.,.35),(138.,.5),(139.5,.35)]:
 rows=family(z0=z,dip=dip);chord=max(r['chord_error_mm'] for r in rows)
 data={f'wire{i}_y{r["yaw_deg"]}':rotate(r['points'],slot['angle_deg']) for i,slot in enumerate(slots) for r in rows}
 failures=[];checks=0
 for i,slot in enumerate(slots):
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
 result=dict(body_entry_z_mm=z,dip_mm=dip,status='PASS' if not failures and bend>=14.224 else 'BLOCKED',checks=checks,hits=failures,minimum_sampled_bend_mm=bend,length_mm=rows[0]['length_mm'],max_chord_error_mm=chord)
 results.append(result)
 if result['status']=='PASS':saved.update({f'z{z}_dip{dip}_{k}':v for k,v in data.items()})
 print('SHAPED_ENTRY',result,flush=True)
ctx.targets=targets;ctx.assert_unchanged()
np.savez_compressed(HERE/'shaped_entry_candidates.npz',**saved)
r=dict(status='PASS' if saved else 'BLOCKED',sources=ctx.sources,results=results,curve_file_sha256=sha(HERE/'shaped_entry_candidates.npz'),script_sha256=sha(Path(__file__)),family_sha256=sha(HERE/'route_family.py'),full_harness='BLOCKED',wire_wire='NOT_TESTED',main_changed=False,elapsed_s=time.time()-start)
(HERE/'shaped_entry_screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
