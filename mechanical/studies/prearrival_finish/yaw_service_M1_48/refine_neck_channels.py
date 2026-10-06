"""Independent two-print trial, based on native M1.48 and full route datums.

Retain the previous terminal-passage subtraction; add clearance for the actual
joined wire centreline. No historical raised cable-anchor geometry is copied.
All new solids remain study files. Print strength and installation stay open.
"""
from pathlib import Path
import sys,json,time
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
ctx=Context();started=time.time()
report_path=HERE/'cuts_adaptive_screen.json'
report=json.loads(report_path.read_text())
assert report['source_main_sha256']==ctx.source_hash
A8=HERE.parent/'harness_A8'
path=A8/'cam_pitch_port/lower_staging/body_partial_curves.npz'
curves=np.load(path)
radius=.74; sphere=manifold.Manifold.sphere(radius,24)
sm=sphere.to_mesh64();vv=np.asarray(sm.vert_properties[:,:3]);ff=np.asarray(sm.tri_verts)
a,b,c=vv[ff[:,0]],vv[ff[:,1]],vv[ff[:,2]]
n=np.cross(b-a,c-a)
inradius=float(np.min(np.abs(np.einsum('ij,ij->i',a,n))/np.linalg.norm(n,axis=1)))

def save(name,m):
    mesh=m.to_mesh64();p=HERE/f'refined_{name}.npz'
    np.savez_compressed(p,vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
    return p

rows=[]
for part,zmin,zmax in [('Yaw_Base',137.,165.),('Pitch_Yoke',174.,194.)]:
    native=ctx.ss[part].m
    cached=HERE/f'cuts_{part}_trial.npz';d=np.load(cached)
    previous=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    assert abs((previous-native).volume())<1e-5
    cuts=[];source_rows=[]
    for pin in range(1,5):
        key=f'pin{pin}_yaw0';p=curves[key]
        ids=np.flatnonzero((p[:,2]>=zmin)&(p[:,2]<=zmax)&(np.linalg.norm(p[:,:2],axis=1)<20.))
        assert len(ids),(part,pin)
        # Some body-side leads enter the same radial window earlier. Only the
        # final contiguous run is the neck lead; do not cut around body loops.
        groups=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
        ids=groups[-1]
        assert np.all(np.diff(ids)==1)
        p=p[ids[0]:ids[-1]+1]
        # Keep the actual source vertices: no route shift or artificial radius fit.
        instances=[sphere.translate(q.tolist()) for q in p]
        capsules=[manifold.Manifold.batch_hull([a,b]) for a,b in zip(instances,instances[1:])]
        sweep=manifold.Manifold.batch_boolean(capsules,manifold.OpType.Add)
        cuts.append(sweep)
        source_rows.append(dict(pin=pin,source_key=key,source_indices=[int(ids[0]),int(ids[-1])],points=len(p)))
    tool=manifold.Manifold.batch_boolean(cuts,manifold.OpType.Add)
    raw=previous-tool
    pieces=raw.decompose()
    real=[m for m in pieces if abs(m.volume())>1e-7]
    assert len(real)==1,(part,[m.volume() for m in pieces])
    new=real[0]
    removed=native-new;extra=previous-new
    p=save(part,new);save(part+'_removed',removed);save(part+'_extra_cut',extra)
    rows.append(dict(name=part,source=str(p.relative_to(PROJECT)),source_sha256=sha(p),
        historical_cut_source=str(cached.relative_to(PROJECT)),historical_cut_source_sha256=sha(cached),
        removed_mm3=float(removed.volume()),added_mm3=float((new-native).volume()),
        extra_cut_mm3=float(extra.volume()),removed_bounds_mm=list(removed.bounding_box()),
        extra_cut_bounds_mm=list(extra.bounding_box()),
        components_mm3=[float(m.volume()) for m in pieces],
        discarded_numerical_components_mm3=[float(m.volume()) for m in pieces if abs(m.volume())<=1e-7],
        current_main_component_count=len(native.decompose()),source_rows=source_rows))
    print('REFINE_CHANNEL',part,rows[-1],flush=True)
ctx.assert_unchanged()
out=dict(**ctx.evidence())
out.update(status='PASS',scope='Construction of two independent clearance candidates only',
    script_sha256=sha(__file__),parts=rows,wire_curve_source=str(path.relative_to(PROJECT)),
    wire_curve_source_sha256=sha(path),sphere_outer_radius_mm=radius,sphere_inradius_mm=inradius,
    main_applied=False,new_printed_parts=0,new_fasteners=0,full_motion='NOT_TESTED',
    bearing_wall='NOT_TESTED',whole_harness='BLOCKED',strength='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'refined_construction.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
