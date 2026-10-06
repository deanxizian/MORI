"""Conservative threshold checks for already sampled smooth centre lines.

This returns only the requested clearance bound, never a larger global minimum.
The full centre-line KD tree is retained. Query points outside its expanded AABB
cannot violate the requested threshold; both curves' half-step and chord-error
bounds are included before excluding them. No geometry or evidence is mutated.
"""
import numpy as np
from mathutils import Vector

def pair_threshold(a,b,gap=.3):
    error=(a['step']+b['step'])/2+a['error']+b['error']+1e-4
    threshold=a['radius']+b['radius']+gap+error
    if len(a['p'])>len(b['p']):a,b=b,a
    ids=np.flatnonzero(np.all(a['p']>=b['lo']-threshold,axis=1)&np.all(a['p']<=b['hi']+threshold,axis=1))
    for i in ids:
        d=float(b['tree'].find(Vector(a['p'][i]))[2])
        if d<threshold:
            return dict(status='BLOCKED',gap_lower_bound_mm=d-a['radius']-b['radius']-error,
                point_mm=a['p'][i].tolist(),method='First conservative threshold witness; not a global minimum')
    return dict(status='PASS',gap_lower_bound_mm=gap,checked_points=len(ids),
        method='Expanded AABB exclusion and nearest-sample threshold including both half-steps and chord errors; only requested bound certified')
