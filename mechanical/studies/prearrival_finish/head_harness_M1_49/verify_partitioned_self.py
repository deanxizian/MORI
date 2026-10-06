"""Check the faster exact self screen against the existing reference."""
from pathlib import Path
import hashlib,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sys.path.insert(0,str(HERE));import numpy as np
from curve_clearance import prepared,self_clear as reference
from curve_self_partition import self_clear
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text());started=time.time()
S=OUT/'cam_side_following';r=read(S/'loop_screen.json')
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert r['status']=='PASS' and sha(S/'curves.npz')==r['curve_sha256'];a=np.load(S/'curves.npz')
cases=[(f'actual_pin{p}_y{y}_p{t}',a[f'pin{p}_y{y}_p{t}']) for p in [1,4] for y,t in [(-60,-20),(0,0),(60,25)]]
tt=np.linspace(0,4*np.pi,3001)
for pitch in [.8,1.,1.3]:cases.append((f'fixture_helix_{pitch}',np.c_[np.cos(tt),np.sin(tt),tt*pitch/(2*np.pi)]))
for name,vertices in [('crossing',[[-10,-10,0],[10,10,0],[-10,10,0],[10,-10,0]]),('clear_U',[[0,0,0],[0,0,20],[0,10,20],[0,10,0]])]:
    p=np.vstack([np.linspace(a,b,501)[:-1] for a,b in zip(np.asarray(vertices[:-1]),np.asarray(vertices[1:]))]+[np.asarray(vertices[-1:])]);cases.append((name,p))
results=[]
for name,p in cases:
    item=prepared(p,.3302,.0003);t=time.time();old=reference(item);old_t=time.time()-t;t=time.time();new=self_clear(item);new_t=time.time()-t
    assert old['status']==new['status'],(name,old,new)
    results.append(dict(id=name,reference=old['status'],partitioned=new['status'],reference_seconds=old_t,partitioned_seconds=new_t,samples=len(p)))
    print('SELF_PARTITION',name,new['status'],old_t,new_t,flush=True)
inputs=[S/'loop_screen.json',S/'curves.npz',HERE/'curve_clearance.py',HERE/'curve_self_partition.py']
out=dict(status='PASS',sources=r['sources'],inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,
         scope='Algorithm equivalence checks on six actual curves and five labelled synthetic fixtures; not additional hardware qualification.',
         main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'self_partition_verification.json').write_text(json.dumps(out,indent=2)+'\n');print('SELF_PARTITION_DONE',len(results),out['elapsed_s'],flush=True)
