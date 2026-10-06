"""Shift one unassigned capacity strand to the existing rear-right window.

Only candidate wire coordinates change; current native printed solids remain
untouched. The entire previous local strand shape is rotated by32.75degrees.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/rearward_entry_refined';OUT.mkdir(exist_ok=True,parents=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import rotate
from curve_clearance import prepared,pair
from validate import rigidtr
ctx=Context();start=time.time()
source=HERE/'front_neck_candidates.npz';data=np.load(source)
neck={k:data[k] for k in data.files}
for yaw in range(-60,61,10):neck[f'wire1_y{yaw}']=rotate(neck[f'wire1_y{yaw}'],-32.75)
original=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
hits=[];checks=0;pairs=[]
for yaw in range(-60,61,10):
    p=neck[f'wire1_y{yaw}']
    for group,t in targets.items():
        ctx.targets=t
        for pitch in (range(-20,26,5) if group=='pitch' else [0]):
            tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=.00001,radius=.7112)
            checks+=1
            if hit:hits.append(dict(yaw=yaw,pitch=pitch,group=group,**hit))
    a=prepared(p,.7112,.00001)
    for slot in range(11):
        if slot==1:continue
        pairs.append(dict(yaw=yaw,a=1,b=slot,**pair(a,prepared(neck[f'wire{slot}_y{yaw}'],.7112 if slot<7 else .3302,.00001))))
    print('REARWARD_ENTRY',yaw,'solid_hits',len(hits),'pair_hits',sum(r['status']!='PASS' for r in pairs),flush=True)
ctx.targets=original;ctx.assert_unchanged()
np.savez_compressed(OUT/'neck_candidates.npz',**neck)
r=dict(status='PASS' if not hits and all(r['status']=='PASS' for r in pairs) else 'BLOCKED',
    sources=ctx.sources,source_curve_sha256=sha(source),curve_sha256=sha(OUT/'neck_candidates.npz'),
    changed_slot=1,from_phase_deg=22,to_phase_deg=-10.75,checks=checks,hits=hits,pair_checks=pairs,
    OD_mm=1.4224,scope='One local capacity strand moved within existing opening, current solids and local11-line pairs only',
    unchanged_slots=list(range(1))+list(range(2,11)),full_harness='BLOCKED',main_changed=False,
    wire_selection='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'neck_screen.json').write_text(json.dumps(r,indent=2)+'\n')
print('REARWARD_DONE',r['status'],flush=True)
