"""Pure analytic root and neck-entry arcs; no scene/file side effects."""
import math
import numpy as np
from curvature_paths import paths
UP = np.array([0.,0.,1.])
def line(a,b,step=.03): return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
def rebuild(p, q, seed, z, step=.03):
    R = seed['minimum_centerline_radius_mm']; lead = seed['lead_mm']
    unit = lambda deg: np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg)),0.])
    eh,xh = unit(seed['entry_deg']),unit(seed['exit_deg'])
    tt = np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
    stem = line(p,p+lead*UP,step)
    entry = stem[-1]+R*(1-np.cos(tt))[:,None]*eh+R*np.sin(tt)[:,None]*UP
    q=np.asarray(q).copy(); q[2]=z
    bottom=q-R*xh-R*UP; drop=entry[-1,2]-bottom[2]
    if drop<=0:return None
    angle=math.acos(1-drop/(2*R)) if drop<2*R else math.pi/2
    aa=np.linspace(0,angle,math.ceil(R*angle/step)+1)
    c=bottom-2*R*math.sin(angle)*xh+drop*UP
    a=c+R*np.sin(aa)[:,None]*xh-R*(1-np.cos(aa))[:,None]*UP
    v=line(a[-1],a[-1]-max(0.,drop-2*R)*UP,step);back=aa[::-1]
    b=v[-1]+R*(math.sin(angle)-np.sin(back))[:,None]*xh-R*(np.cos(back)-math.cos(angle))[:,None]*UP
    last=bottom+R*np.sin(tt)[:,None]*xh+R*(1-np.cos(tt))[:,None]*UP
    plan=next((x for x in paths(entry[-1,:2],eh[:2],a[0,:2],xh[:2],seed['planar_radius_mm'],step) if x['family']==seed['family']),None)
    if plan is None:return None
    middle=np.c_[plan['points_xy_mm'],np.full(len(plan['points_xy_mm']),entry[-1,2])]
    return np.vstack([stem,entry[1:],middle[1:],a[1:],v[1:],b[1:],last[1:]])

