"""Pure offset of selected rear neck upper ends, with unchanged lower entry."""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from route_family import profile
from neck_curve_geometry import absmax
from rear_power_geometry import smooth

def build(row,original,slot,angles,turns,shift_y=1.,start_z=190.,end_z=204.):
    z=np.unique(np.r_[row['points'][:,2],np.linspace(200.,end_z,math.ceil((end_z-200.)/.007)+1),start_z])
    t=np.minimum((z-149.)/51.,1.);co=np.asarray(row['coefficients']);gamma=math.radians(turns[slot])
    w,wd,wdd=smooth(z,171.,200.)
    theta=poly.polyval(t,co)+math.radians(angles[slot])+gamma*w
    td=np.where(z<200.,poly.polyval(t,poly.polyder(co))/51.,0.)+gamma*wd
    tdd=np.where(z<200.,poly.polyval(t,poly.polyder(co,2))/51.**2,0.)+gamma*wdd
    r,rd,rdd=profile(z,10.6,15.2,173.,30.,.6);dip=1.1 if slot==4 else 0.
    dw,dwd,dwdd=smooth(z,161.,177.);r-=dip*dw;rd-=dip*dwd;rdd-=dip*dwdd
    c,s=np.cos(theta),np.sin(theta);p=np.c_[r*c,r*s,z]
    vel=np.c_[rd*c-r*s*td,rd*s+r*c*td,np.ones(len(z))]
    acc=np.c_[(rdd-r*td**2)*c-(2*rd*td+r*tdd)*s,(rdd-r*td**2)*s+(2*rd*td+r*tdd)*c,np.zeros(len(z))]
    yaw=math.radians(row['yaw_deg']);direction=np.array([-shift_y*math.sin(yaw),shift_y*math.cos(yaw),0.])
    w,wd,wdd=smooth(z,start_z,end_z);p+=w[:,None]*direction;vel+=wd[:,None]*direction;acc+=wdd[:,None]*direction
    curvature=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3
    half=math.sqrt(30.*4.6-4.6**2/4);maxrd=half/math.sqrt(30.**2-half**2)+1.875*.6/8+dip*1.875/16
    maxrdd=30.**2/(30.**2-half**2)**1.5+5.774*.6/64+dip*5.774/256
    maxthd=absmax(poly.polyder(co))/51.+abs(gamma)*1.875/29.;maxthdd=absmax(poly.polyder(co,2))/51.**2+abs(gamma)*5.774/29.**2
    bound=maxrdd+15.2*maxthd**2+2*maxrd*maxthd+15.2*maxthdd+abs(shift_y)*5.774/(end_z-start_z)**2
    j=np.searchsorted(original[:,2],149.);p=np.vstack([original[:j],p])
    return p,dict(minimum_sampled_bend_mm=float(1/curvature.max()),chord_error_mm=float(bound*np.diff(z).max()**2/8),
                  polygon_length_mm=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),end_mm=p[-1].tolist())
