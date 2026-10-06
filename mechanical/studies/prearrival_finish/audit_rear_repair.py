"""Compare M1.46 with immutable M1.45; verify actual exported rear shell."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
from export import topology
from mathutils.bvhtree import BVHTree

def digest(o):
    o.data.calc_loop_triangles()
    v=np.array([tuple(x) for x in vertices_world(o)],dtype=np.float64)
    f=np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.uint64)
    return hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest(),v,f

load_collections();assembled();bpy.context.view_layer.update()
current={o.name:o for o in parts()}
now={n:digest(o) for n,o in current.items()}
baseline=HERE/'baseline_M1_45/mechanical/mori_v1_2.blend'
with bpy.data.libraries.load(str(baseline),link=False) as (src,dst):
    dst.objects=list(current)
old={n:o for n,o in zip(current,dst.objects)}
changed=[];presentation=[]
for n,o in old.items():
    bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
before={n:digest(o) for n,o in old.items()}
for n in current:
    if now[n][0]!=before[n][0]:
        if current[n].get('group')=='dock':
            # The standalone maintenance cradle has a presentation offset in
            # saved previews. Compare its local physical mesh separately.
            a=current[n].data;b=old[n].data;a.calc_loop_triangles();b.calc_loop_triangles()
            av=np.array([tuple(v.co) for v in a.vertices]);bv=np.array([tuple(v.co) for v in b.vertices])
            af=np.array([tuple(t.vertices) for t in a.loop_triangles]);bf=np.array([tuple(t.vertices) for t in b.loop_triangles])
            presentation.append(dict(id=n.removeprefix(PREFIX),local_mesh_identical=np.array_equal(av,bv) and np.array_equal(af,bf)))
        else:changed.append(n.removeprefix(PREFIX))
n=PREFIX+'Head_Rear';_,v,f=now[n];_,ov,of=before[n]
trees=[BVHTree.FromPolygons([Vector(x) for x in vv],ff.tolist(),all_triangles=True) for vv,ff in [(v,f),(ov,of)]]
distances=[]
q=P['interface_completion']['head_seam']
def in_seam_region(p):
    return any((p[0]-sign*x)**2+(p[2]-D['head_z']-z)**2<(q['lug_radius_mm']+.02)**2
        for sign in [-1,1] for x,z in [(q['old_abs_x_mm'],q['old_z_from_head_mm']),(q['abs_x_mm'],q['z_from_head_mm'])])
for vv,ff,tree in [(v,f,trees[1]),(ov,of,trees[0])]:
    points=np.r_[vv,vv[ff].mean(axis=1)]
    ds=np.array([tree.find_nearest(Vector(p))[3] for p in points])
    outside=np.array([not in_seam_region(p) for p in points])
    distances.append(dict(samples=len(points),max_mm=float(ds.max()),p99_mm=float(np.percentile(ds,99)),
                          max_at_mm=points[int(np.argmax(ds))].tolist(),outside_seam_max_mm=float(ds[outside].max()),
                          outside_seam_samples=int(outside.sum())))
sm=Solid(current[n]).m;bm=Solid(old[n]).m
from interface_completion import axial
region=manifold.Manifold()
for sign in [-1,1]:
    for x,z in [(q['old_abs_x_mm'],q['old_z_from_head_mm']),(q['abs_x_mm'],q['z_from_head_mm'])]:
        region+=axial(q['lug_radius_mm']+.02,90,[sign*x,-10,D['head_z']+z],[0,1,0])
removed=bm-sm;added=sm-bm
outside_volume=max(0,(removed-region).volume())+max(0,(added-region).volume())
source_hash=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()
manifest=json.loads((ROOT/'reports/export_manifest.json').read_text())
rear=next(r for r in manifest['parts'] if r['id']=='Head_Rear')
old_config=json.loads((HERE/'baseline_M1_45/config/geometry.json').read_text())
copy=json.loads(json.dumps(P));copy['revision']=old_config['revision'];copy['interface_completion']['head_seam'].pop('rebuild_rear_from_nominal_shell')
later=set(P.get('prearrival_thin_cleanup',{}).get('changed_existing_ids',[]))
if later:
    copy.pop('prearrival_thin_cleanup')
    prior_config=json.loads((PROJECT/Path(P['prearrival_thin_cleanup']['baseline_blend']).parents[1]/'config/geometry.json').read_text())
    copy['drive_print_cleanup']['bearing_bar_depth_mm']=prior_config['drive_print_cleanup']['bearing_bar_depth_mm']
if P.get('camera_cam_completion',{}).get('enabled'):
    later |= declared_camera_cam_changes()
    copy.pop('camera_cam_completion')
if P.get('neck_harness_capacity',{}).get('enabled'):
    later |= declared_neck_capacity_changes()
    copy.pop('neck_harness_capacity')
    before_neck=json.loads((PROJECT/Path(P['neck_harness_capacity']['baseline_blend']).parents[1]/'config/geometry.json').read_text())
    copy['head_joint']['yaw_vertical_rule']=before_neck['head_joint']['yaw_vertical_rule']
if P.get('waveshare_detail',{}).get('entry_correction',{}).get('enabled'):
    later |= declared_cam_entry_changes()
    copy['waveshare_detail'].pop('entry_correction')
checks=dict(only_rear_and_declared_later_changes=set(changed)=={'Head_Rear'}|later,all_other_parameters_unchanged=copy==old_config,
            cradle_physical_mesh_unchanged=all(x['local_mesh_identical'] for x in presentation),
            closed_stl=rear['status']=='PASS',all_exports_pass=manifest['exported_count']==manifest['candidate_count'],
            actual_blender_stl_reimport=rear['blender_reimport']['status']=='PASS',
            outside_seam_surface_deviation_under_002_mm=max(r['outside_seam_max_mm'] for r in distances)<.02,
            outside_seam_symmetric_difference_under_002_mm3=outside_volume<.02,
            nominal_bounds_unchanged=bool(np.max(np.abs(np.r_[v.min(0),v.max(0)]-np.r_[ov.min(0),ov.max(0)]))<.0001))
out=dict(revision=P['revision'],source_blend_sha256=source_hash,status='PASS' if all(checks.values()) else 'FAIL',
         checks=checks,parts_compared=len(current),changed=changed,presentation_only_dock_changes=presentation,
         sampled_surface_distance=distances,outside_seam_symmetric_difference_mm3=outside_volume,
         removed_volume_mm3=max(0,(bm-sm).volume()),added_volume_mm3=max(0,(sm-bm).volume()),
         final_stl=rear,limits=['Surface deviation samples are not a mathematical Hausdorff proof.',
         'Old seam-cylinder restoration left nearly zero-thickness fragments up to2.55mm from the intended solid surface. Those fragments are removed inside the old/current seam regions; their distance is reported, not hidden as a passing global surface tolerance.',
         'No nominal hole, wall, actuator or board datum changed. Only the same rear shell construction was replaced.',
         'Topology/export PASS is not print strength or manufacturing release.'])
(HERE/'rear_repair_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='final_stl'},ensure_ascii=False,indent=2),flush=True)
if not all(checks.values()):raise RuntimeError('Rear repair scope/geometry audit failed')
