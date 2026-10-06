"""Read-only connectivity of the actual central free volume at mechanical zero.

If a free-volume component touches the test box, no closed-cavity conclusion is
allowed. This check does not offset walls for wire diameter or bend radius.
"""
from pathlib import Path
SCRIPT=Path(__file__).resolve();HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
lo=np.array([-36.,-36.,132.]);hi=np.array([36.,36.,207.])
box=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
relevant=[];names=[]
for name,s in ss.items():
    if np.any(s.lo>hi) or np.any(s.hi<lo):continue
    relevant.append(s.m^box);names.append(name)
occupied=manifold.Manifold.batch_boolean(relevant,manifold.OpType.Add)
mesh=occupied.to_mesh64()
np.savez_compressed(OUT/'central_occupied_zero.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
free=box-occupied
assert free.status()==manifold.Error.NoError
components=free.decompose();rows=[]
probe=manifold.Manifold.sphere(.02,16).translate([6.8,0,166])
for i,m in enumerate(components):
    volume=float(m.volume());bb=np.asarray(m.bounding_box())
    probe_overlap=max(0.,float((m^probe).volume()))
    touches=bool(np.any(bb[:3]<=lo+1e-4) or np.any(bb[3:]>=hi-1e-4))
    rows.append(dict(index=i,volume_mm3=volume,bounds_mm=bb.tolist(),
        probe_overlap_volume_mm3=probe_overlap,component_touches_box=touches))
    if probe_overlap>1e-7:
        mesh=m.to_mesh64();np.savez_compressed(OUT/f'central_void_component_{i}.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
        print('CENTRAL_VOID_PROBE_COMPONENT',rows[-1],flush=True)
out=dict(status='PASS',scope='Raw zero-pose free-volume topology inspection only',
    source_blend_sha256=before,box_bounds_mm=[lo.tolist(),hi.tolist()],obstacle_names=names,
    component_count=len(rows),components=rows,main_geometry_changed=False,
    warning='Manifold decomposition separates boundary-connected mesh components. Negative-volume inner boundary components must not be mistaken for independent free spaces. Inspect volume signs and geometry before drawing a route conclusion.',
    wire_clearance='NOT_TESTED',bending='NOT_TESTED',motion='NOT_TESTED')
(OUT/'central_void_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('CENTRAL_VOID_COMPLETE',len(rows),flush=True)
