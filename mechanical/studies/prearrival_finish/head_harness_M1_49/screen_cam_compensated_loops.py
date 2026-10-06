"""Use upper pitch-loop length to compensate the new rear neck candidates.

This tests actual matching yaw/pitch pairs, not unrelated pose pairs. The
fixed transition between neck end and loop start is not yet present.
"""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
N=HERE/'remaining_routes/rear_power_bump';L=HERE/'remaining_routes/cam_rearward_loops'
OUT=HERE/'remaining_routes/cam_compensated_loops';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from cam_pitch_loop_geometry import make,trim_tail
from curve_clearance import prepared,pair,self_clear
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
nr=read(N/'neck_screen.json');lr=read(L/'loop_screen.json');refined=read(L/'refined_pairs.json')
for report in [nr,lr,refined]:
    for f,h in {**report['sources'],**report['inputs']}.items():
        root=ROOT if f.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE
        assert sha(root/f)==h,f
assert nr['status']=='PASS' and sha(N/'curves.npz')==nr['curve_sha256']
assert refined['status']=='PASS'
nc=np.load(N/'curves.npz');case=next(r for r in lr['results'] if r['id']=='rear3')
A=HERE.parent/'harness_A8/cam_fan_in/short_tail_v2';old=read(A/'screen.json')
assert sha(A/'tails.npz')==old['tail_curves_sha256'];oldtails=np.load(A/'tails.npz')
mapping={1:9,2:8,3:7,4:10};poses=range(-20,26,5);yaws=range(-60,61,10)
tails={pin:trim_tail(oldtails[f'slot{pin-1}'],case['tail_end_y_mm']) for pin in mapping}
lengths={pin:{y:float(np.linalg.norm(np.diff(nc[f'wire{slot}_y{y}'],axis=0),axis=1).sum()) for y in yaws} for pin,slot in mapping.items()}
maxlen={pin:max(ls.values()) for pin,ls in lengths.items()}
native=ctx.targets;groups={name:s.group if s.group in ['yaw','pitch'] else 'body' for name,s in ctx.ss.items()}
targets={g:{name:t for name,t in native.items() if groups.get(name,'body')==g} for g in ['body','yaw','pitch']}
other_error=.0003;lower={};arrays={};metadata=[];hits=[];checks=0
for yaw,slot in itertools.product(yaws,range(11)):
    tr=np.linalg.inv(np.asarray(rigidtr(yaw,0)));p=nc[f'wire{slot}_y{yaw}']
    lower[yaw,slot]=prepared(p@tr[:3,:3].T+tr[:3,3],nr['OD_mm'][slot]/2,other_error)
curves={}
for pin,yaw,pitch in itertools.product(mapping,yaws,poses):
    pt=np.asarray(rigidtr(0,pitch));yt=np.asarray(rigidtr(yaw,0))
    target=case['exact_core_length_mm']+maxlen[pin]-lengths[pin][yaw]
    result=make(tails[pin][-1],pt,pitch,case['anchor_y_mm'],case['anchor_z_mm'],target=target)
    assert result is not None,(pin,yaw,pitch,target)
    core,m=result;tail=tails[pin][::-1]@pt[:3,:3].T+pt[:3,3];assert np.linalg.norm(core[-1]-tail[0])<1e-5
    p=np.vstack([core,tail[1:]]);curves[pin,yaw,pitch]=p;arrays[f'pin{pin}_y{yaw}_p{pitch}']=p
    metadata.append(dict(pin=pin,yaw=yaw,neck_polygon_length_mm=lengths[pin][yaw],compensation_mm=maxlen[pin]-lengths[pin][yaw],
                         neck_plus_core_length_mm=lengths[pin][yaw]+m['exact_length_mm'],**m))
    for group,t in targets.items():
        ctx.targets=t;tr=yt if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(pt)
        hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=.0003);checks+=1
        if hit:hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,group=group,**hit))
    if pitch==25:print('COMPENSATED_NATIVE',pin,yaw,len(hits),flush=True)
self_rows=[];pairs=[];lower_hits=[]
items={key:prepared(p,.3302,.0003) for key,p in curves.items()}
for (pin,yaw,pitch),item in items.items():
    self_rows.append(dict(pin=pin,yaw=yaw,pitch=pitch,**self_clear(item)))
    for slot in range(11):
        r=pair_threshold(item,lower[yaw,slot])
        if r['status']!='PASS':lower_hits.append(dict(pin=pin,yaw=yaw,pitch=pitch,slot=slot,**r))
for yaw,pitch in itertools.product(yaws,poses):
    for a,b in itertools.combinations(mapping,2):pairs.append(dict(yaw=yaw,pitch=pitch,a=a,b=b,**pair(items[a,yaw,pitch],items[b,yaw,pitch])))
variation={pin:max(m['neck_plus_core_length_mm'] for m in metadata if m['pin']==pin)-min(m['neck_plus_core_length_mm'] for m in metadata if m['pin']==pin) for pin in mapping}
assert max(variation.values())<1e-8 and checks==1560 and len(pairs)==780 and len(self_rows)==520
ok=not hits and not lower_hits and all(r['status']=='PASS' for r in self_rows+pairs)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'curves.npz',**arrays)
inputs=[N/'neck_screen.json',N/'curves.npz',L/'loop_screen.json',L/'refined_pairs.json',A/'screen.json',A/'tails.npz',HERE/'cam_pitch_loop_geometry.py',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
r=dict(status='PASS' if ok else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
       mapping=mapping,loop_case='rear3',native_checks=checks,hits=hits,pairs=pairs,self_checks=self_rows,lower_conflicts=lower_hits,metadata=metadata,
       neck_plus_loop_length_variation_mm=variation,curve_sha256=sha(OUT/'curves.npz'),main_changed=False,C6_main_applied=False,
       scope='Compensated CAM upper loops versus the eleven local neck paths. Fixed connecting fans, anchoring and full endpoint routes are not included.',
       length_evidence='Analytic upper-loop length compensates sampled neck polygon length; verify full joined curve lengths before supplier drawings.',
       full_harness='BLOCKED',wired_assembly='NOT_TESTED',anchors='NOT_TESTED',supplier_cut_lengths_released=False,
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'loop_screen.json').write_text(json.dumps(r,indent=2)+'\n');print('COMPENSATED_LOOPS_DONE',r['status'],len(hits),len(lower_hits),r['elapsed_s'],flush=True)
