"""Pure consecutive circular S bends with explicit planar waypoints."""
import numpy as np
from upper_curve_geometry import UP,line,shift

def make(start,end,radius,lead=0.,waypoints=(),step=.025):
    start=np.asarray(start);end=np.asarray(end)
    p=line(start,start+lead*UP,step);length=lead;error=0.
    for xy in list(waypoints)+[end[:2]]:
        q,L,err=shift(p[-1],xy,radius,step)
        p=np.vstack([p,q[1:]]);length+=L;error=max(error,err)
    if p[-1,2]>end[2]+1e-8:return None
    length+=end[2]-p[-1,2];p=np.vstack([p,line(p[-1],end,step)[1:]])
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-10]]
    assert np.linalg.norm(p[-1]-end)<1e-8
    return p,length,error
