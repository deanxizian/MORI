"""Pure replay of the rear_separated_neck 171/1.1 candidate centre lines.

No scene setup, file access or prior-study-prefix execution. This is not an
equal-length harness: the upper service loop still needs length compensation.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from route_family import profile

def smooth(z,start,end):
    u=np.clip((z-start)/(end-start),0.,1.)
    return 10*u**3-15*u**4+6*u**5

def build(row,original,slot,angles,turns,power4_dip=1.1):
    if slot not in turns:return np.asarray(original).copy()
    z=row['points'][:,2];t=(z-149.)/51.
    theta=poly.polyval(t,row['coefficients'])+math.radians(angles[slot])+math.radians(turns[slot])*smooth(z,171.,200.)
    r,_,_=profile(z,10.6,15.2,173.,30.,.6)
    if slot==4:r-=power4_dip*smooth(z,161.,177.)
    q=np.c_[r*np.cos(theta),r*np.sin(theta),z]
    if slot==5:
        a=math.radians(row['yaw_deg']);direction=np.array([-2*math.cos(a)+1.5*math.sin(a),-2*math.sin(a)-1.5*math.cos(a),0.])
        q+=smooth(z,187.,200.)[:,None]*direction
    j=int(np.searchsorted(original[:,2],149.))
    return np.vstack([original[:j],q])
