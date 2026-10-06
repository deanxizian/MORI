"""Same bounded PH search, with convex/BVH screening and exact cross-checks.

This remains a bare-housing space diagnostic, not a completed cable assembly.
All convex search shapes are conservative bounds; no obstacle is removed.
"""
from pathlib import Path
FAST_SCRIPT=Path(__file__).resolve();FAST_BASE=FAST_SCRIPT.parent/'plan_CAM_PH_rotated_entry.py'
code=FAST_BASE.read_text();prefix,run=code.split('started=time.time();expanded=0;',1)
__file__=str(FAST_BASE);exec(compile(prefix,str(FAST_BASE),'exec'),globals());__file__=str(FAST_SCRIPT)
ROT_SCRIPT=FAST_SCRIPT;ROT_OUT=STOCK_OUT/'PH_rotated_entry_fast';ROT_OUT.mkdir(exist_ok=True)
exact_collision=collision;exact_audits=[];convex_queries=0
target_vertices={n:np.asarray(m.to_mesh64().vert_properties[:,:3]) for n,(m,*_) in target_data.items()}
def fast_hit(m):
    raw=m.to_mesh64();v=np.asarray(raw.vert_properties[:,:3]);f=np.asarray(raw.tri_verts,dtype=np.uint64)
    tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True,epsilon=1e-6)
    tris=v[f];normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);length=np.linalg.norm(normal,axis=1)
    normal=normal[length>1e-12]/length[length>1e-12,None];offset=np.sum(normal*tris[length>1e-12,0],axis=1)
    # Verify convexity of the shape before using half spaces for containment.
    assert np.max(v@normal.T-offset)<=2e-5
    center=v.mean(0)
    for name,solid in near(m):
        _,lo,hi,target_tree=target_data[name]
        if tree.overlap(target_tree):return dict(obstacle=name,kind='padded_surface_contact')
        verts=target_vertices[name]
        if np.any(np.all(verts@normal.T<=offset+1e-7,axis=1)):
            return dict(obstacle=name,kind='obstacle_inside_convex_bound')
        if np.all(center>=lo) and np.all(center<=hi):
            probe=manifold.Manifold.sphere(.005,12).translate(center.tolist())
            if (probe^solid).volume()>probe.volume()/2:
                return dict(obstacle=name,kind='convex_bound_inside_obstacle')
    return None
def collision(m,allow_native=False):
    global queries,convex_queries
    if allow_native:return exact_collision(m,True)
    queries+=1;convex_queries+=1;out=fast_hit(m)
    # Sample successful as well as rejected queries against the original
    # closed-solid Boolean. Surface touching may be conservatively rejected.
    if convex_queries<=12 or convex_queries%100==0:
        exact=exact_collision(m)
        exact_audits.append(dict(query=convex_queries,fast_clear=out is None,exact_clear=exact is None))
        assert not(out is None and exact is not None),(out,exact)
    return out
exec(compile('started=time.time();expanded=0;'+run,str(FAST_BASE),'exec'),globals())
report.update(optimizer_base_sha256=sha(FAST_BASE),collision_method='Convex half-space containment, boundary BVH overlap, and closed-solid center containment; conservative padded-contact rejection',
              exact_boolean_audits=exact_audits,convex_queries=convex_queries)
(ROT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('PH_FAST_AUDIT',len(exact_audits),'exact comparisons',flush=True)
