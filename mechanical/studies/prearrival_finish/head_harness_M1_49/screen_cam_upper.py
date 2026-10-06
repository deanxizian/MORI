"""Recheck historical CAM loop/tail coordinates against current M1.49 solids.

Load arrays as candidate geometry only. Never execute their generating script
prefixes, reuse historical solid PASS, or substitute an unapproved print.
"""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context,np,sha
from validate import rigidtr
ctx=Context();started=time.time();A8=HERE.parent/'harness_A8'
src=A8/'cam_fan_in/short_tail_v2'
meta=json.loads((src/'screen.json').read_text())
assert sha(src/'curves.npz')==meta['curves_sha256']
assert sha(src/'tails.npz')==meta['tail_curves_sha256']
loops=np.load(src/'curves.npz');tails=np.load(src/'tails.npz')
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
rows=[];paths={};hits=[];checks=0
for slot,pitch in itertools.product(range(4),range(-20,26,5)):
    loop=loops[f'candidate0_slot{slot}_pitch{pitch}'];tail=tails[f'slot{slot}'][::-1]
    tp=np.asarray(rigidtr(0,pitch));posed_tail=tail@tp[:3,:3].T+tp[:3,3]
    assert np.linalg.norm(loop[-1]-posed_tail[0])<1e-5
    curve=np.vstack([loop,posed_tail[1:]])
    # Retained tail samples reach 0.040901 mm. The actual maximum step is
    # included by Context.clear() in its conservative surface-distance bound.
    assert np.max(np.linalg.norm(np.diff(curve,axis=0),axis=1))<.05
    paths[f'slot{slot}_pitch{pitch}']=curve
    # Conservative 0.0003 mm bound covers the original circular/cubic sources.
    # Curve construction and matching endpoint proofs are separate from collision.
    for group,t in targets.items():
        ctx.targets=t
        for yaw in (range(-60,61,10) if group=='body' else [0]):
            ty=np.asarray(rigidtr(yaw,0))
            tr=ty if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(tp)
            q=curve@tr[:3,:3].T+tr[:3,3]
            issue=ctx.clear(q,chord_error=.0003,radius=.6604/2)
            checks+=1
            if issue:hits.append(dict(slot=slot,pitch=pitch,yaw=yaw,group=group,**issue))
    rows.append(dict(slot=slot,pitch=pitch,length_mm=float(np.linalg.norm(np.diff(curve,axis=0),axis=1).sum()),
        start_mm=curve[0].tolist(),end_mm=curve[-1].tolist()))
    print('CAM_UPPER',slot,pitch,'hits',len(hits),flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(HERE/'cam_upper_candidates.npz',**paths)
report=dict(status='PASS' if not hits else 'BLOCKED',source_blend_sha256=ctx.source_hash,
    sources=ctx.sources,inputs={str(p.relative_to(PROJECT)):sha(p) for p in [src/'curves.npz',src/'tails.npz',src/'screen.json',src/'math_bounds.json']},
    curve_sha256=sha(HERE/'cam_upper_candidates.npz'),checks=checks,hits=hits,rows=rows,
    scope='CAM pitch loops and photo-based port tails versus current native solids at13yaw/10pitch samples; neck fan-in still missing',
    historical_collision_evidence_reused=False,main_changed=False,substituted_prints=[],
    source_chord_error_bound_mm=.0003,wire_OD_mm=.6604,required_gap_mm=.3,
    connector_crimp_exit='ASSUMED',full_endpoint_routing='BLOCKED',wire_wire='NOT_TESTED',
    anchors='NOT_TESTED',wired_assembly='NOT_TESTED',supplier_cut_lengths_released=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(HERE/'cam_upper_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_UPPER_DONE',report['status'],'checks',checks,'hits',len(hits),flush=True)
