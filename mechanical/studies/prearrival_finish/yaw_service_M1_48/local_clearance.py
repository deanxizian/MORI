"""Lipschitz clearance bound using adjacent sample spans, not global spacing.

Every curve interval is covered by its nearest endpoint plus half its length.
The declared curve-to-chord error remains added. This tightens the numerical
bound without changing wire diameter or the required physical surface gap.
"""
import numpy as np
from mathutils import Vector


def clear(ctx, points, chord_error=0., ignore=(), radius=.3302, surface_gap=.3):
    p = np.asarray(points)
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    assert len(ds) and np.all(ds > 0)
    adjacent = np.maximum(np.r_[ds[0], ds], np.r_[ds, ds[-1]])
    bounds = radius + surface_gap + adjacent/2 + chord_error + 1e-4
    for name, target in ctx.targets.items():
        if name in ignore:
            continue
        ids = np.flatnonzero(np.all(p >= target['lo']-bounds[:,None], axis=1)
                            & np.all(p <= target['hi']+bounds[:,None], axis=1))
        for i in ids:
            near = target['tree'].find_nearest(Vector(p[i]))
            distance = float(near[3])
            if distance < bounds[i]:
                return dict(object=name, point_index=int(i), point_mm=p[i].tolist(),
                            nearest_surface_mm=list(near[0]), surface_distance_mm=distance,
                            required_bound_mm=float(bounds[i]),
                            surface_gap_lower_bound_mm=float(distance-radius-adjacent[i]/2-chord_error-1e-4))
        # A wholly enclosed curve segment need not approach the surface.
        starts = ids[np.r_[True, np.diff(ids)>1]] if len(ids) else []
        for i in starts:
            point = p[i]
            if np.all(point >= target['lo']) and np.all(point <= target['hi']):
                from common import manifold
                probe = manifold.Manifold.sphere(.005,12).translate(point.tolist())
                if (probe ^ target['m']).volume() > probe.volume()/2:
                    return dict(object=name, point_index=int(i), point_mm=point.tolist(), inside=True)
    return None


def adaptive_clear(ctx, points, chord_error=0., ignore=(), radius=.3302, surface_gap=.3):
    """Refine ambiguous straight chords while retaining original curve error.

    The 1-Lipschitz surface distance gives a certified interval lower bound.
    Refinement only samples existing chords; it neither moves their geometry
    nor changes the retained curve-to-chord error or required surface gap.
    """
    p=np.asarray(points)
    ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
    adjacent=np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])
    need=radius+surface_gap+chord_error+1e-4
    bounds=need+adjacent/2
    for name,target in ctx.targets.items():
        if name in ignore: continue
        ids=np.flatnonzero(np.all(p>=target['lo']-bounds[:,None],axis=1)
                          &np.all(p<=target['hi']+bounds[:,None],axis=1))
        cache={}
        def distance(q):
            return float(target['tree'].find_nearest(Vector(q))[3])
        for i in ids: cache[int(i)]=distance(p[i])
        uncertain=[int(i) for i in ids if cache[int(i)]<bounds[i]]
        segments=set()
        for i in uncertain:
            if i: segments.add(i-1)
            if i+1<len(p): segments.add(i)
        for i in sorted(segments):
            for j in (i,i+1):
                if j not in cache: cache[j]=distance(p[j])
            stack=[(p[i],p[i+1],cache[i],cache[i+1],0)]
            while stack:
                a,b,da,db,depth=stack.pop()
                length=float(np.linalg.norm(b-a))
                if min(da,db)<need:
                    q,d=(a,da) if da<db else (b,db)
                    return dict(object=name,point_mm=q.tolist(),surface_distance_mm=d,
                                required_bound_mm=need,source_segment=int(i),
                                surface_gap_lower_bound_mm=d-radius-chord_error-1e-4,
                                refinement_depth=depth)
                lower=(da+db-length)/2
                if lower>=need: continue
                if depth>=20:
                    return dict(object=name,point_mm=((a+b)/2).tolist(),
                                numerical_interval_unresolved=True,segment_length_mm=length)
                mid=(a+b)/2;dm=distance(mid)
                stack.extend([(a,mid,da,dm,depth+1),(mid,b,dm,db,depth+1)])
        starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
        for i in starts:
            point=p[i]
            if np.all(point>=target['lo']) and np.all(point<=target['hi']):
                from common import manifold
                probe=manifold.Manifold.sphere(.005,12).translate(point.tolist())
                if (probe^target['m']).volume()>probe.volume()/2:
                    return dict(object=name,point_mm=point.tolist(),inside=True)
    return None
