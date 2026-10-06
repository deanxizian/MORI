"""Temporary full wire shape with a separated loose contact below the guide."""
import numpy as np
from upper_curve_geometry import shift,line
from cam_temporary_staging_geometry import service_with_lead
from cam_threading_geometry import clean

def with_lower_fan(start,length,guide_xy,terminal_xy,exit_z=221.,radius=7.,lead=5.,step=.02):
    entry=np.r_[guide_xy,exit_z]
    fan,L,error=shift(np.r_[guide_xy,0.],terminal_xy,radius,step)
    fan[:,2]=exit_z-fan[:,2]
    tail=np.vstack([fan,line(fan[-1],fan[-1]-[0,0,lead],step)[1:]])
    upper,meta=service_with_lead(start,length-L-lead,entry,lead=230.-exit_z,radius=radius,step=step)
    points=clean(np.vstack([upper,tail[1:]]))
    meta.update(exact_length_mm=length,guide_center_xy_mm=list(guide_xy),lower_fan_length_mm=L+lead,
        terminal_rear_mm=points[-1].tolist(),curve_error_mm=max(meta['curve_error_mm'],error))
    return points,meta
