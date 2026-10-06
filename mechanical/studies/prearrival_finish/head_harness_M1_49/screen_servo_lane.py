"""Finite alternative wire curves inside the unchanged native neck.

The Alpha2622 reference is unselected. Its maximum catalogue OD is used only
for this candidate; all other large strands retain their older capacity OD.
"""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/servo_lane';OUT.mkdir(exist_ok=True,parents=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,rotate
from curve_clearance import prepared,pair
from validate import rigidtr
ctx=Context();start=time.time();source=HERE/'front_neck_candidates.npz'
data=np.load(source);native=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
trials=[];arrays={}
for dip in [.6,.9,1.2]:
    rows=family(z0=138.,dip=dip,samples=7201)
    error=max(r['chord_error_mm'] for r in rows);hits=[];pairs=[];checks=0
    for row in rows:
        yaw=row['yaw_deg'];p=rotate(row['points'],-10.75)
        for group,t in targets.items():
            ctx.targets=t
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=.5842)
                checks+=1
                if hit:hits.append(dict(yaw=yaw,pitch=pitch,group=group,**hit))
        a=prepared(p,.5842,error)
        for slot in range(11):
            if slot==1:continue
            pairs.append(dict(yaw=yaw,slot=slot,**pair(a,prepared(data[f'wire{slot}_y{yaw}'],.7112 if slot<7 else .3302,.00001))))
        arrays[f'dip{dip}_wire1_y{yaw}']=p
    minimum_radius=min(r['minimum_sampled_bend_mm'] for r in rows)
    result=dict(dip_mm=dip,phase_deg=-10.75,status='PASS' if not hits and all(r['status']=='PASS' for r in pairs) and minimum_radius>=6.5 else 'BLOCKED',
        checks=checks,hits=hits,pair_checks=pairs,length_mm=rows[0]['length_mm'],
        minimum_sampled_bend_mm=minimum_radius,chord_error_mm=error)
    trials.append(result)
    print('SERVO_LANE',dip,result['status'],'solid',len(hits),'pairs',sum(p['status']!='PASS' for p in pairs),flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
result=dict(status='PASS' if any(r['status']=='PASS' for r in trials) else 'BLOCKED',sources=ctx.sources,
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [source,HERE/'route_family.py',HERE/'curve_clearance.py',HERE/'remaining_routes/sources/alpha_2622_facts.json']},
    results=trials,curve_sha256=sha(OUT/'neck_candidates.npz'),changed_slot=1,OD_mm=1.1684,
    scope='Unselected wire lane only; native finite motion and local strand spacing',main_changed=False,
    body_prefix='NOT_TESTED',upper_endpoint='BLOCKED',wire_selection='BLOCKED',full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'neck_screen.json').write_text(json.dumps(result,indent=2)+'\n')
