"""Pure candidate: preserve the CAM lead, bend rearward, then return upward."""
import math
import numpy as np
from cam_pitch_loop_geometry import make as following, line

def tail(start,radius=7.5,lead=5.,step=.015):
    start=np.asarray(start);a=start+[0.,0.,-lead]
    angles=np.linspace(0.,math.pi/2,max(1,math.ceil(math.pi*radius/2/step))+1)
    arc=a+np.c_[np.zeros(len(angles)),-radius*(1-np.cos(angles)),-radius*np.sin(angles)]
    points=np.vstack([line(start,a,step)[:-1],arc])
    return points,lead+math.pi*radius/2,radius*(1-math.cos(step/(2*radius)))

def loop(tail_endpoint,transform,pitch,anchor_y,anchor_z,target=None):
    transform=np.asarray(transform);b=np.asarray(tail_endpoint)@transform[:3,:3].T+transform[:3,3]
    mirrored=b*np.array([1.,-1.,1.])
    result=following(mirrored,np.eye(4),-pitch,-anchor_y,anchor_z,target=target,step=.015)
    if result is None or target is None:return result
    points,meta=result;points=points*np.array([1.,-1.,1.])
    meta['pitch_deg']=pitch;meta['column_y_mm']*=-1
    return points,meta
