"""Pure circular, constant-length pitch loop geometry in one X plane.

The equations preserve the previous following-arc construction, without
executing any historical study's setup, source substitution or file writes.
Positive endpoint tangent is -Y rotated with the moving pitch assembly.
"""
import math
import numpy as np

def line(a,b,step=.02):
    return np.linspace(a,b,max(1,math.ceil(float(np.linalg.norm(b-a))/step))+1)

def make(tail_endpoint,transform,pitch,anchor_y,anchor_z,lower_radius=7.5,
         terminal_straight=.5,target=None,minimum_radius=6.9342,step=.02):
    angle=math.radians(pitch);mat=np.asarray(transform)
    b=np.asarray(tail_endpoint)@mat[:3,:3].T+mat[:3,3];x=b[0]
    column=b[1]+terminal_straight*math.cos(angle)+lower_radius*(1-math.sin(angle))
    rt=(column-anchor_y)/2
    if rt<minimum_radius+.1 or lower_radius<minimum_radius:return None
    zturn=b[2]+terminal_straight*math.sin(angle)+lower_radius*math.cos(angle)
    base=math.pi*rt+(anchor_z-zturn)+lower_radius*(math.pi/2-angle)+terminal_straight
    if target is None:return base+2*max(5.,zturn-anchor_z+.5)
    height=(target-base)/2
    if height<5.-1e-6 or anchor_z+height<zturn+.49999:return None
    a=np.array([x,anchor_y,anchor_z]);top=a+[0,0,height];endtop=np.array([x,column,anchor_z+height])
    aa=np.linspace(math.pi,0,max(1,math.ceil(math.pi*rt/step))+1)
    upper=np.c_[np.full_like(aa,x),anchor_y+rt+rt*np.cos(aa),anchor_z+height+rt*np.sin(aa)]
    aa=np.linspace(0.,-math.pi/2+angle,max(1,math.ceil(lower_radius*(math.pi/2-angle)/step))+1)
    lower=np.c_[np.full_like(aa,x),column-lower_radius+lower_radius*np.cos(aa),zturn+lower_radius*np.sin(aa)]
    points=np.vstack([line(a,top,step)[:-1],upper[:-1],line(endtop,lower[0],step)[:-1],lower[:-1],line(lower[-1],b,step)])
    error=max(rt,lower_radius)*(1-math.cos(step/(2*min(rt,lower_radius))))
    return points,dict(pitch_deg=pitch,column_y_mm=column,upper_arc_lift_mm=height,
        top_radius_mm=rt,lower_radius_mm=lower_radius,bottom_straight_mm=terminal_straight,
        vertical_span_mm=anchor_z+height-zturn,exact_length_mm=base+2*height,curve_error_bound_mm=error)

def trim_tail(tail,end_y):
    tail=np.asarray(tail);last=tail[-1];assert end_y<=last[1]
    i=len(tail)-1
    while i>0 and np.linalg.norm(tail[i-1,[0,2]]-last[[0,2]])<1e-7:i-=1
    assert tail[i,1]<=end_y,'Only the existing final +Y straight may be shortened'
    return np.vstack([tail[tail[:,1]<end_y],np.array([last[0],end_y,last[2]])])
