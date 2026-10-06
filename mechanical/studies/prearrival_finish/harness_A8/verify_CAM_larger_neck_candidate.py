"""Reload the larger-neck candidate and check bounded continuous sweeps.

Keeps the 0.3 mm requirement. The check padding is below the construction
padding but its inscribed radius minus interpolation error exceeds 0.3 mm.
No whole-harness or strength claim follows from this local verification.
"""
import sys,json,hashlib,time,math,collections
from pathlib import Path
LNV_SCRIPT=Path(__file__).resolve();LNV_A8=LNV_SCRIPT.parent;PROJECT=LNV_A8.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
LNV_OUT=LNV_A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
LNV_INPUT=Path(bpy.data.filepath)
assert LNV_INPUT in (LNV_OUT/'candidate.blend',LNV_OUT/'cleaned/candidate.blend')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
LNV_HASH=sha(LNV_INPUT);LNV_BUILD=json.loads((LNV_OUT/'construction.json').read_text())
if LNV_INPUT.parent.name=='cleaned':
    LNV_STORAGE=json.loads((LNV_OUT/'cleaned/storage.json').read_text())
    assert LNV_STORAGE['status']=='PASS' and LNV_STORAGE['output_candidate_sha256']==LNV_HASH
    assert LNV_STORAGE['source_candidate_sha256']==LNV_BUILD['candidate_blend_sha256']
else:assert LNV_BUILD['candidate_blend_sha256']==LNV_HASH
assert LNV_BUILD['script_sha256']==sha(LNV_A8/'build_CAM_larger_neck_candidate.py')
assert all(sha(PROJECT/p)==h for p,h in LNV_BUILD['protected_sources'].items())
load_collections();assembled();bpy.context.view_layer.update()
LNV_PHYSICAL={o.name.removeprefix(PREFIX):o for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
assert len(LNV_PHYSICAL)==209
LNV_AUDIT_HELPER=LNV_A8/'repair_threading_storage.py'
code='def mesh_check'+LNV_AUDIT_HELPER.read_text().split('def mesh_check',1)[1].split('\nrows=[]',1)[0]
exec(compile(code,str(LNV_AUDIT_HELPER),'exec'),globals())
LNV_TOPOLOGY={n:mesh_check(LNV_PHYSICAL[n].data)[0] for n in ('Yaw_Base','Pitch_Yoke')}
LNV_SOURCE={n:Solid(o).m for n,o in LNV_PHYSICAL.items()}
# The candidate already contains the 29 sourced mating allocations. Read them
# in place rather than importing duplicate .001 objects and losing port keys.
plug={o.name.removeprefix(PREFIX+'PREARRIVAL_Plug_'):Solid(o) for o in bpy.context.scene.objects
      if o.type=='MESH' and o.name.startswith(PREFIX+'PREARRIVAL_Plug_')}
assert len(plug)==LNV_BUILD['mating_allocations']==29
fixed_file=LNV_A8.parent/'harness_A2/assembly_safe_review/fourteen_wire_solids.json'
fixed_data=json.loads(fixed_file.read_text())
assert sha(fixed_file)==LNV_BUILD['source_fixed_wires_sha256']
fixed={n:{'m':manifold.Manifold(manifold.Mesh64(np.asarray(r['vertices_mm']),np.asarray(r['triangles'],dtype=np.uint64)))} for n,r in fixed_data.items()}
source_hash=LNV_BUILD['source_main_sha256'];REQUIRED_R=LNV_BUILD['required_wire_bend_radius_mm']
LNV_TARGETS=dict(LNV_SOURCE)
LNV_TARGETS.update({'Plug_'+n:s.m for n,s in plug.items()})
LNV_TARGETS.update({'fixed_wire_'+n:s['m'] for n,s in fixed.items()})
LNV_BOXES={n:np.array(m.bounding_box()) for n,m in LNV_TARGETS.items()}
LNV_STARTED=time.time()
LNV_DIMS=np.array([1.,1.8,4.1]);LNV_PAD=.31
sp=manifold.Manifold.sphere(LNV_PAD,48);sm=sp.to_mesh64();vs=np.asarray(sm.vert_properties[:,:3]);fs=np.asarray(sm.tri_verts)
a,b,c=vs[fs[:,0]],vs[fs[:,1]],vs[fs[:,2]];norm=np.cross(b-a,c-a)
inner=float(np.min(np.abs(np.einsum('ij,ij->i',a,norm))/np.linalg.norm(norm,axis=1)))
path=np.load(LNV_OUT/'lower_bend/selected_path.npz')['radial_z_axis_angle']
da=float(np.max(np.abs(np.diff(path[:,2]))))
contact_error=(10.+LNV_DIMS[2]+np.linalg.norm(LNV_DIMS[:2]/2)+LNV_PAD)*da**2/8+1e-6
wire_error=10.*da**2/8+1e-6
contact_bound=inner-contact_error
wire_bound=inner/LNV_PAD*.64-wire_error-.3302
assert min(contact_bound,wire_bound)>.3
contact_template=manifold.Manifold.cube(LNV_DIMS.tolist(),center=True).minkowski_sum(sp)
wire_sphere=manifold.Manifold.sphere(.64,48)
def lnv_hits(m):
    bb=np.array(m.bounding_box());hits=[]
    for name,target in LNV_TARGETS.items():
        box=LNV_BOXES[name]
        if np.any(bb[:3]>box[3:]) or np.any(box[:3]>bb[3:]):continue
        volume=max(0.,float((m^target).volume()))
        if volume>1e-5:hits.append(dict(obstacle=name,intersection_mm3=volume))
    return hits
rows=[];contact_shapes={};wire_shapes={};curves=np.load(LNV_OUT/'wire_relaxation_curves.npz')
for phase in (45,135,225,315):
    phi=math.radians(phase);er=np.array([math.cos(phi),math.sin(phi),0.]);ez=np.array([0.,0.,1.]);et=np.cross(ez,er)
    ts=[]
    for r,z,ang in path:
        axis=er*math.sin(ang)+ez*math.cos(ang);x=er*math.cos(ang)-ez*math.sin(ang)
        ts.append(np.column_stack([x,et,axis,r*er+z*ez+axis*LNV_DIMS[2]/2]))
    instances=[contact_template.transform(t) for t in ts];spans=[];i=0
    while i<len(ts)-1:
        j=i+1
        while j+1<len(ts) and np.max(np.abs(ts[j+1][:,:3]-ts[i][:,:3]))<1e-12:
            if np.linalg.norm(np.cross(ts[j+1][:,3]-ts[i][:,3],ts[j][:,3]-ts[i][:,3]))>1e-9:break
            j+=1
        spans.append((i,j));i=j
    contact=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([instances[i],instances[j]]) for i,j in spans],manifold.OpType.Add)
    new=curves['phase'+str(phase)+'_new'];old=curves['phase'+str(phase)+'_old']
    wire=manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([wire_sphere.translate(p.tolist()) for p in (new[i],new[j],old[i],old[j])]) for i,j in spans],manifold.OpType.Add)
    ch=lnv_hits(contact);wh=lnv_hits(wire)
    contact_shapes[phase]=contact;wire_shapes[phase]=wire
    row=dict(phase_deg=phase,status='PASS' if not ch and not wh else 'BLOCKED',spans=len(spans),contact_hits=ch,wire_relaxation_hits=wh)
    rows.append(row);print('LARGER_NECK_RELOAD',row,flush=True)
