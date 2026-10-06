"""Higher fixed entry with unchanged approved geometry above a joining plane.

The lower angular polynomial matches position, tangent and second derivative
at the joining plane. A zero-end-derivative bump equalizes total length for
each sampled yaw. These are curve candidates, not elastic cable predictions.
"""
import math
import numpy as np
from numpy.polynomial import polynomial as poly
from neck_curve_geometry import family as approved_family,radial,rotate,G,W,absmax

B6=np.array([0.,0.,0.,64.,-192.,192.,-64.])
def family(z0=136.,join_z=156.,samples=2201):
    original=approved_family();h=join_z-z0;H=70.;ta=(join_z-130)/H
    assert z0<join_z<173.
    grid=np.unique(np.r_[np.linspace(z0,200.,samples),join_z,173.,184.519548,196.039097])
    grid=grid[(grid>=z0)&(grid<=200.)]
    r,d,dd=radial(grid,10.6,15.2,173.,30.)
    half=math.sqrt(30*4.6-4.6**2/4)
    breaks=[join_z,173.,173+half,173+2*half,200.]
    zz=np.concatenate([a+(G+1)/2*(b-a) for a,b in zip(breaks,breaks[1:])])
    ww=np.concatenate([W/2*(b-a) for a,b in zip(breaks,breaks[1:])])
    qr,qd,_=radial(zz,10.6,15.2,173.,30.)
    qu=(G+1)/2;qw=W/2
    source=[]
    matrix=np.array([[1,1,1],[3,4,5],[6,12,20]],float)
    for row in original:
        old=np.asarray(row['coefficients'])
        c=np.r_[0.,0.,0.,np.linalg.solve(matrix,[poly.polyval(ta,old),poly.polyval(ta,poly.polyder(old))*h/H,poly.polyval(ta,poly.polyder(old,2))*h*h/H**2])]
        c=np.r_[c,0.]
        upper=float(np.sum(ww*np.sqrt(1+qd*qd+(qr*poly.polyval((zz-130)/H,poly.polyder(old))/H)**2)))
        def lower(co):return float(np.sum(qw*np.sqrt(h*h+(10.6*poly.polyval(qu,poly.polyder(co)))**2)))
        source.append(dict(row=row,old=old,base=c,upper=upper,length0=upper+lower(c)))
    target=max(s['length0'] for s in source)+.001
    result=[]
    for source_row in source:
        c=source_row['base'];upper=source_row['upper'];old=source_row['old']
        def length(amp):return upper+float(np.sum(qw*np.sqrt(h*h+(10.6*poly.polyval(qu,poly.polyder(c+amp*B6)))**2)))
        lo=0.;hi=3.
        assert length(0)<=target<=length(hi)
        for _ in range(60):
            mid=(lo+hi)/2
            if length(mid)<target:lo=mid
            else:hi=mid
        co=c+(lo+hi)/2*B6
        lower_mask=grid<=join_z
        t=(grid-130)/H;u=(grid-z0)/h
        theta=poly.polyval(t,old);td=poly.polyval(t,poly.polyder(old))/H;tdd=poly.polyval(t,poly.polyder(old,2))/H**2
        theta[lower_mask]=poly.polyval(u[lower_mask],co)
        td[lower_mask]=poly.polyval(u[lower_mask],poly.polyder(co))/h
        tdd[lower_mask]=poly.polyval(u[lower_mask],poly.polyder(co,2))/h**2
        cs,sn=np.cos(theta),np.sin(theta)
        p=np.c_[r*cs,r*sn,grid]
        vel=np.c_[d*cs-r*sn*td,d*sn+r*cs*td,np.ones(len(grid))]
        acc=np.c_[(dd-r*td**2)*cs-(2*d*td+r*tdd)*sn,(dd-r*td**2)*sn+(2*d*td+r*tdd)*cs,np.zeros(len(grid))]
        k=np.linalg.norm(np.cross(vel,acc),axis=1)/np.linalg.norm(vel,axis=1)**3
        # Conservative global polynomial derivative bound; unchanged upper
        # radial profile derivatives bounded analytically as in original.
        tdmax=max(absmax(poly.polyder(co))/h,absmax(poly.polyder(old))/H)
        tddmax=max(absmax(poly.polyder(co,2))/h**2,absmax(poly.polyder(old,2))/H**2)
        slope=half/math.sqrt(30**2-half**2);rdd=30**2/(30**2-half**2)**1.5
        second=rdd+15.2*tdmax**2+2*slope*tdmax+15.2*tddmax
        result.append(dict(yaw_deg=source_row['row']['yaw_deg'],points=p,length_mm=length((lo+hi)/2),minimum_sampled_bend_mm=float(1/k.max()),chord_error_mm=float(second*np.diff(grid).max()**2/8),lower_coefficients=co.tolist(),upper_coefficients=old.tolist(),body_entry_z_mm=z0,join_z_mm=join_z))
    return result

if __name__=='__main__':
    for z in [134.,136.,138.,139.5]:
        for join in [154.,156.,158.]:
            r=family(z,join)
            print(z,join,min(x['minimum_sampled_bend_mm'] for x in r),r[0]['length_mm'])
