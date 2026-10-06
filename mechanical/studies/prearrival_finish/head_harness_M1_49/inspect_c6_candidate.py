"""Bound the C6 material change without adopting it into the assembly."""
from pathlib import Path
import json,sys,math,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/c6_left_slot_entry'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha,manifold
from common import P
from entry_channel_candidate import build
ctx=Context();start=time.time();old=ctx.ss['Yaw_Base'].m
new,construction=build(old,P['neck_harness_capacity']);removed=old-new
if not (OUT/'Yaw_Base_candidate.npz').exists():
    mesh=new.to_mesh64();np.savez_compressed(OUT/'Yaw_Base_candidate.npz',vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
reference=np.load(OUT/'Yaw_Base_candidate.npz')
saved=manifold.Manifold(manifold.Mesh64(reference['vertices_mm'],reference['triangles'].astype(np.uint64)))
assert (new-saved).volume()+(saved-new).volume()<1e-7
def cyl(r):return manifold.Manifold.cylinder(40,r,r,720).translate([0,0,125])
inner_unchanged=(removed^cyl(11.69)).volume();outside_unchanged=(removed-cyl(12.51)).volume()
assert inner_unchanged<1e-7 and outside_unchanged<1e-7
assert removed.volume()>0 and (new-old).volume()<1e-7
sections=[]
for z in [139.,142.,146.,148.,149.]:
    sections.append(dict(kind='XY',z_mm=z,old=[p.tolist() for p in old.slice(z).to_polygons()],
        new=[p.tolist() for p in new.slice(z).to_polygons()],removed=[p.tolist() for p in removed.slice(z).to_polygons()]))
for angle in [125.,144.,180.]:
    a=math.radians(angle);t=np.array([[math.cos(a),math.sin(a),0,0],[0,0,1,0],[-math.sin(a),math.cos(a),0,0]])
    sections.append(dict(kind='RZ',angle_deg=angle,old=[p.tolist() for p in old.transform(t).slice(0).to_polygons()],
        new=[p.tolist() for p in new.transform(t).slice(0).to_polygons()],removed=[p.tolist() for p in removed.transform(t).slice(0).to_polygons()]))
ctx.assert_unchanged()
result=dict(status='PASS',scope='Candidate exact material-difference and connectivity checks only; no manufacturing or load qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [HERE/'entry_channel_candidate.py',OUT/'Yaw_Base_candidate.npz']},
    construction=construction,inside_R11_69_removed_mm3=inner_unchanged,outside_R12_51_removed_mm3=outside_unchanged,
    added_volume_mm3=(new-old).volume(),sections=sections,approved=False,main_changed=False,
    motion_inference='The candidate is a strict subset of the current fixed Yaw_Base. Removing occupied volume cannot introduce a new rigid-part collision. This does not prove unchanged strength or wire clearance.',
    bearing_and_fastener_evidence='All current material inside R11.69 and outside R12.51 is unchanged; bearing seat begins at R20, keeper axes are X +/-26.2.',
    full_harness='BLOCKED',physical_strength='NOT_TESTED',script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'geometry_review.json').write_text(json.dumps(result,indent=2)+'\n');print('C6_GEOMETRY_REVIEW',construction,flush=True)
