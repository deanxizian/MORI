"""Pure tangent 3-D body-prefix construction; no scene or file side effects."""
import math
import numpy as np
from curvature_paths import paths

def make(row,azimuth,pin_coord,z=138.,R=7.,step=.06):
    p=np.asarray(pin_coord);a=p+[0,0,row['lead_mm']]
    top=a[2]+R;drop=top-(z-R)
    if not 0<drop<2*R:return None
    alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
    tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
    qq=np.linspace(0,alpha,math.ceil(R*alpha/step)+1)
    e=math.radians(row['entry_deg']);eh=np.array([math.cos(e),math.sin(e),0.])
    x=math.radians(row['exit_deg']);xh=np.array([math.cos(x),math.sin(x),0.])
    t=math.radians(azimuth);q=np.array([10.6*math.cos(t),10.6*math.sin(t),z])
    stem=np.linspace(p,a,max(2,math.ceil(np.linalg.norm(a-p)/step)+1))
    entry=a+R*(1-np.cos(tt[:,None]))*eh+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*np.sin(tt)]
    b=q-R*xh-[0,0,R];c=b-run*xh+[0,0,drop]
    first=c+R*np.sin(qq[:,None])*xh-np.c_[np.zeros(len(qq)),np.zeros(len(qq)),R*(1-np.cos(qq))]
    qr=qq[::-1]
    second=first[-1]+R*(math.sin(alpha)-np.sin(qr[:,None]))*xh-np.c_[np.zeros(len(qr)),np.zeros(len(qr)),R*(np.cos(qr)-math.cos(alpha))]
    final=b+R*np.sin(tt[:,None])*xh+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*(1-np.cos(tt))]
    end=np.vstack([first,second[1:],final[1:]])
    options=[r for r in paths(entry[-1,:2],eh[:2],c[:2],xh[:2],row['planar_radius_mm'],step) if r['family']==row['family']]
    if not options:return None
    assert len(options)==1
    plan=options[0];xy=plan['points_xy_mm'];middle=np.c_[xy,np.full(len(xy),top)]
    full=np.vstack([stem,entry[1:],middle[1:],end[1:]])
    return full,len(stem),row['lead_mm']+R*math.pi+2*R*alpha+plan['analytic_length_mm'],max(plan['chord_error_mm'],R*(1-math.cos(step/R/2)))
