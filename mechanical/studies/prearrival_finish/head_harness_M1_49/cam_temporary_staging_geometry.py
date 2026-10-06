"""Length-preserving temporary service loop with a longer terminal-side stem.

Geometry only. Neither wire strain nor a supplier-approved radius is implied.
"""
import math
import numpy as np
from upper_curve_geometry import shift,line
from cam_threading_geometry import clean

def service_with_lead(start,length,anchor,lead=16.,radius=7.,step=.02):
    start=np.asarray(start);anchor=np.asarray(anchor)
    s,Ls,error=shift(anchor+[0,0,lead],[start[0],start[1]+2*radius],radius,step)
    topz=(length+start[2]+s[-1,2]-math.pi*radius-Ls-lead)/2
    assert topz>=max(start[2],s[-1,2])+.5
    top=np.array([start[0],start[1],topz]);aa=np.linspace(0,math.pi,math.ceil(math.pi*radius/step)+1)
    arc=top+np.c_[np.zeros(len(aa)),radius*(1-np.cos(aa)),radius*np.sin(aa)]
    p=clean(np.vstack([line(start,top,step)[:-1],arc[:-1],line(arc[-1],s[-1],step)[:-1],s[::-1][:-1],line(s[0],anchor,step)]))
    return p,dict(exact_length_mm=length,curve_error_mm=max(error,radius*(1-math.cos(math.pi/(2*(len(aa)-1))))),
        terminal_tangent=[0.,0.,-1.],minimum_radius_mm=radius,terminal_lead_mm=lead,topz_mm=topz)
