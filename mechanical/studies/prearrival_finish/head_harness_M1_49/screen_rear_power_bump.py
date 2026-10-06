"""Separate slot 5 from CAM pin 1 without changing the other ten paths."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/rear_separated_neck/review';OLD=HERE/'remaining_routes/left_tall_balanced'
OUT=HERE/'remaining_routes/rear_power_bump';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from route_family import family
from rear_power_bump_geometry import build
from curve_clearance import prepared,pair,self_clear
from validate import rigidtr
ctx=Context();start=time.time();read=lambda p:json.loads(p.read_text())
review=read(BASE/'review.json');nr=read(OLD/'neck_screen.json')
for r in [review,nr]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert review['ten_local_paths']=='PASS' and sha(BASE/'curves.npz')==review['curve_sha256']
assert sha(OLD/'neck_candidates.npz')==nr['curve_sha256']
retained=np.load(BASE/'curves.npz');old=np.load(OLD/'neck_candidates.npz');lane=next(r for r in nr['results'] if r['status']=='PASS')
parent=read(HERE/'remaining_routes/rear_separated_neck/neck_screen.json')
case=next(r for r in parent['results'] if r['power4_extra_radial_dip_mm']==1.1)
other_error=max(lane['chord_error_mm'],max(r['chord_error_mm'] for r in case['curvature']))
other={(slot,yaw):prepared(retained[f'wire{slot}_y{yaw}'],nr['OD_mm'][slot]/2,other_error) for slot,yaw in itertools.product(range(11),range(-60,61,10)) if slot!=5}
rows={r['yaw_deg']:r for r in family(z0=149.,dip=.6,samples=7201)}
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
radius=nr['OD_mm'][5]/2;results=[];saved={}
# Keep delayed case 10 endpoints, adding a local angular separation that
# returns to zero at Z193. No adjacent paths or printed geometry change.
params=[dict(turn=82.,dip=.4,offset=(-1.,-2.5),offset_start=191.,offset_end=206.,end_z=206.,mid_bump_deg=bump)
        for bump in [.5,1.,1.5,2.]]
for index,params_i in enumerate(params):
    curves={};meta={};hits=[];pairs=[];self_rows=[];checks=0
    for yaw,row in rows.items():
        curves[yaw],meta[yaw]=build(row,old[f'z149.0_dip0.6_wire5_y{yaw}'],lane['angles_deg'][5],**params_i)
    minbend=min(r['minimum_sampled_bend_mm'] for r in meta.values())
    stage='bend';success=False
    if minbend>=7.:
        # Early native witnesses avoid running a full grid for a failed route.
        stage='yaw_native';ctx.targets=targets['yaw']
        for yaw in [0,60,-60]+[y for y in rows if y not in [0,60,-60]]:
            tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=curves[yaw]
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=meta[yaw]['chord_error_mm'],radius=radius);checks+=1
            if hit:hits.append(dict(yaw=yaw,pitch=0,group='yaw',**hit));break
        if not hits:
            stage='pairs';pack={y:prepared(curves[y],radius,meta[y]['chord_error_mm']) for y in rows}
            for yaw in rows:
                for slot in range(11):
                    if slot==5:continue
                    q=dict(yaw=yaw,a=5,b=slot,**pair(pack[yaw],other[slot,yaw]));pairs.append(q)
                    if q['status']!='PASS':break
                if pairs[-1]['status']!='PASS':break
            if all(p['status']=='PASS' for p in pairs):
                stage='complete_native'
                for yaw in rows:
                    self_rows.append(dict(yaw=yaw,**self_clear(pack[yaw])))
                    for group in ['body','pitch']:
                        ctx.targets=targets[group]
                        for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                            tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch)));p=curves[yaw]
                            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=meta[yaw]['chord_error_mm'],radius=radius);checks+=1
                            if hit:hits.append(dict(yaw=yaw,pitch=pitch,group=group,**hit))
                success=not hits and all(r['status']=='PASS' for r in self_rows)
                assert checks==156 and len(pairs)==130 and len(self_rows)==13
    r=dict(index=index,params=params_i,status='PASS' if success else 'BLOCKED',stage=stage,hits=hits,pairs=pairs,self_checks=self_rows,
           native_checks=checks,curvature=[dict(yaw=y,**m) for y,m in meta.items()],minimum_sampled_bend_mm=minbend)
    results.append(r);print('POWER_BUMP',index,r['status'],stage,minbend,hits[:1],[(p['a'],p['b'],p['yaw']) for p in pairs if p['status']!='PASS'],flush=True)
    if success:
        saved={k:retained[k] for k in retained.files};saved.update({f'wire5_y{y}':p for y,p in curves.items()});break
ctx.targets=native;ctx.assert_unchanged()
if saved:np.savez_compressed(OUT/'curves.npz',**saved)
inputs=[BASE/'review.json',BASE/'curves.npz',OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'remaining_routes/rear_separated_neck/neck_screen.json',HERE/'rear_power_bump_geometry.py',HERE/'route_family.py',HERE/'curve_clearance.py',HERE/'remaining_routes/rear_power_delayed/neck_screen.json']
r=dict(status='PASS' if saved else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
       retained_ten_paths='byte-identical arrays; native and 585 pair checks retained from hashed review',changed_slot=5,OD_mm=nr['OD_mm'],
       curve_sha256=sha(OUT/'curves.npz') if saved else None,main_changed=False,C6_main_applied=False,full_harness='BLOCKED',constant_length='BLOCKED',
       scope='Local eleven-conductor neck candidate only; unchanged solids and lower entries. Complete upper connections, length compensation and wired assembly remain open.',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'neck_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('POWER_BUMP_DONE',r['status'],r['elapsed_s'],flush=True)
