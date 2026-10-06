"""Bounded short-lead alternatives with current solids and all pitch wire poses."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes'; FULL=BASE/'static_flex/full_route'; OUT=FULL/'short_lead'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts')); sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold,Vector
from validate import rigidtr
from upper_pack_geometry import refined
from full_static_flex_mixed_geometry import solve,ribbon
ctx=Context(); started=time.time(); source=FULL/'screen/review.json'; old=json.loads(source.read_text())
a,b=np.array(old['ends_mm']); curves_path=BASE/'cam_side_fans/c6_join/candidate_curves.npz'; curves=np.load(curves_path)
rows=[]
for lead in [2.,2.5,3.]:
    label=f'L{lead:g}_W10.5'; fit=solve(a,b,lead=lead); g=ribbon(fit)
    m=manifold.Manifold(manifold.Mesh64(g['vertices_mm'],g['triangles'])); assert m.status()==manifold.Error.NoError
    tree=ctx.target(m)['tree']; lo=g['vertices_mm'].min(0); hi=g['vertices_mm'].max(0)
    failures=[]; nearby=[]; wfail=[]; wnear=[]; error=g['metadata']['polygonal_chord_error_bound_mm']
    for name,target in ctx.targets.items():
        if np.any(lo>target['hi']+1) or np.any(hi<target['lo']-1): continue
        overlap=float((m^target['m']).volume()); gap=float(m.min_gap(target['m'],1.))
        item=dict(target=name,overlap_mm3=overlap,gap_mm=gap,gap_search_cap_mm=1.); nearby.append(item)
        if overlap>1e-7 or gap<.3+error: failures.append(item)
    for pitch in range(-20,26,5):
        tr=np.array(rigidtr(0,pitch))
        names=[(f'CAM_{i}_y0_p{pitch}',.6604) for i in range(1,5)]
        names += [(f'P_J9_{i}_y0',1.1684) for i in range(1,4)]
        names += [(f'P_J18_{i}_y0',1.1684) for i in range(1,3)]
        names += [(f'SPK_reservation_{i}_y0',.889) for i in [3,6]]
        for key,diameter in names:
            p=refined(curves[key],.1); p=(p-tr[:3,3])@tr[:3,:3]; bound=diameter/2+.3+.05+error
            ids=np.flatnonzero(np.all(p>=lo-bound,axis=1)&np.all(p<=hi+bound,axis=1))
            if not len(ids): continue
            distance,i=min((float(tree.find_nearest(Vector(p[i]))[3]),int(i)) for i in ids)
            item=dict(pitch=pitch,wire=key,surface_gap_lower_bound_mm=distance-diameter/2-.05-error,point_mm=p[i].tolist())
            wnear.append(item)
            if distance<bound: wfail.append(item)
    np.savez_compressed(OUT/(label+'.npz'),**{k:v for k,v in g.items() if k!='metadata'})
    rows.append(dict(id=label,status='FAIL' if failures or wfail else 'PASS',parameters=g['metadata'],lead_mm=lead,
        nearby_targets=nearby,rigid_failures=failures,wire_failures=wfail,wire_nearby=wnear,wire_checks=110))
    print('FULL_FFC_SHORT_LEAD',label,rows[-1]['status'],'rigid',failures,'wire',len(wfail),flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in rows) else 'BLOCKED',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [source,curves_path,HERE/'full_static_flex_mixed_geometry.py',HERE/'full_static_flex_geometry.py',HERE/'upper_pack_geometry.py']},
    rows=rows,main_changed=False,adopted=False,full_flex_fit='BLOCKED',physical_validation='NOT_TESTED',
    limits='Short lead is capacity only: actual connector stiffener, no-bend length and insertion remain unknown. 110 wire cases are zero yaw with all 10 pitches, not the full 130-pose check.',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('FULL_FFC_SHORT_LEAD_DONE',r['status'],flush=True)
