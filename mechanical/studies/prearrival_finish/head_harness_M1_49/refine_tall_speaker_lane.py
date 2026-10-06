"""Resolve the one late-twist local conflict without changing a printed part.

Other ten curves and their finite solid checks are reused exactly. All wire
pairs are rechecked for a surviving speaker phase. No endpoint is approved.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/left_tall_entry';OUT=HERE/'remaining_routes/left_tall_entry_refined';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import rotate
from curve_clearance import prepared,pair
from validate import rigidtr
ctx=Context();started=time.time();source=json.loads((BASE/'neck_screen.json').read_text());row=source['results'][0]
for f,h in {**source['sources'],**source['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(BASE/'neck_candidates.npz')==source['curve_sha256']
assert row['checks']==1716 and row['hits'] and all(h['slot']==6 for h in row['hits'])
curves=dict(np.load(BASE/'neck_candidates.npz'));native=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
attempts=[];selected=None;checks=0
for phase in [3.,3.2,1.5]:
    candidate=dict(curves)
    for yaw in range(-60,61,10):
        key=f'z149.0_dip0.6_wire6_y{yaw}';candidate[key]=rotate(curves[key],phase-2.)
    hits=[]
    for yaw in range(-60,61,10):
        p=candidate[f'z149.0_dip0.6_wire6_y{yaw}']
        for group,t in targets.items():
            ctx.targets=t
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=row['chord_error_mm'],radius=.4445);checks+=1
                if hit:hits.append(dict(slot=6,yaw=yaw,pitch=pitch,group=group,**hit))
    pairs=[]
    if not hits:
        for yaw in range(-60,61,10):
            items={i:prepared(candidate[f'z149.0_dip0.6_wire{i}_y{yaw}'],source['OD_mm'][i]/2,row['chord_error_mm']) for i in range(11)}
            for a,b in itertools.combinations(items,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
    success=not hits and len(pairs)==715 and all(r['status']=='PASS' for r in pairs)
    angles=list(row['angles_deg']);angles[6]=phase
    result=dict(row,status='PASS' if success else 'BLOCKED',angles_deg=angles,hits=hits,pair_checks=pairs,
                checks=1716,new_slot_solid_checks=156,reused_solid_checks=1560,phase_deg=phase)
    attempts.append(result);print('TALL_PHASE',phase,result['status'],len(hits),flush=True)
    if success:selected=candidate;break
ctx.targets=native;ctx.assert_unchanged()
if selected:np.savez_compressed(OUT/'neck_candidates.npz',**selected)
report=dict(source,status='PASS' if selected else 'BLOCKED',results=attempts,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in [BASE/'neck_screen.json',BASE/'neck_candidates.npz',HERE/'route_family.py',HERE/'curve_clearance.py']},
    curve_sha256=sha(OUT/'neck_candidates.npz') if selected else None,
    reused_proof='Ten unchanged native-checked local curves; exact source/input hashes and all original failures isolated to slot6. New slot6 solid checks and all715 wire pairs explicit.',
    new_checks=checks,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'neck_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('TALL_PHASE_DONE',report['status'],report['elapsed_s'],flush=True)
