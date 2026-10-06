# -*- coding: utf-8 -*-
"""Select mutually separated candidate wires, preserving endpoint/pin maps."""
from pathlib import Path
import json,hashlib,time
import numpy as np
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'ecowire_candidate.json'
data=json.loads(SOURCE.read_text());pools=data['candidate_pools']
def samples(curve,step=.4):
    p=np.array(curve);ds=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.r_[0,ds.cumsum()]
    s=np.linspace(0,cum[-1],int(np.ceil(cum[-1]/step))+1)
    return np.array([np.interp(s,cum,p[:,i]) for i in range(3)]).T
sampled={(key,i):samples(row['curve_mm']) for key,pool in pools.items() for i,row in enumerate(pool)}
cache={};checks=0
def compatible(ka,ia,kb,ib):
    k=tuple(sorted([(ka,ia),(kb,ib)]))
    if k not in cache:
        required=(pools[ka][ia]['wire_OD_max_mm']+pools[kb][ib]['wire_OD_max_mm'])/2+.32
        A=sampled[ka,ia];B=sampled[kb,ib]
        d=float(np.sqrt(np.min(np.sum((A[:,None,:]-B[None,:,:])**2,axis=2))))
        # Each true curve point has a sampled point <=0.2mm away; use the sum
        # to avoid accepting false gaps. Final exact segments are checked too.
        if d>=required+.4:cache[k]=True
        elif d<required:cache[k]=False
        else:cache[k]=exact_segment_min(pools[ka][ia]['curve_mm'],pools[kb][ib]['curve_mm'])[0]>=required
    return cache[k]
order=sorted(pools,key=lambda k:len(pools[k]));start=time.time()
def search(chosen):
    global checks
    if len(chosen)==len(order):return chosen
    key=order[len(chosen)]
    for i in range(len(pools[key])):
        checks+=1
        if checks>500000:return None
        if all(compatible(key,i,k,j) for k,j in chosen):
            result=search(chosen+[(key,i)])
            if result:return result
    return None
def exact_segment_min(A,B):
    A=np.array(A);B=np.array(B);u=np.diff(A,axis=0)[:,None,:];v=np.diff(B,axis=0)[None,:,:]
    p=A[:-1,None,:];q=A[1:,None,:];r=B[None,:-1,:];s=B[None,1:,:]
    def point_segment(x,y,z):
        vv=z-y;d=(vv*vv).sum(-1);tt=np.clip(((x-y)*vv).sum(-1)/np.maximum(d,1e-16),0,1)
        return np.linalg.norm(x-y-tt[:,:,None]*vv,axis=2)
    ds=np.minimum.reduce([point_segment(p,r,s),point_segment(q,r,s),point_segment(r,p,q),point_segment(s,p,q)])
    w=p-r;aa=(u*u).sum(-1);bb=(u*v).sum(-1);cc=(v*v).sum(-1);dd=(u*w).sum(-1);ee=(v*w).sum(-1)
    det=aa*cc-bb*bb;valid=det>1e-12
    tt=(bb*ee-cc*dd)/np.where(valid,det,1);zz=(aa*ee-bb*dd)/np.where(valid,det,1)
    good=valid&(tt>=0)&(tt<=1)&(zz>=0)&(zz<=1)
    mid=np.linalg.norm(w+tt[:,:,None]*u-zz[:,:,None]*v,axis=2)
    ds=np.minimum(ds,np.where(good,mid,np.inf))
    i,j=np.unravel_index(np.argmin(ds),ds.shape)
    return float(ds[i,j]),[int(i),int(j)]
selected=search([])
routes=[] if selected is None else [pools[k][i] for k,i in selected]
pairs=[]
for i,a in enumerate(routes):
    for b in routes[i+1:]:
        d,where=exact_segment_min(a['curve_mm'],b['curve_mm'])
        required=(a['wire_OD_max_mm']+b['wire_OD_max_mm'])/2+.32
        pairs.append(dict(a=a['id'],b=b['id'],minimum_polyline_center_distance_mm=d,
            wire_surface_gap_mm=d-(a['wire_OD_max_mm']+b['wire_OD_max_mm'])/2,
            required_center_distance_mm=required,segment_indices=where,status='PASS' if d>=required else 'FAIL'))
out=dict(status='PASS' if len(routes)==6 and all(p['status']=='PASS' for p in pairs) else 'BLOCKED',
    scope='Joint H01-H03 six-wire static candidate only; not complete harness qualification',
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_blend_sha256=data['source_blend_sha256'],
    routes=routes,pair_checks=pairs,search_combinations=checks,compatibility_pairs=len(cache),
    elapsed_s=time.time()-start,solid_sweep='NOT_TESTED',assembly_slack='NOT_TESTED',strain_relief='NOT_TESTED',
    hardware_selection='CANDIDATE_NOT_SELECTED',cut_lengths_released=False)
(HERE/'ecowire_joint.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(out['status'],checks,len(routes),len(cache),out['elapsed_s'])
