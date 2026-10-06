"""Planar upper-camera corridor, with explicit assumed terminal datums."""
import math
import numpy as np

def route(start,end,rear_radius=3.,front_radius=3.5,offset=1.8,width=6.6,step=.15):
    pos=np.asarray(start[1:],float).copy(); angle=math.pi/2
    points=[]; tangents=[]; pieces=[]; length=0.
    def line(L):
        nonlocal pos,length
        assert L>=0
        T=np.array([math.cos(angle),math.sin(angle)])
        for u in np.linspace(0,1,max(1,math.ceil(L/step))+1)[:-1]:
            points.append(pos+L*u*T); tangents.append(T)
        pieces.append(dict(kind='line',length_mm=float(L))); pos+=L*T; length+=L
    def arc(R,turn):
        nonlocal pos,angle,length
        a=angle; origin=pos.copy(); sign=np.sign(turn)
        for u in np.linspace(0,turn,max(2,math.ceil(R*abs(turn)/step))+1)[:-1]:
            points.append(origin+R/sign*np.array([math.sin(a+u)-math.sin(a),-math.cos(a+u)+math.cos(a)]))
            tangents.append(np.array([math.cos(a+u),math.sin(a+u)]))
        pos=origin+R/sign*np.array([math.sin(a+turn)-math.sin(a),-math.cos(a+turn)+math.cos(a)])
        angle+=turn; length+=R*abs(turn)
        pieces.append(dict(kind='arc',radius_mm=R,turn_deg=math.degrees(turn),length_mm=R*abs(turn)))
    theta=math.acos(1-offset/10.); arc(5.,theta); arc(5.,-theta)
    turn=math.radians(100); height=end[2]-front_radius*(1-math.cos(turn))
    line(height-rear_radius-pos[1]); arc(rear_radius,-math.pi/2)
    line(end[1]-front_radius*math.sin(turn)-pos[0]); arc(front_radius,turn)
    points.append(pos.copy()); tangents.append(np.array([math.cos(angle),math.sin(angle)]))
    p=np.column_stack([np.zeros(len(points)),np.array(points)])
    T=np.column_stack([np.zeros(len(tangents)),np.array(tangents)])
    W=np.repeat([[1.,0,0]],len(p),axis=0); N=np.cross(T,W); thickness=.15
    vertices=np.stack([p-W*width/2-N*thickness/2,p+W*width/2-N*thickness/2,
        p+W*width/2+N*thickness/2,p-W*width/2+N*thickness/2],axis=1).reshape(-1,3)
    f=[]
    for i in range(len(p)-1):
        for j in range(4):
            a=4*i+j; b=4*i+(j+1)%4; f.extend([[a,b,b+4],[a,b+4,a+4]])
    f.extend([[0,2,1],[0,3,2]]); a=4*(len(p)-1); f.extend([[a,a+1,a+2],[a,a+2,a+3]])
    f=np.array(f,dtype=np.uint64)
    if np.einsum('ij,ij->i',vertices[f[:,0]],np.cross(vertices[f[:,1]],vertices[f[:,2]])).sum()<0: f=f[:,::-1].copy()
    assert np.linalg.norm(p[-1]-end)<1e-8
    radius=min(5.,front_radius,rear_radius)
    return dict(points_mm=p,tangents=T,width_vectors=W,vertices_mm=vertices,triangles=f,
        metadata=dict(length_mm=length,width_mm=width,thickness_mm=thickness,
            rear_radius_mm=rear_radius,front_radius_mm=front_radius,rearward_offset_mm=offset,
            minimum_radius_mm=radius,chord_error_bound_mm=(radius+thickness/2)*(1-math.cos(step/radius/2)),
            start_mm=list(start),end_mm=list(end),pieces=pieces,start_tangent=T[0].tolist(),end_tangent=T[-1].tolist(),
            planar=True,twist_deg=0.,classification='PLACEHOLDER',data_status='ASSUMED',
            limits='Only capacity: full FPC length/profile, lower-edge exit and bend limits unknown; no compatible extension selected.'))
