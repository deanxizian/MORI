"""Create a shared upper neck curve with a straight, staggerable lower entry.

The twist starts later within the existing bore. A straight extension to
Z142 allows individual conductors to join at different heights without
changing the common upper trajectory. No printed solid is changed.
"""
from pathlib import Path
import itertools, json, sys, time
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/stagger_neck'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,rotate
from curve_clearance import prepared,pair
from validate import rigidtr
ctx=Context(); started=time.time(); native=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
angles=[11,22,33,125,144,163,0,49,135,153,42]
results=[];arrays={}
for start,dip in [(147.,.6),(148.,.6),(149.,.6),(147.,.9)]:
    rows=family(z0=start,dip=dip,samples=7201)
    error=max(r['chord_error_mm'] for r in rows)
    curves={}
    for i,row in itertools.product(range(11),rows):
        p=rotate(row['points'],angles[i]);a=p[0].copy();a[2]=142.
        lead=np.linspace(a,p[0],int(np.ceil((start-142.)/.03))+1)
        curves[f'wire{i}_y{row["yaw_deg"]}']=np.vstack([lead,p[1:]])
    checks=0;hits=[];pairs=[]
    for i in range(11):
        for yaw in range(-60,61,10):
            p=curves[f'wire{i}_y{yaw}']; radius=.5842 if i<7 else .3302
            for group,t in targets.items():
                ctx.targets=t
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=radius);checks+=1
                    if hit:hits.append(dict(slot=i,yaw=yaw,pitch=pitch,group=group,**hit))
        print('STAGGER_NECK_SLOT',start,dip,i,'hits',len(hits),flush=True)
    if not hits:
        for yaw in range(-60,61,10):
            items={i:prepared(curves[f'wire{i}_y{yaw}'],.5842 if i<7 else .3302,error) for i in range(11)}
            for a,b in itertools.combinations(items,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    bend=min(r['minimum_sampled_bend_mm'] for r in rows)
    success=not hits and len(pairs)==715 and all(r['status']=='PASS' for r in pairs) and bend>=7.
    result=dict(twist_start_z_mm=start,entry_z_mm=142.,dip_mm=dip,status='PASS' if success else 'BLOCKED',
        angles_deg=angles,hits=hits,checks=checks,pair_checks=pairs,minimum_sampled_bend_mm=bend,
        length_mm=rows[0]['length_mm']+start-142.,chord_error_mm=error)
    results.append(result)
    arrays.update({f'z{start}_dip{dip}_'+k:v for k,v in curves.items()})
    print('STAGGER_NECK_DONE',start,dip,result['status'],flush=True)
    if success:break
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
report=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',
    sources=ctx.sources,results=results,inputs={str(p.relative_to(PROJECT)):sha(p) for p in
    [HERE/'route_family.py',HERE/'curve_clearance.py',HERE/'remaining_routes/sources/alpha_2622_facts.json']},
    curve_sha256=sha(OUT/'neck_candidates.npz'),OD_mm=[1.1684]*7+[.6604]*4,
    scope='Eleven local curves with a shared later twist and variable straight entry; no body connection proof',
    body_prefixes='NOT_TESTED',upper_loops='NOT_TESTED',full_harness='BLOCKED',
    wire_selection='BLOCKED',main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'neck_screen.json').write_text(json.dumps(report,indent=2)+'\n')
