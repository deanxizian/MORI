"""Pure local constant-length curve family, with a documented radial flare.

This is geometry for screening only. It is not a material/fatigue simulation.
The flare consists of two equal circular arcs tangent to vertical straight
portions. No saved scene or prior study initializer is imported.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
S=np.array([0.,0.,0.,10.,-15.,6.])
B=np.array([0.,0.,16.,-32.,16.,0.])
G,W=np.polynomial.legendre.leggauss(96)

def absmax(c):
    roots=poly.polyroots(poly.polyder(c))
    ts=[0.,1.]+[float(v.real) for v in roots if abs(v.imag)<1e-8 and 0<v.real<1]
    return float(np.max(np.abs(poly.polyval(ts,c))))

def radial(z,r0,r1,start,bend):
    half=math.sqrt(bend*(r1-r0)-(r1-r0)**2/4)
    r=np.full_like(z,r0);d=np.zeros_like(z);dd=np.zeros_like(z)
    a=(z>start)&(z<=start+half);b=(z>start+half)&(z<start+2*half);c=z>=start+2*half
    h=z[a]-start;q=np.sqrt(bend*bend-h*h)
    r[a]=r0+bend-q;d[a]=h/q;dd[a]=bend*bend/q**3
    h=start+2*half-z[b];q=np.sqrt(bend*bend-h*h)
    r[b]=r1-bend+q;d[b]=h/q;dd[b]=-bend*bend/q**3
    r[c]=r1
    return r,d,dd

def family(z0=130.,z1=200.,r0=10.6,r1=15.2,flare_start=173.,flare_radius=30.,samples=1401):
    H=z1-z0;half=math.sqrt(flare_radius*(r1-r0)-(r1-r0)**2/4)
    assert z0<flare_start<flare_start+2*half<z1
    breaks=np.array([0.,(flare_start-z0)/H,(flare_start+half-z0)/H,(flare_start+2*half-z0)/H,1.])
    qs=[];ws=[]
    for a,b in zip(breaks,breaks[1:]):
        qs.extend(a+(G+1)/2*(b-a));ws.extend(W/2*(b-a))
    qs=np.asarray(qs);ws=np.asarray(ws)
    qr,qd,qdd=radial(z0+H*qs,r0,r1,flare_start,flare_radius)
    def length(co):
        thd=poly.polyval(qs,poly.polyder(co))
        return float(np.sum(ws*np.sqrt(H*H+(H*qd)**2+(qr*thd)**2)))
    target=length(math.pi/3*S)+.025
    t=np.unique(np.r_[np.linspace(0,1,samples),breaks]);dt=np.diff(t).max()
    r,d,dd=radial(z0+H*t,r0,r1,flare_start,flare_radius);d*=H;dd*=H*H
    slope=half/math.sqrt(flare_radius**2-half**2)
    bend2=flare_radius**2/(flare_radius**2-half**2)**1.5
    rows=[]
    for yaw in range(-60,61,10):
        alpha=math.radians(yaw);lo,hi=0.,3.
        assert length(alpha*S)<=target<=length(alpha*S+hi*B)
        for _ in range(52):
            mid=(lo+hi)/2
            if length(alpha*S+mid*B)<target:lo=mid
            else:hi=mid
        co=alpha*S+(lo+hi)/2*B
        th=poly.polyval(t,co);thd=poly.polyval(t,poly.polyder(co));thdd=poly.polyval(t,poly.polyder(co,2))
        cs,sn=np.cos(th),np.sin(th)
        p=np.c_[r*cs,r*sn,z0+H*t]
        velocity=np.c_[d*cs-r*sn*thd,d*sn+r*cs*thd,np.full(len(t),H)]
        acceleration=np.c_[(dd-r*thd**2)*cs-(2*d*thd+r*thdd)*sn,
            (dd-r*thd**2)*sn+(2*d*thd+r*thdd)*cs,np.zeros(len(t))]
        curvature=np.linalg.norm(np.cross(velocity,acceleration),axis=1)/np.linalg.norm(velocity,axis=1)**3
        td=absmax(poly.polyder(co));tdd=absmax(poly.polyder(co,2))
        second=H*H*bend2+r1*td*td+2*H*slope*td+r1*tdd
        rows.append(dict(yaw_deg=yaw,points=p,coefficients=co.tolist(),length_mm=length(co),
            minimum_sampled_bend_mm=float(1/curvature.max()),chord_error_mm=float(second*dt*dt/8)))
    return rows

def rotate(p,degrees):
    angle=math.radians(degrees);c,s=math.cos(angle),math.sin(angle)
    return np.asarray(p)@np.array([[c,-s,0],[s,c,0],[0,0,1]]).T
