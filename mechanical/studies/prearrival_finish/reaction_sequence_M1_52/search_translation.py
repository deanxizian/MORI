"""Try a small fore/aft bench offset before lifting the current collar.

Uses the current native yoke, including the adopted larger neck. No C6, guide
or clamp candidate is substituted. Records finite screening separately from
the denser translation-distance bound.
"""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import P
ctx=Context();started=time.time();assert P['revision']=='V1.2-M1.52'
baseline=json.loads((OUT/'initial.json').read_text());assert baseline['source_blend_sha256']==ctx.source_hash
names=['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Lock_Screw']
moving={n:ctx.ss[n].m for n in names};fixture=ctx.ss['Pitch_Yoke'].m

def path(offset,step):
    a=np.array([0.,offset,0.]);b=a+np.array([0.,0.,110.])
    return np.r_[np.linspace(np.zeros(3),a,max(1,int(np.ceil(abs(offset)/step)))+1),
                 np.linspace(a,b,int(np.ceil(110/step))+1)[1:]]

def evaluate(poses,gap_cap=.6):
    smallest=100.;witness=None;checked=0
    for v in poses:
        checked+=1
        for n,m in moving.items():
            p=m.translate(v.tolist());overlap=max(0.,float((p^fixture).volume()))
            gap=0 if overlap>1e-6 else float(p.min_gap(fixture,gap_cap))
            if gap<smallest:smallest=gap;witness=dict(part=n,shift_mm=v.tolist(),overlap_mm3=overlap,gap_mm=gap)
            if overlap>1e-6:return dict(status='BLOCKED',checked_samples=checked,minimum_sampled_gap_mm=smallest,witness=witness)
    return dict(status='PASS',checked_samples=checked,minimum_sampled_gap_mm=smallest,witness=witness)

rows=[];chosen=None
for offset in [1.75,2.0,2.25,1.5,2.5,1.25,2.75,-1.75,-2.0]:
    poses=path(offset,.5);r=evaluate(poses)
    rows.append(dict(offset_y_mm=offset,screen_step_mm=.5,**r))
    print('OFFSET_BENCH_SCREEN',offset,r,flush=True)
    if r['status']=='PASS' and r['minimum_sampled_gap_mm']>.06:
        chosen=offset;break
refinement=None
if chosen is not None:
    poses=path(chosen,.05);r=evaluate(poses)
    maximum_step=float(np.linalg.norm(np.diff(poses,axis=0),axis=1).max())
    lower_bound=r['minimum_sampled_gap_mm']-maximum_step/2
    refinement=dict(**r,step_mm=maximum_step,continuous_gap_lower_bound_mm=lower_bound,
                    method='Rigid translation distance to a fixed closed solid is 1-Lipschitz; each interval is bounded from its two endpoints. Numerical mesh uncertainty and manufacturing tolerances are not physical qualification.',
                    translation_bound_status='PASS' if r['status']=='PASS' and lower_bound>.001 else 'BLOCKED',
                    poses_mm=poses.tolist())
ctx.assert_unchanged()
report=dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,sources=ctx.sources,
            status='PASS' if refinement and refinement['translation_bound_status']=='PASS' else 'BLOCKED',
            scope='Detached bare-yoke collar subassembly only; not whole assembly or horn qualification',
            rows=rows,chosen_offset_y_mm=chosen,refinement=refinement,moving=names,fixture=['Pitch_Yoke'],
            main_changed=False,C6_applied=False,physical_fit='NOT_TESTED',final_horn_and_fasteners='BLOCKED',
            full_reaction_preassembly='BLOCKED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'translation_search.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('OFFSET_BENCH_DONE',report['status'],chosen,report['elapsed_s'],flush=True)
