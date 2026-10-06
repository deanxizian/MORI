"""Equal-length routes with a nominal outlet turn inside the unchanged neck.

The dip applies above the fixed bridge windows, where the inside of the
rotating neck follows a swept envelope. It changes wire paths only.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from neck_curve_geometry import S,B,G,W,absmax,radial,rotate

def profile(z,r0,r1,start,bend,dip):
    r,d,dd=radial(z,r0,r1,start,bend)
    for a,sign in [(149.,1.),(173.,-1.)]:
        u=np.clip((z-a)/8.,0.,1.);active=(z>a)&(z<a+8.)
        step=10*u**3-15*u**4+6*u**5
        first=np.where(active,(30*u**2-60*u**3+30*u**4)/8.,0.)
        second=np.where(active,(60*u-180*u**2+120*u**3)/64.,0.)
        r-=dip*sign*step;d-=dip*sign*first;dd-=dip*sign*second
    return r,d,dd

def family(z0=138.,z1=200.,r0=10.6,r1=15.2,flare_start=173.,flare_radius=30.,samples=1801,dip=.2,nominal_turn_deg=0.):
    H=z1-z0;half=math.sqrt(flare_radius*(r1-r0)-(r1-r0)**2/4)
    breaks=np.unique(np.r_[0.,1.,(np.array([149.,157.,173.,181.,flare_start,flare_start+half,flare_start+2*half])-z0)/H])
    assert np.all((breaks>=0)&(breaks<=1))
    qs=np.concatenate([a+(G+1)/2*(b-a) for a,b in zip(breaks,breaks[1:])])
    ws=np.concatenate([W/2*(b-a) for a,b in zip(breaks,breaks[1:])])
    qr,qd,_=profile(z0+H*qs,r0,r1,flare_start,flare_radius,dip)
    def length(co):
        td=poly.polyval(qs,poly.polyder(co))
        return float(np.sum(ws*np.sqrt(H*H+(H*qd)**2+(qr*td)**2)))
    target=max(length(math.radians(y+nominal_turn_deg)*S) for y in [-60,60])+.025
    t=np.unique(np.r_[np.linspace(0,1,samples),breaks]);dt=np.diff(t).max()
    r,d,dd=profile(z0+H*t,r0,r1,flare_start,flare_radius,dip);d*=H;dd*=H*H
    max_radial_slope=half/math.sqrt(flare_radius**2-half**2)+1.875*dip/8
    max_radial_dd=flare_radius**2/(flare_radius**2-half**2)**1.5+5.774*dip/64
    rows=[]
    for yaw in range(-60,61,10):
        alpha=math.radians(yaw+nominal_turn_deg);lo,hi=0.,3.
        assert length(alpha*S)<=target<=length(alpha*S+hi*B)
        for _ in range(52):
            mid=(lo+hi)/2
            if length(alpha*S+mid*B)<target:lo=mid
            else:hi=mid
        co=alpha*S+(lo+hi)/2*B
        th=poly.polyval(t,co);td=poly.polyval(t,poly.polyder(co));tdd=poly.polyval(t,poly.polyder(co,2))
        cs,sn=np.cos(th),np.sin(th);p=np.c_[r*cs,r*sn,z0+H*t]
        vel=np.c_[d*cs-r*sn*td,d*sn+r*cs*td,np.full(len(t),H)]
        acc=np.c_[(dd-r*td**2)*cs-(2*d*td+r*tdd)*sn,(dd-r*td**2)*sn+(2*d*td+r*tdd)*cs,np.zeros(len(t))]
        curvature=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3
        tdmax=absmax(poly.polyder(co));tddmax=absmax(poly.polyder(co,2))
        second=H*H*max_radial_dd+r1*tdmax**2+2*H*max_radial_slope*tdmax+r1*tddmax
        rows.append(dict(yaw_deg=yaw,points=p,coefficients=co.tolist(),length_mm=length(co),minimum_sampled_bend_mm=float(1/curvature.max()),chord_error_mm=float(second*dt**2/8)))
    return rows
