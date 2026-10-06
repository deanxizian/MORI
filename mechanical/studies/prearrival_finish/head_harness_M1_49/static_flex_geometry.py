"""Pure planar ribbon packing allocation, not a terminated FFC model.

The width stays vertical; bends are cylindrical about Z with no twist or
hard-way bending. The two unknown insertion/approach portions are excluded.
"""
import math
import numpy as np

def core(length=170., radius=5., width=10.5, thickness=.2, z=236., step=.2):
    # Four horizontal runs, 52 mm of vertical runs, six rounded 90deg turns.
    right=(length-52+6*(2-math.pi/2)*radius)/4-10
    pts=np.array([[-10,-16,z],[right,-16,z],[right,0,z],[-10,0,z],
                  [-10,16,z],[right,16,z],[right,36,z],[-10,36,z]],float)
    segments=[];tangents=[];piece=[];start=pts[0]
    def line(a,b):
        d=b-a;l=float(np.linalg.norm(d));n=max(1,math.ceil(l/step))
        if l<1e-10:return
        segments.extend(np.linspace(a,b,n+1)[:-1]);tangents.extend([d/l]*n)
        piece.append(dict(kind='line',length_mm=l))
    for i in range(1,len(pts)-1):
        u=(pts[i]-pts[i-1]);u/=np.linalg.norm(u)
        v=(pts[i+1]-pts[i]);v/=np.linalg.norm(v)
        assert abs(u@v)<1e-10
        a=pts[i]-radius*u;b=pts[i]+radius*v
        assert np.linalg.norm(pts[i]-pts[i-1])>2*radius or i==1
        line(start,a)
        n=max(2,math.ceil(math.pi*radius/2/step));center=a+radius*v
        for angle in np.linspace(0,math.pi/2,n+1)[:-1]:
            segments.append(center-radius*v*math.cos(angle)+radius*u*math.sin(angle))
            tangents.append(v*math.sin(angle)+u*math.cos(angle))
        piece.append(dict(kind='arc',radius_mm=radius,angle_rad=math.pi/2,length_mm=math.pi*radius/2))
        start=b
    line(start,pts[-1]);segments.append(pts[-1]);tangents.append((pts[-1]-pts[-2])/np.linalg.norm(pts[-1]-pts[-2]))
    p=np.array(segments);t=np.array(tangents);normal=np.column_stack([-t[:,1],t[:,0],np.zeros(len(t))])
    wz=np.array([0,0,width/2]);n=normal*thickness/2
    vertices=np.stack([p-wz-n,p+wz-n,p+wz+n,p-wz+n],axis=1).reshape(-1,3)
    triangles=[]
    for i in range(len(p)-1):
        for j in range(4):
            a=4*i+j;b=4*i+(j+1)%4;c=b+4;d=a+4
            triangles.extend([[a,b,c],[a,c,d]])
    triangles.extend([[0,2,1],[0,3,2]])
    a=4*(len(p)-1);triangles.extend([[a,a+1,a+2],[a,a+2,a+3]])
    # Mesh orientation fixed once for this rectangular sweep.
    triangles=np.asarray(triangles,dtype=np.uint64)
    volume=np.einsum('ij,ij->i',vertices[triangles[:,0]],
        np.cross(vertices[triangles[:,1]],vertices[triangles[:,2]])).sum()/6
    if volume<0:triangles=triangles[:,::-1].copy()
    max_angle=(math.pi/2)/math.ceil(math.pi*radius/2/step)
    error=(radius+thickness/2)*(1-math.cos(max_angle/2))
    exact=sum(s['length_mm'] for s in piece)
    assert abs(exact-length)<1e-9
    return dict(points_mm=p,tangents=t,vertices_mm=vertices,triangles=triangles,
        metadata=dict(analytic_length_mm=exact,polyline_length_mm=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),
            radius_mm=radius,width_mm=width,thickness_mm=thickness,z_mm=z,
            points=len(p),chord_error_bound_mm=error,planar=True,twist_deg=0,
            ends_mm=[p[0].tolist(),p[-1].tolist()],rightmost_vertex_x_mm=right,
            full_cable_length_mm=200,unmodeled_end_approach_reserve_mm=[15,15],
            endpoint_fit='NOT_TESTED',width_thickness_radius_evidence='ASSUMED capacity screen only'))
