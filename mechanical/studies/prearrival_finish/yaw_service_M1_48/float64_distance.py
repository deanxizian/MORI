"""Vectorized point-to-triangle distance, including degenerate edges."""
import numpy as np


def minimum(point, vertices, triangles):
    q=np.asarray(point,dtype=np.float64)
    a,b,c=(vertices[triangles[:,i]] for i in range(3))
    ab=b-a;bc=c-b;ca=a-c
    normal=np.cross(ab,c-a)
    area2=np.einsum('ij,ij->i',normal,normal)
    inside=(np.einsum('ij,ij->i',np.cross(ab,q-a),normal)>=0)
    inside&=(np.einsum('ij,ij->i',np.cross(bc,q-b),normal)>=0)
    inside&=(np.einsum('ij,ij->i',np.cross(ca,q-c),normal)>=0)
    signed=np.einsum('ij,ij->i',q-a,normal)
    best=np.full(len(a),np.inf)
    use=inside&(area2>1e-30)
    best[use]=signed[use]**2/area2[use]
    for origin,edge in [(a,ab),(b,bc),(c,ca)]:
        den=np.einsum('ij,ij->i',edge,edge)
        t=np.clip(np.divide(np.einsum('ij,ij->i',q-origin,edge),den,
                            out=np.zeros(len(a)),where=den>0),0,1)
        delta=q-origin-t[:,None]*edge
        best=np.minimum(best,np.einsum('ij,ij->i',delta,delta))
    index=int(np.argmin(best))
    return float(np.sqrt(best[index])),index
