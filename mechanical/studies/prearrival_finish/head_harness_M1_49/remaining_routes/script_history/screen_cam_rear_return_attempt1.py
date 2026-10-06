"""Screen reversed CAM tails to avoid the proven neck/tail crossings.

Only candidate curves change. Original connector points and the first 5 mm
approach are preserved. Complete transitions, anchors and delivery remain open.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/rear_power_bump';OUT=HERE/'remaining_routes/cam_rear_return';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from cam_rear_return_geometry import tail,loop
from curve_clearance import prepared,pair,self_clear
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());nr=read(N/'neck_screen.json')
for f,h in {**nr['sources'],**nr['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(N/'curves.npz')==nr['curve_sha256']
A=HERE.parent/'harness_A8/cam_fan_in/short_tail_v2';old=read(A/'screen.json')
assert sha(A/'tails.npz')==old['tail_curves_sha256'];oldtails=np.load(A/'tails.npz');nc=np.load(N/'curves.npz')
mapping={1:9,2:8,3:7,4:10};poses=range(-20,26,5);yaws=range(-60,61,10)
tails={p:tail(oldtails[f'slot{p-1}'][0])[0] for p in mapping}
lengths={p:{y:float(np.linalg.norm(np.diff(nc[f'wire{s}_y{y}'],axis=0),axis=1).sum()) for y in yaws} for p,s in mapping.items()}
maxlen={p:max(ls.values()) for p,ls in lengths.items()}
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
lower={};results=[];arrays={}
for yaw,s in itertools.product(yaws,range(11)):
    tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=nc[f'wire{s}_y{yaw}'];p=p@tr[:3,:3].T+tr[:3,3]
    lower[yaw,s]=prepared(refined(p,.01),nr['OD_mm'][s]/2,.0003)
for anchor_y,anchor_z in [(-12.,220.),(-14.,220.),(-16.,220.)]:
    base=[loop(tails[1][-1],np.asarray(rigidtr(0,p)),p,anchor_y,anchor_z) for p in poses]
    assert all(b is not None for b in base);target0=max(base)+.02
    curves={};metadata=[];hits=[];checks=0
    for pin,yaw,pitch in itertools.product(mapping,yaws,poses):
        pt=np.asarray(rigidtr(0,pitch));yt=np.asarray(rigidtr(yaw,0));target=target0+maxlen[pin]-lengths[pin][yaw]
        core,m=loop(tails[pin][-1],pt,pitch,anchor_y,anchor_z,target)
        end=tails[pin][::-1]@pt[:3,:3].T+pt[:3,3];assert np.linalg.norm(core[-1]-end[0])<1e-5
        p=np.vstack([core,end[1:]]);curves[pin,yaw,pitch]=p
        metadata.append(dict(pin=pin,yaw=yaw,compensation_mm=maxlen[pin]-lengths[pin][yaw],**m))
        for group,tg in targets.items():
            ctx.targets=tg;tr=yt if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(pt)
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=.0003);checks+=1
            if hit:hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,group=group,**hit));break
        if hits:break
    self_rows=[];pairs=[];lower_hits=[]
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
    r=dict(status='PASS' if ok else 'BLOCKED',anchor_y_mm=anchor_y,anchor_z_mm=anchor_z,base_core_length_mm=target0,
           metadata=metadata,hits=hits,native_checks=checks,lower_conflicts=lower_hits,pairs=pairs,self_checks=self_rows)
    results.append(r);print('CAM_REAR_RETURN',anchor_y,r['status'],hits[:1],len(lower_hits),flush=True)
    if ok:
        arrays={f'pin{pin}_y{y}_p{pt}':p for (pin,y,pt),p in curves.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'curves.npz',**arrays)
np.savez_compressed(OUT/'tails.npz',**{f'pin{p}':t for p,t in tails.items()})
inputs=[N/'neck_screen.json',N/'curves.npz',A/'screen.json',A/'tails.npz',HERE/'cam_rear_return_geometry.py',HERE/'cam_pitch_loop_geometry.py',HERE/'curve_clearance.py',HERE/'upper_pack_geometry.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
       curve_sha256=sha(OUT/'curves.npz') if arrays else None,tail_sha256=sha(OUT/'tails.npz'),mapping=mapping,
       preserved_connector_approach_mm=5.,tail_radius_mm=7.5,main_changed=False,C6_main_applied=False,full_harness='BLOCKED',
       scope='Rear-return tail and compensated loop candidates; original port coordinates retained, only candidate paths change. Complete joining and anchoring remain open.',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'loop_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('CAM_REAR_RETURN_DONE',r['status'],r['elapsed_s'],flush=True)
