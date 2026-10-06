"""Move the temporary pitch loop rearward by shortening its existing tail.

No PCB, connector, printed part or actual fastening feature is modified.
Three planning curves are checked against current solids and the current
eleven local neck paths, before attempting new upper fan connections.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/cam_rearward_loops';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from cam_pitch_loop_geometry import make,trim_tail
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
N=HERE/'remaining_routes/left_tall_balanced';nr=read(N/'neck_screen.json')
ur=read(HERE/'cam_upper_screen.json');A=HERE.parent/'harness_A8/cam_fan_in/short_tail_v2';old=read(A/'screen.json')
for report in [nr,ur]:
    assert report['status']=='PASS'
    for name,h in report['sources'].items():assert sha(ROOT/name)==h,name
    for name,h in report.get('inputs',{}).items():
        root=ROOT if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE
        assert sha(root/name)==h,name
assert sha(A/'curves.npz')==old['curves_sha256'] and sha(A/'tails.npz')==old['tail_curves_sha256']
assert sha(N/'neck_candidates.npz')==nr['curve_sha256']
original_tails=np.load(A/'tails.npz');original_loops=np.load(A/'curves.npz');neck=np.load(N/'neck_candidates.npz')
poses=range(-20,26,5);trans={p:np.asarray(rigidtr(0,p)) for p in poses}
# First verify that the pure helper replays all 40 original curves exactly.
replay=[];target=old['selected'][0]['exact_length_mm']
for pin,p in itertools.product(range(1,5),poses):
    q,row=make(original_tails[f'slot{pin-1}'][-1],trans[p],p,-1.5,230.,target=target)
    previous=original_loops[f'candidate0_slot{pin-1}_pitch{p}'];assert q.shape==previous.shape
    delta=float(np.linalg.norm(q-previous,axis=1).max());assert delta<1e-5
    replay.append(dict(pin=pin,pitch=p,maximum_vertex_delta_mm=delta))
print('REARWARD_HELPER_REPLAY',max(r['maximum_vertex_delta_mm'] for r in replay),flush=True)
native=ctx.targets;groups={name:s.group if s.group in ['yaw','pitch'] else 'body' for name,s in ctx.ss.items()}
targets={g:{name:t for name,t in native.items() if groups.get(name,'body')==g} for g in ['body','yaw','pitch']}
low={};row=next(r for r in nr['results'] if r['status']=='PASS')
for yaw,slot in itertools.product(range(-60,61,10),range(11)):
    tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));q=neck[f'z149.0_dip0.6_wire{slot}_y{yaw}'];q=q@tr[:3,:3].T+tr[:3,3]
    low[yaw,slot]=prepared(q,nr['OD_mm'][slot]/2,row['chord_error_mm'])
results=[];arrays={}
for case,end_y,ay in [('rear3',6.5,-4.5),('rear5',4.5,-6.5),('rear7',2.5,-8.5)]:
    tails={pin:trim_tail(original_tails[f'slot{pin-1}'],end_y) for pin in range(1,5)}
    bases=[make(tails[1][-1],trans[p],p,ay,230.) for p in poses]
    if any(b is None for b in bases):
        results.append(dict(id=case,status='BLOCKED',reason='minimum radius'));continue
    target=max(bases)+.02;curves={};metadata=[];hits=[];checks=0
    for pin,p in itertools.product(range(1,5),poses):
        core,m=make(tails[pin][-1],trans[p],p,ay,230.,target=target)
        tail=tails[pin][::-1]@trans[p][:3,:3].T+trans[p][:3,3]
        assert np.linalg.norm(core[-1]-tail[0])<1e-5
        q=np.vstack([core,tail[1:]]);curves[pin,p]=q;metadata.append(dict(pin=pin,**m))
        for group,t in targets.items():
            ctx.targets=t
            for yaw in (range(-60,61,10) if group=='body' else [0]):
                tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(trans[p])
                hit=ctx.clear(q@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=.0003);checks+=1
                if hit:hits.append(dict(pin=pin,pitch=p,yaw=yaw,group=group,**hit))
        arrays[f'{case}_pin{pin}_pitch{p}']=q
    print('REARWARD_NATIVE',case,len(hits),flush=True)
    mutual=[];self_rows=[];lower_hits=[]
    if not hits:
        items={(pin,p):prepared(q,.3302,.0003) for (pin,p),q in curves.items()}
        for (pin,p),item in items.items():
            self_rows.append(dict(pin=pin,pitch=p,**self_clear(item)))
            for (yaw,slot),lower in low.items():
                r=pair_threshold(item,lower)
                if r['status']!='PASS':lower_hits.append(dict(pin=pin,pitch=p,yaw=yaw,slot=slot,**r))
        for p in poses:
            for a,b in itertools.combinations(range(1,5),2):mutual.append(dict(pitch=p,a=a,b=b,**pair(items[a,p],items[b,p])))
    ok=not hits and len(mutual)==60 and all(r['status']=='PASS' for r in mutual+self_rows) and not lower_hits
    results.append(dict(id=case,status='PASS' if ok else 'BLOCKED',tail_end_y_mm=end_y,anchor_y_mm=ay,anchor_z_mm=230.,
        metadata=metadata,exact_core_length_mm=target,hits=hits,native_checks=checks,mutual=mutual,self_checks=self_rows,lower_conflicts=lower_hits,
        upper_fan_connections='NOT_TESTED',reason='Only existing final straight was shortened; original connector endpoints remain identical'))
    print('REARWARD_CASE',case,results[-1]['status'],'lower_conflicts',len(lower_hits),flush=True)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'curves.npz',**arrays)
inputs=[A/'screen.json',A/'curves.npz',A/'tails.npz',N/'neck_screen.json',N/'neck_candidates.npz',HERE/'cam_upper_screen.json',HERE/'cam_pitch_loop_geometry.py',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
report=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',scope='Rearward pitch-loop candidates versus current native solids and eleven local neck paths; no complete endpoint or upper transition proof',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},helper_baseline_replay=replay,
    results=results,curve_sha256=sha(OUT/'curves.npz'),main_changed=False,full_harness='BLOCKED',anchors='NOT_TESTED',
    wired_assembly='NOT_TESTED',supplier_cut_lengths_released=False,physical_behavior='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'loop_screen.json').write_text(json.dumps(report,indent=2)+'\n');print('REARWARD_LOOPS_DONE',report['status'],report['elapsed_s'],flush=True)
