"""Target the measured CAD corridor between the pitch servo and CAM loop 2.

The extra waypoint uses pin1's own exact loop X coordinate, eliminating
the old -10/-9 mm grid's side overshoot. This is still route geometry only.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=HERE/'remaining_routes/cam_rearward_fans/rear3';OUT=OLD.parent/'rear3_aligned';OUT.mkdir(exist_ok=True)
LOOP=HERE/'remaining_routes/cam_rearward_loops';LANE=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from upper_curve_geometry import make
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
fr=read(OLD/'fan_screen.json');nr=read(LANE/'neck_screen.json');lr=read(LOOP/'loop_screen.json');pr=read(LOOP/'refined_pairs.json')
for report in [fr,nr,lr,pr]:
    for name,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/name)==h,name
assert fr['status']==nr['status']==pr['status']=='PASS'
assert sha(OLD/'fan_candidates.npz')==fr['curve_sha256'];assert sha(LOOP/'curves.npz')==lr['curve_sha256'];assert sha(LANE/'neck_candidates.npz')==nr['curve_sha256']
arrays=dict(np.load(OLD/'fan_candidates.npz'));loops=np.load(LOOP/'curves.npz');neck=np.load(LANE/'neck_candidates.npz')
rows=fr['rows'];start=neck['z149.0_dip0.6_wire9_y0'][-1];anchor=loops['rear3_pin1_pitch0'][0]
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
accepted=[];failures=[];checks=0
for wy,lead,radius,trim in itertools.product([7.,7.5,8.,9.,10.],[0.,3.,6.,9.,12.,15.],[7.,8.,9.],[0.,2.,4.]):
    wp=[float(anchor[0]),wy];end=anchor+[0,0,trim];built=make(start,end,radius,lead,wp)
    if built is None:continue
    p,length,error=built;case=dict(pin=1,slot=9,loop_case='rear3',radius_mm=radius,lead_mm=lead,anchor_trim_mm=trim,waypoint_xy_mm=wp)
    ctx.targets=native;hit=ctx.clear(p,radius=.3302,chord_error=error);checks+=1
    if not hit:
        for group,t in targets.items():
            ctx.targets=t
            for yaw,pitch in itertools.product(range(-60,61,10) if group=='body' else [0],range(-20,26,5) if group=='pitch' else [0]):
                tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=error);checks+=1
                if hit:hit=dict(hit,group=group,yaw=yaw,pitch=pitch);break
            if hit:break
    if hit:failures.append(dict(case,**hit));continue
    key=f'rear3_aligned_pin1_{len(accepted)}';arrays[key]=p
    accepted.append(dict(case,id=key,length_mm=length,chord_error_mm=error,start_mm=start.tolist(),end_mm=end.tolist()))
print('ALIGNED_PIN1_OPTIONS',len(accepted),len(failures),flush=True)
rows[0]['candidates'].extend(accepted);rows[0]['failures'].extend(failures)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'fan_candidates.npz',**arrays)
inputs=[OLD/'fan_screen.json',OLD/'fan_candidates.npz',LOOP/'loop_screen.json',LOOP/'curves.npz',LOOP/'refined_pairs.json',LANE/'neck_screen.json',LANE/'neck_candidates.npz',HERE/'upper_curve_geometry.py']
r=dict(status='PASS' if accepted else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    rows=rows,loop_case='rear3',checks=checks,new_pin1_candidates=len(accepted),retained_individual_candidates='Copied only after complete source/hash verification; no old joint proof reused',
    curve_sha256=sha(OUT/'fan_candidates.npz'),main_changed=False,full_harness='BLOCKED',wire_wire='NOT_TESTED',
    scope='Additional native-clear pin1 routes aligned to its original loop plane; joint packing still required',
    wire_OD_mm=.6604,required_gap_mm=.3,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'fan_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('ALIGNED_PIN1_DONE',r['status'],r['elapsed_s'],flush=True)
