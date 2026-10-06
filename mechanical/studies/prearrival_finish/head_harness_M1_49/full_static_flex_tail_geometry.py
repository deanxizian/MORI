"""Alternative free-span framing: change width orientation on a longer end run."""
import math
import numpy as np
from full_static_flex_geometry import rotation,log_rotation,trace,ribbon

def solve_tail(start,end,radius=7.5,total_length=194.,lead=8.8,tail=12.5,middle_seed=20.):
    targetT=np.array([1.,0,0]);targetW=rotation([1,0,0],math.radians(10))@np.array([0.,0,1.])
    targetR=np.column_stack([targetT,targetW,np.cross(targetT,targetW)])
    def unpack(v):return [lead,*v[:5],tail],[0,0,v[5],0,v[6],0,v[7]]
    def residual(v):
        lengths,twists=unpack(v);r=trace(start,lengths,twists,radius)
        R=np.column_stack([r['T'],r['W'],np.cross(r['T'],r['W'])])
        return np.r_[r['end']-end,log_rotation(targetR.T@R)*30.,r['length']-total_length]
    remaining=total_length-3*math.pi*radius-lead-tail
    seed=np.array([2.,(remaining-middle_seed-4)/2,middle_seed,
        (remaining-middle_seed-4)/2,2.,math.radians(-12),math.radians(-7),math.radians(15)])
    lo=np.array([.25]*5+[-math.pi/2]*3);hi=np.array([85.]*5+[math.pi/2]*3)
    q=np.clip(seed,lo,hi);history=[]
    for iteration in range(100):
        r=residual(q);cost=float(r@r);history.append(cost)
        if np.linalg.norm(r)<2e-7:break
        J=np.column_stack([(residual(q+np.eye(8)[i]*1e-5)-residual(q-np.eye(8)[i]*1e-5))/2e-5 for i in range(8)])
        update=np.linalg.lstsq(J,-r,rcond=1e-10)[0];found=False
        for scale in [1.,.5,.25,.125,.0625,.03125,.015625]:
            new=np.clip(q+scale*update,lo,hi);nr=residual(new)
            if nr@nr<cost:q=new;found=True;break
        if not found:break
    lengths,twists=unpack(q);r=trace(start,lengths,twists,radius)
    return dict(status='PASS' if np.linalg.norm(residual(q))<1e-5 else 'FAIL',
        lengths=lengths,twists=twists,radius=radius,start=np.asarray(start),end=np.asarray(end),
        residual=residual(q),iterations=len(history),fit_history=history,
        endpoint_error_mm=float(np.linalg.norm(r['end']-end)),length_mm=r['length'],
        target_width_vector=targetW)
