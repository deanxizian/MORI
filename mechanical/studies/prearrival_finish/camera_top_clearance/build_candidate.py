"""Independent flat top-edge clearance candidate; main CAD remains unchanged.

Shorten only the outside upper edge of the camera pocket on Display_Frame.
The inner camera pocket, rear datum, capture lips, holes and all purchased
components retain their original positions and geometry. No new step or part.
"""
import sys,json,hashlib,time,math
from pathlib import Path
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent;PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from validate_head_cleanup import geometry_record
from optics_mount import camera_transform,camera_pupil
from export import topology
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(PROJECT)):sha(p) for p in [PROJECT/'mechanical/mori_v1_2.blend',PROJECT/'config/geometry.json',PROJECT/'contracts/mechanical_interfaces.json',PROJECT/'contracts/components.json']}
load_collections()
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[c].hide_viewport=False
assembled();bpy.context.view_layer.update()
objects={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
assert len(objects)==209
before={n:geometry_record(o) for n,o in objects.items()}
ss={n:Solid(o) for n,o in objects.items()};solids={n:s.m for n,s in ss.items()}
q=P['assembly_completion']['camera'];c=P['waveshare_detail']['camera']
rc=np.array(camera_transform().to_3x3())@np.array([[1.,0,0],[0,0,1.],[0,-1.,0]])
p=np.array(camera_pupil());tr=np.column_stack([rc,p])
wx,vy=q['pocket_outer_xy_mm'];inner_v=c['carrier_xy_mm'][1]/2+q['pocket_xy_clearance_mm']
frame=solids['Display_Frame'];shell=solids['Head_Front'];initial_volume=max(0.,float((frame^shell).volume()))
assert .007<initial_volume<.008
def local_box(lo,hi):
    lo=np.array(lo);hi=np.array(hi)
    return manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist()).transform(tr)
trials=[];chosen=None
for trim in [.1,.2,.3,.4,.5,.6]:
    top=-vy/2+trim
    cut=local_box([-wx/2-.001,-vy/2-2,q['pocket_back_w_mm']-.001],
                  [wx/2+.001,top,q['pocket_wall_front_w_mm']+.001])
    candidate=frame-cut;gap=float(candidate.min_gap(shell,1.));overlap=max(0.,float((candidate^shell).volume()))
    wall=-top-inner_v
    row=dict(trim_mm=trim,top_local_v_mm=top,nominal_upper_wall_mm=wall,
             shell_gap_mm=gap,shell_overlap_mm3=overlap,removed_volume_mm3=float((frame-candidate).volume()),
             status='PASS' if gap>=.3-1e-5 and overlap<1e-7 and wall>=1.2-1e-8 else 'BLOCKED')
    trials.append(row);print('TOP_EDGE_TRIAL',row,flush=True)
    if chosen is None and row['status']=='PASS':chosen=(row,candidate,cut)
assert chosen,'No candidate met the stated 0.3mm gap and 1.2mm nominal upper-wall allocations.'
selected,candidate,cut=chosen
removed=frame-candidate;added=candidate-frame
assert max(0.,added.volume())<1e-7
inner_protected=local_box([-inner_v-.001,-inner_v-.001,c['carrier_back_from_pupil_mm']-q['pocket_back_clearance_mm']-.001],
                         [inner_v+.001,inner_v+.001,12])
inner_change=max(0.,float((removed^inner_protected).volume()))
assert inner_change<1e-7
raw=candidate.to_mesh64();vv=np.array(raw.vert_properties[:,:3],copy=True);ff=np.array(raw.tri_verts,dtype=np.uint64,copy=True)
np.savez_compressed(OUT/'Display_Frame.npz',vertices_mm=vv,triangles=ff)
raw_removed=removed.to_mesh64();np.savez_compressed(OUT/'removed.npz',vertices_mm=raw_removed.vert_properties[:,:3],triangles=raw_removed.tri_verts)
topo=topology(vv,ff.tolist())
topo['status']='PASS' if all(topo[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles']) and topo['signed_volume_mm3']>0 else 'FAIL'
assert topo['status']=='PASS',topo
o=objects['Display_Frame'];mats=list(o.data.materials);me=bpy.data.meshes.new('CAMERA_TOP_CLEARANCE_Display_Frame')
me.from_pydata(vv.tolist(),[],ff.tolist());me.update();o.data=me;o.matrix_world=Matrix.Identity(4)
for m in mats:me.materials.append(m)
o['camera_top_clearance_candidate']='UNADOPTED: continuous upper edge trimmed '+str(selected['trim_mm'])+'mm; original inner seat, axes and hardware retained.'
o['data_status']='ASSUMED';o['manufacturing_release']=False
bpy.context.view_layer.update()
after={n:geometry_record(o) for n,o in objects.items()}
assert [n for n in before if before[n]!=after[n]]==['Display_Frame']
captured={n:dict(local_mesh_sha256=after[n]['local_mesh_sha256'],world_matrix=after[n]['world_matrix']) for n in objects if n!='Display_Frame'}
sc=bpy.context.scene;sc['independent_study']='Camera pocket upper outside edge clearance candidate; unadopted, not for manufacture'
sc['source_main_sha256']=protected['mechanical/mori_v1_2.blend']
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
report=dict(status='PASS',scope='One independent source-preserving geometry candidate, pending saved-mesh/path verification and user adoption',
 script_sha256=sha(SCRIPT),source_main_sha256=protected['mechanical/mori_v1_2.blend'],protected_sources=protected,
 source_objects=209,changed_parts=['Display_Frame'],unchanged_source_parts=208,
 old_local_top_v_mm=-vy/2,camera_local_basis_columns=rc.tolist(),camera_pupil_world_mm=p.tolist(),trials=trials,
 selected=selected,nominal_wall_scope='Upper camera-pocket wall between the unchanged inner plane and the new outer top plane only; not minimum wall of the full part or strength approval',
 added_material_mm3=max(0.,float(added.volume())),inner_camera_seat_changed_mm3=inner_change,
 original_shell_overlap_mm3=initial_volume,topology=topo,unchanged_part_fingerprints=captured,
 camera_evidence='Photo-estimated OV3660 dimensions remain ASSUMED; no new manufacturer or measurement claim',
 source_fov_and_capture_parts_unchanged=True,main_applied=False,manufacturing_release=False,
 candidate_sha256=sha(OUT/'candidate.blend'),mesh_sha256=sha(OUT/'Display_Frame.npz'),removed_sha256=sha(OUT/'removed.npz'))
(OUT/'construction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/k)==v for k,v in protected.items())
print('CAMERA_TOP_CANDIDATE_DONE',selected,flush=True)