pair_rows=[]
phases=(45,135,225,315)
for i,a in enumerate(phases):
    for b in phases[i+1:]:
        overlaps={k:max(0.,float((x^y).volume())) for k,x,y in [
            ('contact_contact',contact_shapes[a],contact_shapes[b]),('wire_wire',wire_shapes[a],wire_shapes[b]),
            ('contact_a_wire_b',contact_shapes[a],wire_shapes[b]),('contact_b_wire_a',contact_shapes[b],wire_shapes[a])]}
        pair_rows.append(dict(phases=[a,b],status='PASS' if max(overlaps.values())<=1e-5 else 'BLOCKED',padded_overlap_mm3=overlaps))

# Measure radial journal material before/after without inventing a strength
# acceptance threshold. All sampled stations and unavailable rays are kept.
wall_helper=LNV_A8/'inspect_coupled_feed_sections.py'
code='def ray_material_intervals'+wall_helper.read_text().split('def ray_material_intervals',1)[1].split('\nbearing=',1)[0]
exec(compile(code,str(wall_helper),'exec'),globals())
raw=np.load(LNV_OUT/'Pitch_Yoke_before.npz');wall_before=manifold.Manifold(manifold.Mesh64(raw['vertices_mm'],raw['triangles'].astype(np.uint64)))
journal_r=P['head_axial_retention']['bearing']['trial_journal_d_mm']/2
bearing_bounds=np.asarray(LNV_SOURCE['Yaw_Bearing'].bounding_box());zs=np.linspace(bearing_bounds[2]+.5,bearing_bounds[5]-.25,17)
walls={}
for tag,m in [('before',wall_before),('candidate',LNV_SOURCE['Pitch_Yoke'])]:
    wall_rows=[];missing=[]
    for z in zs:
        polygons=[np.asarray(p) for p in m.slice(float(z)).to_polygons()]
        for degree in np.arange(.125,360,.5):
            bands=ray_material_intervals(polygons,math.radians(float(degree)))
            material=[] if bands is None else [(a,min(b,journal_r)) for a,b in bands if a<journal_r and b>journal_r-.02]
            if len(material)!=1:missing.append(dict(z_mm=float(z),angle_deg=float(degree),material=bands));continue
            a,b=material[0];wall_rows.append(dict(z_mm=float(z),angle_deg=float(degree),inner_radius_mm=a,outer_radius_mm=b,thickness_mm=b-a))
    walls[tag]=dict(sampled_rays=len(zs)*720,valid_rays=len(wall_rows),missing=missing,minimum=min(wall_rows,key=lambda r:r['thickness_mm']))

