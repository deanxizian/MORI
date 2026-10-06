"""Exact sampled remote-self screen using material-length spatial partitions.

Same threshold and arc-neighbour exclusion as curve_clearance.self_clear.
Partition boxes only discard pairs whose sample distances cannot reach that
threshold. Every remaining eligible sample pair is checked by a local KDTree.
"""
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

def self_clear(a,minimum_material_separation=5.,gap=.3):
    p=a['p'];s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    threshold=2*a['radius']+gap+a['step']+2*a['error']+1e-4
    bin_ids=np.floor(s/(minimum_material_separation/2)).astype(int)
    cuts=np.r_[0,np.flatnonzero(np.diff(bin_ids))+1,len(p)]
    groups=[np.arange(i,j) for i,j in zip(cuts,cuts[1:])]
    lo=np.array([p[g].min(0) for g in groups]);hi=np.array([p[g].max(0) for g in groups])
    s0=np.array([s[g[0]] for g in groups]);s1=np.array([s[g[-1]] for g in groups]);trees={};candidate_bins=0
    for i,ids in enumerate(groups):
        delta=np.maximum(np.maximum(lo[i]-hi,lo-hi[i]),0.)
        close=(np.sum(delta*delta,axis=1)<=(threshold+1e-9)**2)&(np.arange(len(groups))>i)&((s1-s0[i])>minimum_material_separation)
        for j in np.flatnonzero(close):
            candidate_bins+=1
            if j not in trees:
                t=KDTree(len(groups[j]))
                for k in groups[j]:t.insert(Vector(p[k]),int(k))
                t.balance();trees[j]=t
            for k in ids:
                for _,l,d in trees[j].find_range(Vector(p[k]),threshold):
                    if abs(s[k]-s[l])>minimum_material_separation:
                        return dict(status='BLOCKED',i=int(k),j=int(l),distance_mm=float(d),required_bound_mm=threshold,
                                    point_mm=p[k].tolist(),method='Exact eligible sample pairs after conservative material-bin AABB culling')
    return dict(status='PASS',minimum_material_separation_mm=minimum_material_separation,
                scope='Remote self approach; adjacent spans excluded using the separately checked minimum bend radius',
                method='Exact eligible sample pairs after conservative material-bin AABB culling',bins=len(groups),tested_bin_pairs=candidate_bins)
