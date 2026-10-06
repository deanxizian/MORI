"""Add a straight terminal approach to the unselected camera-FPC allocation."""
import math
import numpy as np
from camera_flex_corridor_geometry import route

def terminal_route(start,end,tail=2.,width=6.6):
    direction=np.array([0.,-math.sin(math.radians(10)),math.cos(math.radians(10))])
    end=np.asarray(end,float); g=route(start,end-direction*tail,front_radius=4.,width=width)
    n=max(1,math.ceil(tail/.15)); fractions=np.linspace(0,1,n+1)[1:]
    p=g['points_mm'][-1]+fractions[:,None]*tail*direction
    last=g['vertices_mm'][-4:]; v=np.concatenate([g['vertices_mm'],(last[None,:,:]+fractions[:,None,None]*tail*direction).reshape(-1,3)])
    faces=g['triangles'][:-2].tolist(); count=len(g['points_mm'])
    for i in range(count-1,count+n-1):
        for j in range(4):
            a=4*i+j; b=4*i+(j+1)%4; faces.extend([[a,b,b+4],[a,b+4,a+4]])
    a=4*(count+n-1); faces.extend([[a,a+1,a+2],[a,a+2,a+3]])
    f=np.array(faces,dtype=np.uint64)
    # Base ribbon may have globally flipped winding; restore a consistent winding from geometry.
    # Its first side normal sign determines how the newly appended side triangles are oriented.
    old=g['triangles'][0].tolist()
    if old==[5,1,0]:
        f[len(g['triangles'])-2:]=f[len(g['triangles'])-2:,::-1]
    g['points_mm']=np.vstack([g['points_mm'],p])
    g['tangents']=np.vstack([g['tangents'],np.repeat(direction[None,:],n,axis=0)])
    g['width_vectors']=np.vstack([g['width_vectors'],np.repeat([[1.,0,0]],n,axis=0)])
    g['vertices_mm']=v; g['triangles']=f
    g['metadata']['length_mm']+=tail; g['metadata']['end_mm']=end.tolist()
    g['metadata']['terminal_straight_mm']=tail
    g['metadata']['pieces'].append(dict(kind='line',length_mm=tail))
    assert np.linalg.norm(g['points_mm'][-1]-end)<1e-8
    return g
