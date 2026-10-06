"""Pure-geometry prefilter; no clearance or actual-cable qualification."""
from pathlib import Path
import numpy as np
import json, hashlib, math

HERE=Path(__file__).resolve().parent
OUT=HERE/'cam_fan_in/curvature_prefilter_v4'; OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
starts=np.load(HERE/'cam_pitch_port/lower_staging/body_partial_curves.npz')
up=np.array([0.,0.,1.])
ends=np.array(json.loads((HERE/'cam_fan_in/short_tail_v2/screen.json').read_text())['selected'][0]['anchor_slots_mm'])
rng=np.random.default_rng(202610042)
t=np.linspace(0,1,129)
b2=np.array([(1-t)**2,2*t*(1-t),t*t]).T
b1=np.array([1-t,t]).T
rows=[]
for pin in range(1,5):
    a=starts[f'pin{pin}_yaw0'][-1]; b=ends[pin-1]; accepted=[]; total=0
    for batch in range(10):
        n=2000; total+=n
        if pin==1:
            low=[-9.70,-16.,210., -.015,.03,1., 5.,4.,5.,5.]
            high=[-9.64,-14.5,215., .015,.25,1., 8.,7.,9.,10.]
        elif pin==2:
            low=[-11.0,10.8,210., .10,-.65,1., 5.,5.,5.,7.]
            high=[-10.75,12.3,214., .30,-.25,1., 8.,8.,9.,11.]
        elif pin==3:
            low=[-4.,-18.,206., -.9,.1,1., 9.,5.,5.,9.]
            high=[2.,-13.,216., -.5,.5,1., 14.,9.,10.,15.]
        else:
            low=[-5.,23.,204., -1.,-.35,.25, 8.,5.,5.,10.]
            high=[0.,29.,216., -.5,.1,.75, 14.,10.,12.,16.]
        vals=rng.uniform(low,high,(n,10));mid=vals[:,:3];tan=vals[:,3:6]
        tan=tan/np.linalg.norm(tan,axis=1)[:,None];h=vals[:,6:]
        cs=np.stack([np.stack([np.broadcast_to(a,(n,3)),a+h[:,0,None]*up,mid-h[:,1,None]*tan,mid],axis=1),
                     np.stack([mid,mid+h[:,2,None]*tan,b-h[:,3,None]*up,np.broadcast_to(b,(n,3))],axis=1)],axis=1)
        v=np.einsum('tk,nskd->nstd',b2,3*np.diff(cs,axis=2))
        acc=np.einsum('tk,nskd->nstd',b1,6*np.diff(cs,n=2,axis=2))
        speed=np.linalg.norm(v,axis=-1);cross=np.linalg.norm(np.cross(v,acc),axis=-1)
        rad=np.divide(speed**3,cross,out=np.full_like(speed,np.inf),where=cross>1e-12)
        mins=rad.min(axis=(1,2));mins[speed.min(axis=(1,2))<1e-6]=0.
        for i in np.flatnonzero(mins>=7.1):
            accepted.append({'mid':mid[i].tolist(),'tangent':tan[i].tolist(),'handles':h[i].tolist(),
                'sampled_radius_mm':float(mins[i]),'batch':batch,'row':int(i)})
    # Keep a deterministic spread, rather than selecting only nearly identical
    # maximum-radius shapes. Full-source checks are performed in Blender.
    keep=accepted[::max(1,len(accepted)//300)][:300]
    rows.append({'pin':pin,'trial_count':total,'curvature_accepted_count':len(accepted),'candidates':keep})
    print(pin,total,len(accepted),len(keep),flush=True)
result={'script_sha256':sha(Path(__file__)),'source_body_sha256':sha(HERE/'cam_pitch_port/lower_staging/body_partial_curves.npz'),
    'source_anchor_sha256':sha(HERE/'cam_fan_in/short_tail_v2/screen.json'),'rows':rows,
    'scope':'Sampled curvature rejection only; no solid clearance or full-interval radius proof','main_applied':False}
(OUT/'parameters.json').write_text(json.dumps(result,indent=2)+'\n')