section_layers={n:LNV_SOURCE[n] for n in ('Yaw_Base','Pitch_Yoke','Yaw_Reaction_Link','Yaw_Bearing')}
for n in ('Yaw_Base','Pitch_Yoke'):
    a=np.load(LNV_OUT/(n+'_before.npz'))
    section_layers[n+'_before']=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
    section_layers[n+'_removed']=section_layers[n+'_before']-section_layers[n]
q=math.sqrt(.5);radial=np.array([[q,q,0.,0.],[0.,0.,1.,0.],[-q,q,0.,0.]])
sections={'radial45':{n:[p.tolist() for p in m.transform(radial).slice(0.).to_polygons()] for n,m in section_layers.items()}}
for z in (145.,152.5,188.):
    sections['Z'+str(z)]={n:[p.tolist() for p in m.slice(z).to_polygons()] for n,m in section_layers.items()}
(LNV_OUT/'verified_sections.json').write_text(json.dumps(sections,ensure_ascii=False,indent=2)+'\n')

report=dict(status='PASS' if all(r['status']=='PASS' for r in rows+pair_rows) and all(v['status']=='PASS' for v in LNV_TOPOLOGY.values()) else 'BLOCKED',
    scope='Reloaded candidate topology plus bounded continuous terminal, neck-wire and mutual-clearance sweeps; no complete supply or assembly approval',
    script_sha256=sha(LNV_SCRIPT),source_builder_sha256=LNV_BUILD['script_sha256'],audit_helper_sha256=sha(LNV_AUDIT_HELPER),wall_helper_sha256=sha(wall_helper),
    source_main_sha256=source_hash,source_candidate_sha256=LNV_HASH,source_construction_sha256=sha(LNV_OUT/'construction.json'),
    protected_sources=LNV_BUILD['protected_sources'],source_objects=len(LNV_SOURCE),mating_allocations=len(plug),fixed_wires=len(fixed),
    contact_dimensions_mm=LNV_DIMS.tolist(),contact_evidence='ASSUMED requested space; not manufacturer post-crimp maximum',
    clearance_requirement_mm=.3,contact_padding_mm=LNV_PAD,contact_gap_lower_bound_mm=contact_bound,
    wire_gap_lower_bound_mm=wire_bound,minimum_wire_bend_radius_mm=8.,required_wire_bend_radius_mm=REQUIRED_R,
    topology=LNV_TOPOLOGY,rows=rows,pair_rows=pair_rows,finite_journal_wall_samples=walls,
    verified_sections_sha256=sha(LNV_OUT/'verified_sections.json'),
    wall_scope='17 axial planes x720 radial rays in bearing journal land; no all-part minimum wall or strength certification',
    actual_terminal_fit='NOT_TESTED',complete_wire_material_and_body_connector='NOT_TESTED',
    full_assembly_sequence='NOT_TESTED',strength='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-LNV_STARTED)
report['storage_receipt_sha256']=sha(LNV_OUT/'cleaned/storage.json') if LNV_INPUT.parent.name=='cleaned' else None
(LNV_OUT/('verification.json' if LNV_INPUT.parent.name=='cleaned' else 'verification_raw.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(LNV_INPUT)==LNV_HASH and all(sha(PROJECT/p)==h for p,h in report['protected_sources'].items())
print('LARGER_NECK_VERIFY_DONE',report['status'],{k:v['status'] for k,v in LNV_TOPOLOGY.items()},
      {k:v['minimum']['thickness_mm'] for k,v in walls.items()},round(time.time()-LNV_STARTED,2),flush=True)
