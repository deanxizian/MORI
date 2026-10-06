"""Pure slot-5 route alternatives above an unchanged neck entry.

The optional late translation can finish above the old Z200 end. This file
only describes candidate centre lines; it is not a constant-length wire model.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from route_family import profile
from neck_curve_geometry import absmax

def smooth(z, start, end):
    u=np.clip((z-start)/(end-start),0.,1.);a=(z>start)&(z<end);h=end-start
    return (10*u**3-15*u**4+6*u**5,
            np.where(a,(30*u**2-60*u**3+30*u**4)/h,0.),
            np.where(a,(60*u-180*u**2+120*u**3)/h**2,0.))

def build(row, original, angle, *, turn=82., dip=0., dip_start=183., dip_end=198.,
          offset=(0.,0.), offset_start=193., offset_end=206., end_z=206., mid_bump_deg=0.):
    z0=row['points'][:,2]
    extension=np.linspace(200.,end_z,max(2,int(math.ceil((end_z-200.)/.007))+1))[1:] if end_z>200. else []
    z=np.unique(np.r_[z0,extension,dip_start,dip_end,offset_start,offset_end]);z=z[(z>=149.)&(z<=end_z)]
    t=np.minimum((z-149.)/51.,1.);co=np.asarray(row['coefficients']);w,wd,wdd=smooth(z,171.,200.)
    gamma=math.radians(turn);theta=poly.polyval(t,co)+math.radians(angle)+gamma*w
    td=np.where(z<200.,poly.polyval(t,poly.polyder(co))/51.,0.)+gamma*wd
    tdd=np.where(z<200.,poly.polyval(t,poly.polyder(co,2))/51.**2,0.)+gamma*wdd
    # A smooth, local angular separation tapers to zero before the upper outlet.
    bw,bwd,bwdd=smooth(z,177.,185.);cw,cwd,cwdd=smooth(z,185.,193.)
    bg=math.radians(mid_bump_deg)
    theta+=bg*(bw-cw);td+=bg*(bwd-cwd);tdd+=bg*(bwdd-cwdd)
    r,rd,rdd=profile(z,10.6,15.2,173.,30.,.6);dw,dwd,dwdd=smooth(z,dip_start,dip_end)
    r-=dip*dw;rd-=dip*dwd;rdd-=dip*dwdd;cs,sn=np.cos(theta),np.sin(theta)
    q=np.c_[r*cs,r*sn,z]
    vel=np.c_[rd*cs-r*sn*td,rd*sn+r*cs*td,np.ones(len(z))]
    acc=np.c_[(rdd-r*td**2)*cs-(2*rd*td+r*tdd)*sn,(rdd-r*td**2)*sn+(2*rd*td+r*tdd)*cs,np.zeros(len(z))]
    yaw=math.radians(row['yaw_deg']);dx,dy=offset
    direction=np.array([dx*math.cos(yaw)-dy*math.sin(yaw),dx*math.sin(yaw)+dy*math.cos(yaw),0.])
    ow,owd,owdd=smooth(z,offset_start,offset_end)
    q+=ow[:,None]*direction;vel+=owd[:,None]*direction;acc+=owdd[:,None]*direction
    curvature=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3
    half=math.sqrt(30.*4.6-4.6**2/4);dh=dip_end-dip_start
    maxrd=half/math.sqrt(30.**2-half**2)+1.875*.6/8+abs(dip)*1.875/dh
    maxrdd=30.**2/(30.**2-half**2)**1.5+5.774*.6/64+abs(dip)*5.774/dh**2
    maxthd=absmax(poly.polyder(co))/51.+abs(gamma)*1.875/29.+abs(bg)*1.875/8.
    maxthdd=absmax(poly.polyder(co,2))/51.**2+abs(gamma)*5.774/29.**2+abs(bg)*5.774/64.
    bound=maxrdd+15.2*maxthd**2+2*maxrd*maxthd+15.2*maxthdd+np.linalg.norm(direction)*5.774/(offset_end-offset_start)**2
    error=float(bound*np.diff(z).max()**2/8.)
    j=int(np.searchsorted(original[:,2],149.));p=np.vstack([original[:j],q])
    return p,dict(minimum_sampled_bend_mm=float(1./curvature.max()),chord_error_mm=error,
                  polygon_length_mm=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),end_mm=p[-1].tolist())
