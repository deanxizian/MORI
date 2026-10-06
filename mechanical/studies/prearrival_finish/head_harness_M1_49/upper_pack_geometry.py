"""Polyline refinement and leading straight trimming without moving a curve."""
import math
import numpy as np

def refined(points,step=.01):
    points=np.asarray(points);segments=[]
    for a,b in zip(points,points[1:]):
        n=max(1,math.ceil(np.linalg.norm(b-a)/step))
        segments.append(np.linspace(a,b,n+1)[:-1])
    return np.vstack(segments+[points[-1:]])

def trimmed(points,length):
    if length==0:return points.copy()
    ds=np.linalg.norm(np.diff(points,axis=0),axis=1);s=np.r_[0.,np.cumsum(ds)]
    i=int(np.searchsorted(s,length));fraction=(length-s[i-1])/ds[i-1]
    q=points[i-1]+fraction*(points[i]-points[i-1])
    assert np.linalg.norm(q-(points[0]+[0.,0.,length]))<1e-7
    return np.vstack([q,points[i:]])
