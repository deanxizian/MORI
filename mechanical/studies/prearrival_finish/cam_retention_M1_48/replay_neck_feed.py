"""Replay stored conservative neck-feed sweeps on explicitly current solids.

The saved sweeps encode terminal travel and local neck-wire relaxation only;
they deliberately do not prove the unseen rest of the harness can be fed.
"""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from current_context import RetentionContext,PROJECT,np,manifold,sha,cache,overlap_boxes
ctx=RetentionContext();started=time.time()
A8=HERE.parent/'harness_A8'
source=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
build=json.loads((source/'construction.json').read_text())
oldcheck=json.loads((source/'verification.json').read_text())
assert oldcheck['source_construction_sha256']==sha(source/'construction.json')
assert oldcheck['status']=='PASS' and build['contact_dimensions_mm']==[1.,1.8,4.1]
targets=ctx.targets.copy()
for name in ['Pitch_Yoke','Pitch_Cradle']:
    targets[name]=ctx.read(HERE/(name+'.npz'))
# Ties are intentionally not closed at this feed step. All 209 named robot
# parts stay in the conservative target set, even where later assembly could
# leave them off; no printed channel is excluded.
rows=[];sweeps={}
for phase in [45,135,225,315]:
    for kind in ['contact_sweep','wire_relaxation']:
        path=source/f'{kind}_{phase}.npz';m=ctx.read(path);sweeps[kind,phase]=m
        hits=[];close=[]
        for name,t in targets.items():
            if not overlap_boxes(m,t,0.):continue
            volume=float((m^t).volume())
            if volume>1e-7:hits.append(dict(target=name,padded_overlap_mm3=volume))
            close.append(name)
        rows.append(dict(phase_deg=phase,kind=kind,status='BLOCKED' if hits else 'PASS',
                         source=str(path.relative_to(PROJECT)),source_sha256=sha(path),hits=hits,
                         target_count=len(targets),overlapping_aabbs=close))
        print('CURRENT_NECK_FEED',phase,kind,rows[-1]['status'],hits,flush=True)
pairs=[]
for a,b in itertools.combinations([45,135,225,315],2):
    cases=[]
    for ka,kb in itertools.product(['contact_sweep','wire_relaxation'],repeat=2):
        l,r=sweeps[ka,a],sweeps[kb,b]
        v=float((l^r).volume()) if overlap_boxes(l,r) else 0.
        cases.append(dict(a=ka,b=kb,padded_overlap_mm3=v))
    pairs.append(dict(phases=[a,b],status='PASS' if all(r['padded_overlap_mm3']<1e-7 for r in cases) else 'BLOCKED',cases=cases))
ctx.assert_unchanged()
result=dict(status='PASS' if all(r['status']=='PASS' for r in rows+pairs) else 'BLOCKED',
            scope='Explicit stored padded local neck-feed sweeps on current M1.48 with three unadopted print candidates; not complete wire supply',
            **ctx.evidence(),script_sha256=sha(__file__),context_sha256=sha(HERE/'current_context.py'),
            source_construction_sha256=sha(source/'construction.json'),source_sweep_verification_sha256=sha(source/'verification.json'),
            contact_dimensions_mm=build['contact_dimensions_mm'],contact_evidence=build['contact_evidence'],
            inherited_interpolation_error_bound_mm=build['interpolation_error_bound_mm'],
            inherited_contact_gap_lower_bound_mm=oldcheck['contact_gap_lower_bound_mm'],
            inherited_wire_gap_lower_bound_mm=oldcheck['wire_gap_lower_bound_mm'],
            rows=rows,pairs=pairs,closed_ties='Not installed at this stage; explicitly absent',
            all_robot_solids_included=209,mating_allocations=29,fixed_candidate_wires=14,
            loose_body_supply='NOT_TESTED',complete_wire_material='NOT_TESTED',full_sequence='NOT_TESTED',
            actual_terminal_shape='BLOCKED',elapsed_s=time.time()-started)
(HERE/'neck_feed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CURRENT_NECK_FEED_DONE',result['status'],flush=True)
