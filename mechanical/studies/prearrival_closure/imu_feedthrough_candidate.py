"""Unapplied option: one purposeful cable opening beside the carrier PCB."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Reuse the immutable-source routing primitives without running their batch.
exec(compile((HERE/'harness_routes.py').read_text().split('specs=[')[0],str(HERE/'harness_routes.py'),'exec'))
from render import camera
original=ss['Load_Frame'];o=clone(original.o,'CLOSURE_Load_Frame_Candidate')
cx,cy,width,length=41.,-37.,6.8,12.
cut=manifold.Manifold.cylinder(20,width/2,width/2,64).translate((cx,cy-(length-width)/2,105))+manifold.Manifold.cylinder(20,width/2,width/2,64).translate((cx,cy+(length-width)/2,105))+manifold.Manifold.cube((width,length-width,20)).translate((cx-width/2,cy-(length-width)/2,105))
m=original.m-cut;q=m.to_mesh();me=bpy.data.meshes.new(PREFIX+'CLOSURE_Frame_Data');me.from_pydata(q.vert_properties[:,:3].tolist(),[],q.tri_verts.tolist());me.update();o.data=me;o.matrix_world=Matrix.Identity(4)
candidate=Solid(o);ss['Load_Frame']=candidate;obstacles['Load_Frame']=candidate;trees['Load_Frame']=candidate.bvh();los=np.array([obstacles[n].lo for n in obs]);his=np.array([obstacles[n].hi for n in obs])
unrelated=[]
for n,s in ss.items():
    if n=='Load_Frame':continue
    if np.any(np.array(cut.bounding_box())[3:]<s.lo)or np.any(s.hi<np.array(cut.bounding_box())[:3]):continue
    v=max(0,(cut^s.m).volume())
    if v>.01:unrelated.append(dict(part=n,volume_mm3=v))
r=2.5;R=8.;exa,a,aa=endpoint('motion_J4',r);exb,b,ab=endpoint('imu_J1',r)
raw,stats=solve(a,b,r+.3);curve=None;controls_used=None
if raw:
    curve=rounded(raw,R)
    if curve is None or not all(free(p,r+.3) for p in resample(curve,.5)):curve=None
for ztop,zbottom,ybottom in itertools.product([141,142,143,144,145,146],[84,85,86,87],[cy,b[1],-40]):
    if curve is not None:break
    controls=[a,np.array([a[0],a[1],ztop]),np.array([cx,cy,ztop]),np.array([cx,cy,zbottom]),np.array([b[0],ybottom,zbottom]),b]
    test=rounded(controls,R)
    if test is not None and all(free(p,r+.3) for p in resample(test,.5)):
        if all(line_free(p,q,r+.3) for p,q in zip(test,test[1:])):curve=test;controls_used=controls
if curve is None and raw:curve=relax(raw,r+.3,R)
hs=solid_hits(curve,r) if curve else None
out=dict(status='PASS' if curve is not None and not hs and not unrelated else 'BLOCKED',adopted=False,opening_xy_mm=[cx,cy],opening_width_length_mm=[width,length],removed_volume_mm3=(original.m-m).volume(),connected_solids=len(m.decompose()),other_part_overlap=unrelated,search=stats,raw_path_mm=[p.tolist() for p in raw] if raw else None,curve_mm=[p.tolist() for p in curve] if curve else None,control_points_mm=[p.tolist() for p in controls_used] if controls_used else None,route_hits=hs,scope='Candidate only. Nominal diameter5mm cable and8mm bends; actual cable/plug fanout and strength unqualified. Approval required before altering Load_Frame.')
(HERE/'imu_feedthrough_candidate.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('CANDIDATE',out['status'],'REMOVED',out['removed_volume_mm3'],'OTHER',unrelated,'CURVE',curve is not None,flush=True)
# Save as a separate review, preserving main model and unowned objects.
original.o.hide_render=True;original.o.hide_set(True)
for x in bpy.context.scene.objects:
    if x.type=='MESH':x.hide_render=True
for n in ['Load_Frame','MCU_Carrier','Body_IMU']:
    x=ss[n].o;x.hide_render=False;x.color=(.7,.73,.75,1) if n=='Load_Frame' else (.08,.32,.25,1)
if curve:
    for i,(a,b) in enumerate(zip(curve,curve[1:])):
        mid=(a+b)/2;obj=cyl('CLOSURE_IMU_Path_'+str(i),mid,r,float(np.linalg.norm(b-a)),n=16);obj.rotation_euler=Vector(b-a).to_track_quat('Z','Y').to_euler();obj.color=(1,.45,.06,1);obj.hide_render=False;obj['role']='routing_review'
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='OBJECT';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True
sc.render.resolution_x=1150;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
camera('closure_imu',(150,-220,235),(0,-34,111),118);sc.render.filepath=str(HERE/'imu_feedthrough_candidate.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'imu_feedthrough_candidate.blend'))
