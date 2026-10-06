"""Screen fixed-yaw transitions to a rearward CAM pitch-loop candidate.

Only independent route files are written. A four-pin native screen does not
mean the transitions can coexist; the separate packing check is mandatory.
"""
from pathlib import Path
import argparse,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['rear3','rear5','rear7'],default='rear3')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
CASE=args.case;LOOP=HERE/'remaining_routes/cam_rearward_loops';LANE=HERE/'remaining_routes/left_tall_balanced'
OUT=HERE/'remaining_routes/cam_rearward_fans'/CASE;OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from upper_curve_geometry import make
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
nr=read(LANE/'neck_screen.json');loop=read(LOOP/'loop_screen.json');checked=read(LOOP/'refined_pairs.json')
for report in [nr,loop,checked]:
    for name,h in {**report['sources'],**report['inputs']}.items():
        p=ROOT/name if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE/name
        assert sha(p)==h,name
assert nr['status']==checked['status']=='PASS'
assert next(r for r in checked['results'] if r['id']==CASE)['status']=='PASS'
assert sha(LANE/'neck_candidates.npz')==nr['curve_sha256'] and sha(LOOP/'curves.npz')==loop['curve_sha256']
neck=np.load(LANE/'neck_candidates.npz');upper=np.load(LOOP/'curves.npz')
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
arrays={};rows=[];checks=0
waypoints=[None,[-9.,7.],[-8.,7.],[-10.,7.],[-11.,9.],[-12.,9.],[-8.,9.],[-12.7,-8.],[-9.,10.],[-7.,9.]]
for pin,slot in {1:9,2:8,3:7,4:10}.items():
    start=neck[f'z149.0_dip0.6_wire{slot}_y0'][-1];anchor=upper[f'{CASE}_pin{pin}_pitch0'][0]
    accepted=[];failures=[];used={};skipped=0
    for lead,radius,trim,wp in itertools.product([0.,3.,6.,9.,12.,15.,10.5,4.5,7.5,13.5,16.5],[7.,8.,9.,10.],[0.,2.,4.],waypoints):
        bucket=(tuple(wp) if wp else None,trim);bucket_leads=used.setdefault(bucket,set())
        if len(bucket_leads)>=4 or lead in bucket_leads:continue
        end=anchor+[0,0,trim];candidate=make(start,end,radius,lead,wp)
        if candidate is None:skipped+=1;continue
        points,length,error=candidate;case=dict(pin=pin,slot=slot,loop_case=CASE,radius_mm=radius,lead_mm=lead,anchor_trim_mm=trim,waypoint_xy_mm=wp)
        ctx.targets=native;hit=ctx.clear(points,chord_error=error,radius=.3302);checks+=1
        if not hit:
            for group,t in targets.items():
                ctx.targets=t
                for yaw,pitch in itertools.product(range(-60,61,10) if group=='body' else [0],range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                    hit=ctx.clear(points@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=.3302);checks+=1
                    if hit:hit=dict(hit,group=group,yaw=yaw,pitch=pitch);break
                if hit:break
        if hit:failures.append(dict(case,**hit));continue
        key=f'{CASE}_pin{pin}_fan{len(accepted)}';arrays[key]=points;bucket_leads.add(lead)
        accepted.append(dict(case,id=key,length_mm=length,chord_error_mm=error,start_mm=start.tolist(),end_mm=end.tolist()))
    rows.append(dict(pin=pin,status='PASS' if accepted else 'BLOCKED',candidates=accepted,failures=failures,no_geometric_solution=skipped))
    print('REARWARD_FAN_PIN',CASE,pin,len(accepted),len(failures),flush=True)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'fan_candidates.npz',**arrays)
inputs=[LANE/'neck_screen.json',LANE/'neck_candidates.npz',LOOP/'loop_screen.json',LOOP/'curves.npz',LOOP/'refined_pairs.json',HERE/'upper_curve_geometry.py']
r=dict(status='PASS' if all(r['candidates'] for r in rows) else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    loop_case=CASE,rows=rows,checks=checks,curve_sha256=sha(OUT/'fan_candidates.npz'),
    scope='Individual current-solid screens of four fixed-yaw fans; no mutual or upper/local joining proof',
    sampling='Up to four distinct accepted leads per waypoint and trim bucket',wire_OD_mm=.6604,required_gap_mm=.3,
    wire_wire='NOT_TESTED',full_harness='BLOCKED',main_changed=False,C6_main_applied=False,
    anchors='NOT_TESTED',wired_assembly='NOT_TESTED',supplier_cut_lengths_released=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'fan_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('REARWARD_FAN_DONE',CASE,r['status'],r['elapsed_s'],flush=True)
