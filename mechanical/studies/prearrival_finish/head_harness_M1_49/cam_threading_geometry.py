"""Side-effect-free, length-preserving assembly slack shapes at zero head pose."""
import math
import numpy as np
from upper_curve_geometry import shift,line

def clean(p):
    p=np.asarray(p);return p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-10]]

def parking(start,length,dy,radius=7.,step=.02):
    """Keep the first stem vertical; fan only the loose terminal end rearward."""
    start=np.asarray(start);s,Ls,err=shift(start,[start[0],start[1]+dy],radius,step)
    stem=length-Ls-10.;assert stem>0
    s=s+[0,0,stem]
    p=clean(np.vstack([line(start,s[0],step)[:-1],s,line(s[-1],s[-1]+[0,0,10.],step)[1:]]))
    return p,dict(exact_length_mm=length,curve_error_mm=err,terminal_tangent=[0.,0.,1.],minimum_radius_mm=radius)

def forming_u(start,length,alpha,tip_height=270.,radius=7.,step=.02):
    """Turn the free end through a half-circle while retaining total material.

    H is fixed. The tip height decreases monotonically to tip_height because
    dz_tip/dalpha=-(length-H-radius*alpha)*sin(alpha) <= 0 on [0,pi].
    Everything except the unchanged vertical stem stays above tip_height.
    """
    start=np.asarray(start);H=(length-math.pi*radius+tip_height-start[2])/2
    rest=length-H-radius*alpha;assert H>0 and rest>0 and 0<=alpha<=math.pi
    top=start+[0,0,H];n=max(1,math.ceil(radius*alpha/step));aa=np.linspace(0,alpha,n+1)
    arc=top+np.c_[np.zeros(len(aa)),radius*(1-np.cos(aa)),radius*np.sin(aa)]
    tangent=np.array([0.,math.sin(alpha),math.cos(alpha)])
    p=clean(np.vstack([line(start,top,step)[:-1],arc,line(arc[-1],arc[-1]+rest*tangent,step)[1:]]))
    err=radius*(1-math.cos(alpha/(2*n)))
    return p,dict(exact_length_mm=length,curve_error_mm=err,terminal_tangent=tangent.tolist(),
                  minimum_radius_mm=radius,up_stem_mm=H,free_tip_min_height_mm=tip_height,alpha_rad=alpha)

def service(start,length,anchor,radius=7.,step=.02):
    """U-return plus a 3D S approach to an explicitly placed free terminal."""
    start=np.asarray(start);anchor=np.asarray(anchor);lead=3.
    s,Ls,err=shift(anchor+[0,0,lead],[start[0],start[1]+2*radius],radius,step)
    topz=(length+start[2]+s[-1,2]-math.pi*radius-Ls-lead)/2
    assert topz>=max(start[2],s[-1,2])+.5
    top=np.array([start[0],start[1],topz]);aa=np.linspace(0,math.pi,math.ceil(math.pi*radius/step)+1)
    arc=top+np.c_[np.zeros(len(aa)),radius*(1-np.cos(aa)),radius*np.sin(aa)]
    p=clean(np.vstack([line(start,top,step)[:-1],arc[:-1],line(arc[-1],s[-1],step)[:-1],s[::-1][:-1],line(s[0],anchor,step)]))
    err=max(err,radius*(1-math.cos(math.pi/(2*(len(aa)-1)))))
    return p,dict(exact_length_mm=length,curve_error_mm=err,terminal_tangent=[0.,0.,-1.],
                  minimum_radius_mm=radius,topz_mm=topz,anchor_mm=anchor.tolist())
