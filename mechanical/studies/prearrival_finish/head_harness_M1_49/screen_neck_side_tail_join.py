"""Target only the three upper neck paths crossed by the side-return tails."""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/rear_power_bump';T=HERE/'remaining_routes/cam_side_return'
OLD=HERE/'remaining_routes/left_tall_balanced';OUT=HERE/'remaining_routes/neck_side_tail_join';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from route_family import family
from neck_upper_offset_geometry import build
from cam_pitch_loop_geometry import line
from curve_clearance import prepared,pair,self_clear
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());nr=read(N/'neck_screen.json');tr=read(T/'tail_screen.json');lane=read(OLD/'neck_screen.json')
for r in [nr,tr,lane]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(N/'curves.npz')==nr['curve_sha256'];nc=np.load(N/'curves.npz')
assert sha(OLD/'neck_candidates.npz')==lane['curve_sha256'];old=np.load(OLD/'neck_candidates.npz');lanec=next(r for r in lane['results'] if r['status']=='PASS')
tailcase=next(r for r in tr['results'] if r['direction']==-1. and r['base_radius_mm']==7.5)
assert not tailcase['hits'] and tailcase['native_checks']==1560 and all(r['status']=='PASS' for r in tailcase['pairs']+tailcase['self_checks'])
changed=[4,8,9];assert all(r['slot'] in changed for r in tailcase['lower_conflicts'])
angles=lanec['angles_deg'];turns={4:87.,8:89.,9:85.};poses=range(-20,26,5);yaws=range(-60,61,10);rows={r['yaw_deg']:r for r in family(z0=149.,dip=.6,samples=7201)}
tails={};tail_items={};replay=[]
for m in tailcase['metadata']:
    pin=m['pin'];start=np.asarray(m['start_mm']);radius=m['radius_mm'];a=start+[0.,0.,-5.]
    aa=np.linspace(0.,math.pi,math.ceil(math.pi*radius/.01)+1);arc=a+np.c_[-radius*(1-np.cos(aa)),np.zeros(len(aa)),-radius*np.sin(aa)]
    p=np.vstack([line(start,a,.01)[:-1],arc]);assert np.linalg.norm(p[-1]-m['end_mm'])<1e-8;tails[pin]=p
    for pitch in poses:
        mat=np.asarray(rigidtr(0,pitch));tail_items[pin,pitch]=prepared(p@mat[:3,:3].T+mat[:3,3],.3302,.0003)
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
other={(s,y):prepared(nc[f'wire{s}_y{y}'],nr['OD_mm'][s]/2,.0003) for s,y in itertools.product(range(11),yaws) if s not in changed}
results=[];saved={}
for shift_y,start_z in [(1.,190.),(1.4,190.),(1.8,190.),(1.,188.)]:
    curves={};meta={};hits=[];checks=0;pairs=[];self_rows=[];tail_hits=[];tail_checks=0
    for s,y in itertools.product(changed,yaws):
        p,m=build(rows[y],old[f'z149.0_dip0.6_wire{s}_y{y}'],s,angles,turns,shift_y,start_z,204.);curves[s,y]=p;meta[s,y]=m
        original=nc[f'wire{s}_y{y}'];assert np.array_equal(p[p[:,2]<start_z],original[original[:,2]<start_z])
    bend=min(m['minimum_sampled_bend_mm'] for m in meta.values());stage='bend';ok=False
    if bend>=7.:
        stage='native'
        for s,y in itertools.product(changed,yaws):
            p=curves[s,y];err=meta[s,y]['chord_error_mm']
            for group,tg in targets.items():
                ctx.targets=tg
                for pitch in (poses if group=='pitch' else [0]):
                    mat=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(y,pitch if group=='pitch' else 0)))
                    hit=ctx.clear(p@mat[:3,:3].T+mat[:3,3],chord_error=err,radius=nr['OD_mm'][s]/2);checks+=1
                    if hit:hits.append(dict(slot=s,yaw=y,pitch=pitch,group=group,**hit));break
                if hits:break
            if hits:break
        if not hits:
            assert checks==468;stage='neck_pairs';pack={**other,**{k:prepared(p,nr['OD_mm'][k[0]]/2,meta[k]['chord_error_mm']) for k,p in curves.items()}}
            for y in yaws:
                for s in changed:self_rows.append(dict(slot=s,yaw=y,**self_clear(pack[s,y])))
                for a,b in itertools.combinations(range(11),2):
                    if not ({a,b}&set(changed)):continue
                    pairs.append(dict(yaw=y,a=a,b=b,**pair(pack[a,y],pack[b,y])))
            assert len(pairs)==351
            if all(r['status']=='PASS' for r in pairs+self_rows):
                stage='tail_pairs'
                for s,y in itertools.product(changed,yaws):
                    mat=np.linalg.inv(np.asarray(rigidtr(y,0)));p=curves[s,y]
                    lower=prepared(refined(p@mat[:3,:3].T+mat[:3,3],.01),nr['OD_mm'][s]/2,meta[s,y]['chord_error_mm'])
                    for pin,pitch in itertools.product(range(1,5),poses):
                        rr=pair_threshold(tail_items[pin,pitch],lower);tail_checks+=1
                        if rr['status']!='PASS':tail_hits.append(dict(pin=pin,slot=s,yaw=y,pitch=pitch,**rr))
                assert tail_checks==1560;ok=not tail_hits
    r=dict(status='PASS' if ok else 'BLOCKED',stage=stage,shift_y_mm=shift_y,start_z_mm=start_z,end_z_mm=204.,changed_slots=changed,
           hits=hits,native_checks=checks,pairs=pairs,self_checks=self_rows,tail_conflicts=tail_hits,tail_pair_checks=tail_checks,
           minimum_sampled_bend_mm=bend,curvature=[dict(slot=s,yaw=y,**m) for (s,y),m in meta.items()])
    results.append(r);print('SIDE_TAIL_JOIN',shift_y,start_z,r['status'],stage,hits[:1],len(tail_hits),sum(r['status']!='PASS' for r in pairs),flush=True)
    if ok:
        saved={k:nc[k] for k in nc.files};saved.update({f'wire{s}_y{y}':p for (s,y),p in curves.items()});break
ctx.targets=native;ctx.assert_unchanged()
if saved:
    np.savez_compressed(OUT/'neck_curves.npz',**saved);np.savez_compressed(OUT/'tails.npz',**{f'pin{p}':t for p,t in tails.items()})
inputs=[N/'neck_screen.json',N/'curves.npz',T/'tail_screen.json',OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'route_family.py',HERE/'neck_upper_offset_geometry.py',HERE/'rear_power_geometry.py',HERE/'cam_pitch_loop_geometry.py',HERE/'curve_clearance.py',HERE/'upper_pack_geometry.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if saved else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
       neck_curve_sha256=sha(OUT/'neck_curves.npz') if saved else None,tail_sha256=sha(OUT/'tails.npz') if saved else None,
       reused_tail_native_checks=1560,reused_tail_mutual_pairs=780,reused_tail_neck_pairs=4160,reused_neck_mutual_pairs=364,
       OD_mm=nr['OD_mm'],main_changed=False,C6_main_applied=False,full_harness='BLOCKED',constant_length='BLOCKED',
       scope='Three changed upper neck ends versus current solids, other eight neck paths and four moving side tails. Connecting upper loops/fans are absent.',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'join_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('SIDE_TAIL_JOIN_DONE',r['status'],r['elapsed_s'],flush=True)
