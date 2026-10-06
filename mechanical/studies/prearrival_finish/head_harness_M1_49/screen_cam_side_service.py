"""Add a compensated service loop to the collision-free side-return tails."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/neck_side_tail_gentle';OUT=HERE/'remaining_routes/cam_side_service';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from cam_side_service_geometry import make
from curve_clearance import prepared,pair,self_clear
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());nr=read(N/'join_screen.json')
for f,h in {**nr['sources'],**nr['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(N/'neck_curves.npz')==nr['neck_curve_sha256'] and sha(N/'tails.npz')==nr['tail_sha256']
nc=np.load(N/'neck_curves.npz');tails=np.load(N/'tails.npz');mapping={1:9,2:8,3:7,4:10};poses=range(-20,26,5);yaws=range(-60,61,10)
lengths={pin:{y:float(np.linalg.norm(np.diff(nc[f'wire{s}_y{y}'],axis=0),axis=1).sum()) for y in yaws} for pin,s in mapping.items()}
maxlen={pin:max(ls.values()) for pin,ls in lengths.items()}
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
lower={};results=[];arrays={}
for yaw,s in itertools.product(yaws,range(11)):
    tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=nc[f'wire{s}_y{yaw}'];lower[yaw,s]=prepared(refined(p@tr[:3,:3].T+tr[:3,3],.01),nr['OD_mm'][s]/2,.0003)
for ay,az,lead in [(-11.,224.,3.),(-12.,224.,3.),(-11.,224.,1.5),(-10.,224.,3.)]:
    base=max(make(tails['pin1'][-1],np.asarray(rigidtr(0,p)),p,ay,az,lead) for p in poses)+.02
    curves={};metadata=[];hits=[];checks=0
    for pin,yaw,pitch in itertools.product(mapping,yaws,poses):
        pt=np.asarray(rigidtr(0,pitch));yt=np.asarray(rigidtr(yaw,0));target=base+maxlen[pin]-lengths[pin][yaw]
        core,m=make(tails[f'pin{pin}'][-1],pt,pitch,ay,az,lead,target=target)
        end=tails[f'pin{pin}'][::-1]@pt[:3,:3].T+pt[:3,3];assert np.linalg.norm(core[-1]-end[0])<1e-7
        p=np.vstack([core,end[1:]]);curves[pin,yaw,pitch]=p
        metadata.append(dict(pin=pin,yaw=yaw,neck_length_mm=lengths[pin][yaw],compensation_mm=maxlen[pin]-lengths[pin][yaw],**m))
        for group,tg in targets.items():
            ctx.targets=tg;tr=yt if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(pt)
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=.0003);checks+=1
            if hit:hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,group=group,**hit));break
        if hits:break
    pairs=[];self_rows=[];lower_hits=[]
    if not hits:
        items={key:prepared(refined(p,.01),.3302,.0003) for key,p in curves.items()}
        for (pin,yaw,pitch),item in items.items():
            self_rows.append(dict(pin=pin,yaw=yaw,pitch=pitch,**self_clear(item)))
            for s in range(11):
                r=pair_threshold(item,lower[yaw,s])
                if r['status']!='PASS':lower_hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,slot=s,**r))
        for yaw,pitch in itertools.product(yaws,poses):
            for a,b in itertools.combinations(mapping,2):pairs.append(dict(yaw=yaw,pitch=pitch,a=a,b=b,**pair(items[a,yaw,pitch],items[b,yaw,pitch])))
        assert checks==1560 and len(self_rows)==520 and len(pairs)==780
    ok=not hits and not lower_hits and bool(pairs) and all(x['status']=='PASS' for x in pairs+self_rows)
    row=dict(status='PASS' if ok else 'BLOCKED',anchor_y_mm=ay,anchor_z_mm=az,lead_mm=lead,base_core_length_mm=base,
        hits=hits,native_checks=checks,pairs=pairs,self_checks=self_rows,lower_conflicts=lower_hits,metadata=metadata)
    results.append(row);print('CAM_SIDE_SERVICE',ay,az,lead,row['status'],hits[:1],len(lower_hits),sum(r['status']!='PASS' for r in pairs),flush=True)
    if ok:
        arrays={f'pin{p}_y{y}_p{pt}':q for (p,y,pt),q in curves.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'curves.npz',**arrays)
inputs=[N/'join_screen.json',N/'neck_curves.npz',N/'tails.npz',HERE/'cam_side_service_geometry.py',HERE/'cam_pitch_loop_geometry.py',HERE/'upper_curve_geometry.py',HERE/'curve_clearance.py',HERE/'upper_pack_geometry.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,mapping=mapping,
    curve_sha256=sha(OUT/'curves.npz') if arrays else None,main_changed=False,C6_main_applied=False,full_harness='BLOCKED',
    scope='Compound service loops joined to side-return CAM tails with nominal neck-length compensation. Four fixed-yaw fan connections remain absent.',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'loop_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('CAM_SIDE_SERVICE_DONE',r['status'],r['elapsed_s'],flush=True)
