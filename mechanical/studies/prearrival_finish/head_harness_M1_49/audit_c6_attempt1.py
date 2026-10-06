"""Quantify the rejected first C6 cut; do not substitute it into main."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes/c6_left_slot_entry_attempt1'
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha,manifold
ctx=Context();raw=np.load(OUT/'Yaw_Base_candidate.npz')
new=manifold.Manifold(manifold.Mesh64(raw['vertices_mm'],raw['triangles'].astype(np.uint64)))
old=ctx.ss['Yaw_Base'].m;removed=old-new
inner=removed^manifold.Manifold.cylinder(40,11.69,11.69,720).translate([0,0,125])
v=np.asarray(inner.to_mesh64().vert_properties[:,:3]);r=np.linalg.norm(v[:,:2],axis=1) if len(v) else np.array([])
ctx.assert_unchanged()
result=dict(status='FAIL' if inner.volume()>1e-7 else 'PASS',scope='Audit of first independent candidate only; it was not adopted',
    sources=ctx.sources,candidate_sha256=sha(OUT/'Yaw_Base_candidate.npz'),removed_volume_mm3=removed.volume(),
    removed_inside_R11_69_mm3=inner.volume(),inner_removed_radius_range_mm=[float(r.min()),float(r.max())] if len(r) else [],
    inner_removed_bounds_mm=[v.min(0).tolist(),v.max(0).tolist()] if len(v) else [],
    disposition='Rejected. New candidate must subtract only the incremental outer annular strip, not recut the old full slot.',
    main_changed=False,script_sha256=sha(Path(__file__)))
(OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('C6_ATTEMPT1_AUDIT',result,flush=True)
