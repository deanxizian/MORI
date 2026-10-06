"""Move only wire entry stations within the existing window, not any print.

This independent alternative reduces the low reverse bends at the PCB ends.
Seven large wires use the unselected 2622 maximum OD reference for screening;
the smaller two speaker wires still have no selected SKU or complete ends.
"""
from pathlib import Path
import json,sys,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/higher_entry';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family,rotate
from curve_clearance import prepared,pair
from validate import rigidtr
ctx=Context();start=time.time();native=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
angles=[11,22,33,125,144,163,0,49,135,153,42];results=[];arrays={}
for z,dip in [(142.,.6),(143.5,.9)]:
    rows=family(z0=z,dip=dip,samples=7201);error=max(r['chord_error_mm'] for r in rows)
    curves={f'wire{i}_y{r["yaw_deg"]}':rotate(r['points'],angles[i]) for i in range(11) for r in rows}
    hits=[];checks=0;pairs=[]
    for i in range(11):
        radius=.5842 if i<7 else .3302
        for yaw in range(-60,61,10):
            p=curves[f'wire{i}_y{yaw}']
            for group,t in targets.items():
                ctx.targets=t
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=radius);checks+=1
                    if hit:hits.append(dict(slot=i,yaw=yaw,pitch=pitch,group=group,**hit))
        print('HIGHER_NECK',z,dip,'slot',i,'hits',len(hits),flush=True)
    for yaw in range(-60,61,10):
        items={i:prepared(curves[f'wire{i}_y{yaw}'],.5842 if i<7 else .3302,error) for i in range(11)}
        for a,b in itertools.combinations(items,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    bend=min(r['minimum_sampled_bend_mm'] for r in rows)
    result=dict(z0_mm=z,dip_mm=dip,status='PASS' if not hits and all(r['status']=='PASS' for r in pairs) and bend>=7 else 'BLOCKED',
        angles_deg=angles,hits=hits,checks=checks,pair_checks=pairs,minimum_sampled_bend_mm=bend,
        length_mm=rows[0]['length_mm'],chord_error_mm=error)
    results.append(result);arrays.update({f'z{z}_'+k:v for k,v in curves.items()})
    print('HIGHER_NECK_DONE',z,result['status'],flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(OUT/'neck_candidates.npz',**arrays)
report=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',sources=ctx.sources,results=results,
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [HERE/'route_family.py',HERE/'curve_clearance.py',HERE/'remaining_routes/sources/alpha_2622_facts.json']},
    curve_sha256=sha(OUT/'neck_candidates.npz'),OD_mm=[1.1684]*7+[.6604]*4,main_changed=False,
    scope='Eleven local unselected wire-reference curves only; no body prefixes or upper endpoint proof',
    upper_loops='NOT_TESTED',body_prefixes='NOT_TESTED',full_harness='BLOCKED',wire_selection='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'neck_screen.json').write_text(json.dumps(report,indent=2)+'\n')
