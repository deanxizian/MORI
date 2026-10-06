"""Verify the saved, independent camera-pocket candidate against current main.

Only the pocket's upper outside edge may lose material. This is nominal CAD
evidence, not camera metrology, print strength, or manufacturing release.
"""
import sys, json, hashlib, time
from pathlib import Path
SCRIPT=Path(__file__).resolve(); OUT=SCRIPT.parent; PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from export import topology
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
construction=json.loads((OUT/'construction.json').read_text())
protected=construction['protected_sources']; started=time.time()
assert all(sha(PROJECT/p)==h for p,h in protected.items())
assert sha(OUT/'candidate.blend')==construction['candidate_sha256']

def evaluate():
    load_collections()
    for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[c].hide_viewport=False
    assembled();bpy.context.view_layer.update()
    return {o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}

# Input CLI file is the unmodified main. Cache its world solids before opening
# the independently saved candidate, so comparisons do not depend on reports.
assert Path(bpy.data.filepath).resolve()==(PROJECT/'mechanical/mori_v1_2.blend').resolve()
source_objects=evaluate(); source_records={n:geometry_record(o) for n,o in source_objects.items()}
old=Solid(source_objects['Display_Frame']).m
raw=old.to_mesh64();np.savez_compressed(OUT/'original_Display_Frame.npz',vertices_mm=raw.vert_properties[:,:3],triangles=raw.tri_verts)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'candidate.blend'))
objects=evaluate();records={n:geometry_record(o) for n,o in objects.items()}
assert len(objects)==209 and set(records)==set(source_records)
changed=sorted(n for n in records if records[n]!=source_records[n]);assert changed==['Display_Frame'],changed
ss={n:Solid(o) for n,o in objects.items()};solids={n:s.m for n,s in ss.items()}
frame=solids['Display_Frame']; shell=solids['Head_Front']
npz=np.load(OUT/'Display_Frame.npz')
exact=manifold.Manifold(manifold.Mesh64(np.array(npz['vertices_mm'],copy=True),np.array(npz['triangles'],dtype=np.uint64,copy=True)))
delta=(frame-exact).volume()+(exact-frame).volume()
assert 0<=delta<.003,delta  # saved float32 mesh volume difference, reported below
assert max(0.,(exact-old).volume())<1e-7
gap=float(frame.min_gap(shell,1.));overlap=max(0.,float((frame^shell).volume()))
assert gap>=.3 and overlap<1e-7
topo=topology(ss['Display_Frame'].v,ss['Display_Frame'].f.tolist())
topo['connected_solid_components']=len(frame.decompose())
topo['status']='PASS' if all(topo[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles']) and topo['signed_volume_mm3']>0 and topo['connected_solid_components']==1 else 'FAIL'
assert topo['status']=='PASS',topo

rc=np.array(construction['camera_local_basis_columns']); pupil=np.array(construction['camera_pupil_world_mm'])
wall=[]
# Evaluate thickness in float64 camera coordinates. mathutils BVH ray hits are
# float32 world coordinates at Z~272 mm and lose several 1e-5 mm here.
local_v=(ss['Display_Frame'].v-pupil)@np.linalg.inv(rc).T
tri=local_v[ss['Display_Frame'].f]
edge1=tri[:,1,:]-tri[:,0,:];edge2=tri[:,2,:]-tri[:,0,:]
det=edge1[:,0]*edge2[:,2]-edge1[:,2]*edge2[:,0]
valid=abs(det)>1e-12
numeric_wall_tol=2*float(np.spacing(np.float32(abs(ss['Display_Frame'].v).max())))
for x in [-4.,-2.,0.,2.,4.]:
    for w in [-4.,-3.,-2.,-1.1]:
        dx=x-tri[:,0,0];dw=w-tri[:,0,2]
        u=np.zeros(len(tri));v=np.zeros(len(tri))
        u[valid]=(dx[valid]*edge2[valid,2]-dw[valid]*edge2[valid,0])/det[valid]
        v[valid]=(edge1[valid,0]*dw[valid]-edge1[valid,2]*dx[valid])/det[valid]
        hit=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
        levels=sorted(tri[hit,0,1]+u[hit]*edge1[hit,1]+v[hit]*edge2[hit,1])
        unique=[]
        for level in levels:
            if not unique or level-unique[-1]>1e-5:unique.append(float(level))
        assert len(unique)>=2,unique
        thick=unique[1]-unique[0]
        wall.append(dict(x_mm=x,w_mm=w,thickness_mm=thick))
assert all(abs(r['thickness_mm']-1.2)<numeric_wall_tol for r in wall),wall

def hits(m,ids,tol=1e-5):
    bb=np.array(m.bounding_box());out=[]
    for n in sorted(ids):
        a=ss[n]
        if np.any(bb[3:]<a.lo) or np.any(bb[:3]>a.hi):continue
        v=max(0.,float((m^a.m).volume()))
        if v>tol:out.append(dict(part=n,volume_mm3=v))
    return out

cm=solids['Camera_PCB']+solids['Camera_Lens']
capture=[]
for axis in range(3):
    for sign in [-1,1]:
        contacts=hits(cm.translate((rc[:,axis]*sign*.5).tolist()),['Display_Frame','Head_Front'])
        capture.append(dict(local_axis=axis,sign=sign,displacement_mm=.5,contacts=contacts))
assert all(r['contacts'] for r in capture),capture

# Reuse named stage membership, not the candidate's earlier geometry results.
stage_path=PROJECT/'mechanical/studies/prearrival_finish/harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/split_assembly/pitch_stages/screen.json'
stages=json.loads(stage_path.read_text())
rows=[]
for stage in ['optical_frame_front_entry','camera_along_optical_axis','head_front_shell']:
    source=next(r for r in stages['rows'] if r['stage']==stage)
    moving=set(sum(source['moving'],[])) if isinstance(source['moving'][0],list) else set(source['moving'])
    fixed=set(source['fixed']);assert moving|fixed<=set(objects)
    m=manifold.Manifold.batch_boolean([solids[n] for n in sorted(moving)],manifold.OpType.Add)
    if stage=='camera_along_optical_axis':distance=24.;direction=np.array([0,1,math.tan(math.radians(10))])
    else:distance=70. if stage=='optical_frame_front_entry' else 68.;direction=np.array([0,1,0])
    failures=[];samples=np.arange(0,distance+.01,.5)
    for d in samples:
        h=hits(m.translate((direction*d).tolist()),fixed)
        if h:failures.append(dict(distance_mm=float(d),hits=h))
    row=dict(stage=stage,status='PASS' if not failures else 'BLOCKED',samples=len(samples),step_mm=.5,
             moving=sorted(moving),fixed=sorted(fixed),deferred=sorted(set(objects)-moving-fixed),failures=failures)
    rows.append(row);print('CAMERA_TOP_PATH',stage,row['status'],len(failures),flush=True)

# A strict positive-distance bound can cover the complete shell/changed-frame
# translation, without mistaking coarse samples for a continuous proof.
intervals=[];pending=[(0.,68.)];unresolved=[]
while pending:
    a,b=pending.pop();mid=(a+b)/2
    d=float(shell.translate([0,mid,0]).min_gap(frame,100.))
    lower=d-(b-a)/2
    if lower>1e-5:
        intervals.append(dict(start_mm=a,end_mm=b,mid_gap_mm=d,gap_lower_bound_mm=lower))
    elif b-a>.001:
        pending.extend([(a,mid),(mid,b)])
    else:unresolved.append(dict(start_mm=a,end_mm=b,mid_gap_mm=d))
    assert len(intervals)+len(pending)+len(unresolved)<20000
continuous=dict(status='PASS' if not unresolved else 'BLOCKED',scope='Head_Front vs changed Display_Frame only, translation +Y 0..68 mm; other pairs remain finite samples',
    method='Distance is 1-Lipschitz under translation; midpoint gap minus half interval length bounds every intervening position',
    interval_count=len(intervals),minimum_certified_gap_mm=min((r['gap_lower_bound_mm'] for r in intervals),default=0),
    intervals=sorted(intervals,key=lambda r:r['start_mm']),unresolved=unresolved)
print('CAMERA_TOP_CONTINUOUS',continuous['status'],len(intervals),flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rows) and continuous['status']=='PASS' else 'BLOCKED',
    scope='Saved candidate mesh, unchanged datums, local upper wall, nominal capture, named assembly stages, and continuous shell/changed-frame path',
    protected_sources=protected,source_objects=209,changed_source_objects=changed,unchanged_source_objects=208,
    script_sha256=sha(SCRIPT),construction_sha256=sha(OUT/'construction.json'),candidate_sha256=sha(OUT/'candidate.blend'),
    original_mesh_sha256=sha(OUT/'original_Display_Frame.npz'),stage_membership_source_sha256=sha(stage_path),
    saved_vs_exact_symmetric_difference_mm3=float(delta),saved_shell_gap_mm=gap,saved_shell_overlap_mm3=overlap,topology=topo,
    sampled_upper_wall=dict(count=len(wall),min_mm=min(r['thickness_mm'] for r in wall),max_mm=max(r['thickness_mm'] for r in wall),rows=wall,numeric_tolerance_mm=numeric_wall_tol,numeric_tolerance_basis='Two float32 ULP at saved world-coordinate magnitude, not manufacturing tolerance'),
    capture=capture,paths=rows,continuous_shell_frame_path=continuous,
    nonexpansion_proof='Exact candidate is a subset of the original Display_Frame; unchanged transforms and all other geometry mean material removal cannot introduce rigid collision at any common pose. This does not close other pre-existing interfaces.',
    original_and_saved_fov='Head shell and camera unchanged; frame material only removed, so it cannot newly obstruct original sight rays',
    actual_camera_dimensions='ASSUMED_PHOTO_REFERENCE',print_strength='NOT_TESTED',physical_fit='NOT_TESTED',full_harness='BLOCKED',
    main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAMERA_TOP_VERIFIED',report['status'],report['elapsed_s'],flush=True)
