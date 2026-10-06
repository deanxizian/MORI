"""Circular lateral S bends with +Z tangents; no scene or file side effects."""
import math
import numpy as np
UP=np.array([0.,0.,1.])

def line(a,b,step=.025):
    return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)

def shift(start,xy,radius,step=.025):
    delta=np.r_[np.asarray(xy)-start[:2],0.];distance=float(np.linalg.norm(delta))
    if distance<1e-9:return np.array([start]),0.,0.
    axis=delta/distance
    angle=math.acos(1-distance/(2*radius)) if distance<2*radius else math.pi/2
    n=max(1,math.ceil(radius*angle/step));aa=np.linspace(0,angle,n+1)
    first=start+radius*(1-np.cos(aa))[:,None]*axis+radius*np.sin(aa)[:,None]*UP
    mid=line(first[-1],first[-1]+max(0.,distance-2*radius)*axis,step)
    aa=np.linspace(angle,0,n+1)
    last=mid[-1]+radius*(np.cos(aa)-math.cos(angle))[:,None]*axis+radius*(math.sin(angle)-np.sin(aa))[:,None]*UP
    return np.vstack([first,mid[1:],last[1:]]),2*radius*angle+max(0.,distance-2*radius),radius*(1-math.cos(angle/(2*n)))

def make(start,end,radius,lead=0.,waypoint=None,step=.025):
    start=np.asarray(start);end=np.asarray(end)
    p=line(start,start+lead*UP,step);length=lead;error=0.
    waypoints=([np.asarray(waypoint)] if waypoint is not None else [])+[end[:2]]
    for xy in waypoints:
        q,L,err=shift(p[-1],xy,radius,step);p=np.vstack([p,q[1:]])
        length+=L;error=max(error,err)
    if p[-1,2]>end[2]+1e-8:return None
    length+=end[2]-p[-1,2];q=line(p[-1],end,step)
    p=np.vstack([p,q[1:]])
    # Remove zero spans only; preserve every arc's original sampled vertices.
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-10]]
    assert np.linalg.norm(p[-1]-end)<1e-8
    return p,length,error
