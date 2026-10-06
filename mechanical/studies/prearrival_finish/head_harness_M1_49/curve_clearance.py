"""Curve distance utilities with global conservative distance bounds."""
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

def prepared(p,radius=.3302,error=.0003):
    p=np.asarray(p);tree=KDTree(len(p))
    for i,v in enumerate(p):tree.insert(Vector(v),i)
    tree.balance()
    return dict(p=p,tree=tree,radius=radius,error=error,
        step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),lo=p.min(0),hi=p.max(0))

def pair(a,b,gap=.3):
    box=float(np.linalg.norm(np.maximum(np.maximum(a['lo']-b['hi'],b['lo']-a['hi']),0.)))
    lower=box-a['radius']-b['radius']-a['error']-b['error']-1e-4
    if lower>=gap:return dict(status='PASS',gap_lower_bound_mm=lower,method='global bounding box separation')
    d,k=min((float(b['tree'].find(Vector(v))[2]),i) for i,v in enumerate(a['p']))
    lower=d-a['radius']-b['radius']-(a['step']+b['step'])/2-a['error']-b['error']-1e-4
    return dict(status='PASS' if lower>=gap else 'BLOCKED',gap_lower_bound_mm=lower,
        method='global nearest samples minus both half-steps and chord-error bounds',point_mm=a['p'][k].tolist())

def self_clear(a,minimum_material_separation=5.,gap=.3,indices=None):
    p=a['p'];s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    threshold=2*a['radius']+gap+a['step']+2*a['error']+1e-4
    ids=range(len(p)) if indices is None else indices
    for i in ids:
        for _,j,d in a['tree'].find_range(Vector(p[i]),threshold):
            if abs(s[i]-s[j])>minimum_material_separation:
                return dict(status='BLOCKED',i=int(i),j=int(j),distance_mm=float(d),
                    required_bound_mm=threshold,point_mm=p[i].tolist())
    return dict(status='PASS',minimum_material_separation_mm=minimum_material_separation,
        scope='Remote self approach; adjacent spans excluded using the separately checked minimum bend radius')
