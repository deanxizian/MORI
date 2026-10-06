"""Read-only sections through the real joint and two unapproved lower cuts."""
from pathlib import Path
SCRIPT=Path(__file__).resolve()
HELPER=SCRIPT.parent.parent/'head_harness/check_outer_neck_probes.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('# Endpoints are named')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
assert len(ss)==209 and before=='bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
def load_mesh(path):
    d=np.load(path)
    return manifold.Manifold(manifold.Mesh64(vert_properties=d['vertices_mm'],tri_verts=d['triangles'].astype(np.uint64)))
meshes={}
for name,s in ss.items():
    if s.hi[2]>135 and s.lo[2]<211 and s.lo[0]<30 and s.hi[0]>-30 and s.lo[1]<30 and s.hi[1]>-30:
        meshes[name]=s.m
        print('LOCAL_OBJECT',name,s.group,s.lo.round(3).tolist(),s.hi.round(3).tolist(),flush=True)
extra={}
for label,folder in [('lower_C1','lower_entry_candidate'),('lower_C2','lower_entry_open_candidate')]:
    extra[label]=load_mesh(OUT/folder/'Yaw_Base_candidate.npz')
extra['upper_pose_union']=load_mesh(OUT/'central_yaw_obstacle_union.npz')
layers={**meshes,**extra};sections={}
for deg in [0,45,90,135]:
    a=math.radians(deg)
    tr=np.array([[0,0,1,0],[math.cos(a),math.sin(a),0,0],[-math.sin(a),math.cos(a),0,0]])
    sections[str(deg)]={name:[np.array(p)[:,[1,0]].tolist() for p in m.transform(tr).slice(0).to_polygons()]
                        for name,m in layers.items()}
report=dict(source_blend_sha256=before,scope='Radial sections for review; not a strength or whole-harness result',
    coordinates='horizontal signed radial mm; vertical world Z mm',sections=sections,
    objects={n:dict(group=ss[n].group,lo=ss[n].lo.tolist(),hi=ss[n].hi.tolist()) for n in meshes},
    main_geometry_changed=False)
(OUT/'route_sections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('ROUTE_SECTIONS_SAVED',flush=True)
