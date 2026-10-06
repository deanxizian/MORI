"""Pure compound service loop: upper S/return arc plus a pitch-following tip."""
import math
import numpy as np
from cam_pitch_loop_geometry import line
from upper_curve_geometry import shift

def make(endpoint,transform,pitch,anchor_y=-11.,anchor_z=224.,lead=3.,top_radius=7.,lower_radius=7.5,
         terminal_straight=.5,target=None,step=.015):
    transform=np.asarray(transform);b=np.asarray(endpoint)@transform[:3,:3].T+transform[:3,3]
    angle=math.radians(pitch);s,c=math.sin(angle),math.cos(angle);sign=1. if pitch>=0 else -1.
    tangent=np.array([0.,s,-c]);d=b-terminal_straight*tangent
    lower_delta=np.array([0.,sign*lower_radius*(1-c),-lower_radius*abs(s)])
    lower_start=d-lower_delta;column=lower_start[1]
    a=np.array([b[0],anchor_y,anchor_z]);first=a+[0.,0.,lead]
    upper,s_length,s_error=shift(first,[b[0],column+2*top_radius],7.,step)
    base=lead+s_length+math.pi*top_radius+(upper[-1,2]-lower_start[2])+lower_radius*abs(angle)+terminal_straight
    hmin=max(.5,lower_start[2]+.5-upper[-1,2])
    if target is None:return base+2*hmin
    height=(target-base)/2.
    if height<hmin-1e-7:return None
    top=upper[-1]+[0.,0.,height]
    theta=np.linspace(0.,math.pi,max(1,math.ceil(math.pi*top_radius/step))+1)
    u=top+np.c_[np.zeros(len(theta)),top_radius*(np.cos(theta)-1),top_radius*np.sin(theta)]
    phi=np.linspace(0.,abs(angle),max(1,math.ceil(lower_radius*abs(angle)/step))+1)
    follow=lower_start+np.c_[np.zeros(len(phi)),sign*lower_radius*(1-np.cos(phi)),-lower_radius*np.sin(phi)]
    assert np.linalg.norm(follow[-1]-d)<1e-7
    points=np.vstack([line(a,first,step)[:-1],upper[:-1],line(upper[-1],top,step)[:-1],u[:-1],line(u[-1],lower_start,step)[:-1],follow[:-1],line(d,b,step)])
    points=points[np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-10]]
    error=max(s_error,top_radius*(1-math.cos(step/(2*top_radius))),lower_radius*(1-math.cos(step/(2*lower_radius))))
    return points,dict(pitch_deg=pitch,exact_length_mm=base+2*height,upper_lead_mm=height,
        return_straight_mm=top[2]-lower_start[2],top_radius_mm=top_radius,lower_radius_mm=lower_radius,
        maximum_z_mm=float(points[:,2].max()),curve_error_bound_mm=error,anchor_mm=a.tolist())
