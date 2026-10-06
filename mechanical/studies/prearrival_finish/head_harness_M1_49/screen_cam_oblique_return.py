"""Tilt the side-return bundle rearward while preserving concentric projected arcs."""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/rear_power_bump';OUT=HERE/'remaining_routes/cam_oblique_return';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from cam_pitch_loop_geometry import line
from curve_clearance import prepared,pair,self_clear
from upper_pack_geometry import refined
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text());nr=read(N/'neck_screen.json')
for f,h in {**nr['sources'],**nr['inputs']}.items():assert sha(ROOT/f)==h,f
assert nr['status']=='PASS' and sha(N/'curves.npz')==nr['curve_sha256']
A=HERE.parent/'harness_A8/cam_fan_in/short_tail_v2';old=read(A/'screen.json');assert sha(A/'tails.npz')==old['tail_curves_sha256']
oldtails=np.load(A/'tails.npz');nc=np.load(N/'curves.npz');mapping={1:9,2:8,3:7,4:10};poses=range(-20,26,5);yaws=range(-60,61,10)
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']};results=[];arrays={};lower={}
for yaw,s in itertools.product(yaws,range(11)):
    tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=nc[f'wire{s}_y{yaw}'];lower[yaw,s]=prepared(refined(p@tr[:3,:3].T+tr[:3,3],.01),nr['OD_mm'][s]/2,.0003)
for angle_deg,base_radius in [(15.,7.5),(25.,7.5),(8.,7.5)]:
    angle=math.radians(angle_deg);direction=-1.;c,sn=math.cos(angle),math.sin(angle)
    tails={};metadata=[];hits=[];checks=0;curves={}
    for pin in mapping:
        start=oldtails[f'slot{pin-1}'][0];r=base_radius+(pin-1)*c
        a=start+[0.,0.,-5.];angles=np.linspace(0.,math.pi,math.ceil(math.pi*r/.01)+1)
        arc=a+np.c_[-c*r*(1-np.cos(angles)),-sn*r*(1-np.cos(angles)),-r*np.sin(angles)]
        tails[pin]=np.vstack([line(start,a,.01)[:-1],arc]);metadata.append(dict(pin=pin,radius_mm=r,start_mm=start.tolist(),end_mm=tails[pin][-1].tolist(),exact_length_mm=5+math.pi*r))
    for pin,yaw,pitch in itertools.product(mapping,yaws,poses):
        pt=np.asarray(rigidtr(0,pitch));yt=np.asarray(rigidtr(yaw,0));p=tails[pin]@pt[:3,:3].T+pt[:3,3];curves[pin,yaw,pitch]=p
        for group,tg in targets.items():
            ctx.targets=tg;tr=yt if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(pt)
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=.0003);checks+=1
            if hit:hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,group=group,**hit));break
        if hits:break
    pairs=[];self_rows=[];lower_hits=[]
    if not hits:
        items={key:prepared(p,.3302,.0003) for key,p in curves.items()}
        for (pin,yaw,pitch),item in items.items():
            self_rows.append(dict(pin=pin,yaw=yaw,pitch=pitch,**self_clear(item)))
            for s in range(11):
                r=pair_threshold(item,lower[yaw,s])
                if r['status']!='PASS':lower_hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,slot=s,**r))
        for yaw,pitch in itertools.product(yaws,poses):
            for a,b in itertools.combinations(mapping,2):pairs.append(dict(yaw=yaw,pitch=pitch,a=a,b=b,**pair(items[a,yaw,pitch],items[b,yaw,pitch])))
        assert checks==1560 and len(self_rows)==520 and len(pairs)==780
    ok=not hits and not lower_hits and bool(pairs) and all(x['status']=='PASS' for x in pairs+self_rows)
    row=dict(status='PASS' if ok else 'BLOCKED',angle_deg=angle_deg,base_radius_mm=base_radius,metadata=metadata,hits=hits,native_checks=checks,pairs=pairs,lower_conflicts=lower_hits,self_checks=self_rows)
    results.append(row);print('CAM_OBLIQUE_RETURN',angle_deg,base_radius,row['status'],hits[:1],len(lower_hits),flush=True)
    if ok:
        arrays={f'pin{p}':t for p,t in tails.items()};break
ctx.targets=native;ctx.assert_unchanged()
if arrays:np.savez_compressed(OUT/'tails.npz',**arrays)
inputs=[N/'neck_screen.json',N/'curves.npz',A/'screen.json',A/'tails.npz',HERE/'cam_pitch_loop_geometry.py',HERE/'curve_clearance.py',HERE/'upper_pack_geometry.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if arrays else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
       curve_sha256=sha(OUT/'tails.npz') if arrays else None,mapping=mapping,preserved_connector_approach_mm=5.,main_changed=False,C6_main_applied=False,
       full_harness='BLOCKED',scope='Only four moving oblique side-return tails; projected circles have concentric centres, and radii differ by cos(angle) while plane spacing is sin(angle). Native ports and five-millimetre straight leads retained. Loop and neck connections are absent.',
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'tail_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('CAM_OBLIQUE_RETURN_DONE',r['status'],r['elapsed_s'],flush=True)
