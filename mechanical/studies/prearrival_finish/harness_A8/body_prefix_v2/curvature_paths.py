"""Analytic planar tangent paths, CSC and CCC, for bounded route studies.

Points/heading vectors are 2D. Circles have a chosen true centreline radius;
joins are tangent, and returned chords have a declared sagitta bound.
"""
import math
import numpy as np

def left(v):return np.array([-v[1],v[0]])

def arc(c,a,b,sign,R,step=.12):
    aa=math.atan2(*(a-c)[::-1]);bb=math.atan2(*(b-c)[::-1])
    angle=(sign*(bb-aa))%(2*math.pi)
    if min(angle,2*math.pi-angle)<1e-9:angle=0.
    n=max(1,math.ceil(angle*R/step))
    theta=aa+sign*np.linspace(0,angle,n+1)
    points=c+R*np.column_stack([np.cos(theta),np.sin(theta)])
    assert np.linalg.norm(points[0]-a)<1e-7 and np.linalg.norm(points[-1]-b)<1e-7
    return points,R*angle,R*(1-math.cos(angle/n/2)),angle

def paths(p,h,q,k,R,step=.12):
    p=np.asarray(p,float);q=np.asarray(q,float);h=np.asarray(h,float);k=np.asarray(k,float)
    assert abs(np.linalg.norm(h)-1)<1e-8 and abs(np.linalg.norm(k)-1)<1e-8
    for s0 in [1,-1]:
        for s1 in [1,-1]:
            c0=p+s0*R*left(h);c1=q+s1*R*left(k)
            d=c1-c0;dist=np.linalg.norm(d);offset=(s1-s0)*R
            if dist<abs(offset)+1e-9:continue
            theta=math.atan2(d[1],d[0])-math.asin(offset/dist)
            t=np.array([math.cos(theta),math.sin(theta)])
            a=c0-s0*R*left(t);b=c1-s1*R*left(t)
            assert np.linalg.norm(left(t)@((b-a)))<1e-7 and (b-a)@t>0
            x,L0,e0,A0=arc(c0,p,a,s0,R,step);z,L1,e1,A1=arc(c1,b,q,s1,R,step)
            line=np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)/step)+1))
            yield {'family':('L' if s0==1 else 'R')+'S'+('L' if s1==1 else 'R'),
                'points_xy_mm':np.vstack([x,line[1:],z[1:]]),'radius_mm':R,
                'analytic_length_mm':L0+np.linalg.norm(b-a)+L1,'chord_error_mm':max(e0,e1),
                'circle_centres_mm':[c0.tolist(),c1.tolist()],'turn_signs':[s0,s1],
                'arc_angles_rad':[A0,A1],'tangent_points_mm':[a.tolist(),b.tolist()]}
        # Two possible middle circle centres, externally tangent at both ends.
        c0=p+s0*R*left(h);c1=q+s0*R*left(k);d=c1-c0;dist=np.linalg.norm(d)
        if dist<1e-9 or dist>=4*R:continue
        for side in [1,-1]:
            cm=(c0+c1)/2+side*left(d/dist)*math.sqrt(4*R*R-dist*dist/4)
            a=(c0+cm)/2;b=(c1+cm)/2
            x,L0,e0,A0=arc(c0,p,a,s0,R,step);y,Lm,em,Am=arc(cm,a,b,-s0,R,step);z,L1,e1,A1=arc(c1,b,q,s0,R,step)
            for c,u in [(c0,p),(cm,a),(c1,b)]:assert abs(np.linalg.norm(u-c)-R)<1e-7
            yield {'family':('LRL' if s0==1 else 'RLR')+str(side),
                'points_xy_mm':np.vstack([x,y[1:],z[1:]]),'radius_mm':R,
                'analytic_length_mm':L0+Lm+L1,'chord_error_mm':max(e0,em,e1),
                'circle_centres_mm':[c0.tolist(),cm.tolist(),c1.tolist()],'turn_signs':[s0,-s0,s0],
                'arc_angles_rad':[A0,Am,A1],'tangent_points_mm':[a.tolist(),b.tolist()]}
