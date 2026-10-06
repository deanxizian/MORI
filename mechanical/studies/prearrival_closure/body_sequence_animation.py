"""Supplemental editable presentation of the collision-screened body sequence.

Uses an independent P5R7 receipt candidate. No primary files are saved.
Animation is rigid geometry only; no harness, manual support or tightening.
"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
exec(compile((HERE/'rigid_assembly_paths.py').read_text().split('# Parts are handled')[0],str(HERE/'rigid_assembly_paths.py'),'exec'))
from render import camera
from assembly_animation import curves
from mathutils import Matrix,Vector
source_file=Path(bpy.data.filepath);source_hash=hashlib.sha256(source_file.read_bytes()).hexdigest()
upper=set(json.loads((PROJECT/'mechanical/reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']['moving'])
bridge={'Yaw_Base','Yaw_Bearing','Yaw_Base_-1_Nut','Yaw_Base_1_Nut'}
bolts={'Yaw_Base_-1_Screw','Yaw_Base_1_Screw'}
shown=core|drive|upper|bridge|bolts
# Objects are already in project millimeters; unit scale is for UI display only.
sc=bpy.context.scene;sc.animation_data_clear()
for o in sc.objects:
    o.animation_data_clear()
    if o.type=='MESH':o.hide_render=True;o.hide_set(True)
base={n:s.o.matrix_world.copy() for n,s in ss.items()}
for n in shown:
    ss[n].o.hide_render=False;ss[n].o.hide_set(False)
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.color_type='MATERIAL';sc.display.shading.light='STUDIO';sc.display.shading.show_cavity=True
sc.render.resolution_x=960;sc.render.resolution_y=720;sc.render.resolution_percentage=100;sc.render.fps=24
sc.frame_start=1;sc.frame_end=240
sc['presentation_only']=True;sc['source_candidate_sha256']=source_hash
sc['limits']='Rigid partial body assembly only; shell and bridge need independent support, cables and hand/tool motions not animated. Core E fit and head horn remain BLOCKED. Main M1.43 is unchanged.'
origin=Vector((0,0,D['body_z']))
def uptr(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
def insertkeys(n,f,tr):
    o=ss[n].o;o.matrix_world=tr@base[n];o.keyframe_insert(data_path='location',frame=f);o.keyframe_insert(data_path='rotation_euler',frame=f)
keys=[(1,15,-14,90,94),(70,15,-14,14,18),(100,15,0,14,18),(135,15,0,14,0),(185,15,0,14,0)]
# Dense final angular keys preserve rotation about the body datum instead of
# interpolating object origins along unrelated straight chords.
for f in range(186,226):
    u=(f-185)/40;keys.append((f,15*(1-u),0,14*(1-u),0))
keys.append((240,0,0,0,0))
for f,a,y,z,bz in keys:
    for n in upper:insertkeys(n,f,uptr(a,y,z))
    for n in bridge:insertkeys(n,f,Matrix.Translation((0,y,bz)))
for n in bolts:
    row=next(q for q in json.loads((HERE/'assembly_preflight.json').read_text())['fasteners'] if q['id']==n)
    axis=Vector(row['axis'])
    for f,d in [(1,25),(145,25),(172,0),(240,0)]:insertkeys(n,f,Matrix.Translation(axis*d))
for n in shown:
    for fc in curves(ss[n].o):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
for m in list(sc.timeline_markers):sc.timeline_markers.remove(m)
for f,label in [(1,'上壳倾15°，桥水平；分别托住'),(70,'到预装高度，向前移14mm'),(100,'壳不动，桥单独下降18mm'),(145,'装入两枚M3；此段预留锁紧时间'),(185,'桥已固定，上壳回正落位'),(225,'仅刚体顺序；线束/握持待验证')]:sc.timeline_markers.new(label,frame=f)
camera('body_sequence_animation',(285,-365,310),(0,-5,145),390)
bm=bpy.data.materials.new('MORI__BODY_ORDER_BRIDGE_COLOR');bm.diffuse_color=(.82,.40,.06,1)
ss['Yaw_Base'].o.data.materials.clear();ss['Yaw_Base'].o.data.materials.append(bm)
for face in ss['Yaw_Base'].o.data.polygons:face.material_index=0
sc.frame_set(135);sc.render.image_settings.media_type='IMAGE';sc.render.image_settings.file_format='PNG';sc.render.filepath=str(HERE/'body_sequence_poster.png');bpy.ops.render.render(write_still=True)
# Verify keyed poses reproduce their nominal rigid transform to numerical tolerance.
errors=[]
for f,a,y,z,bz in keys:
    sc.frame_set(f);bpy.context.view_layer.update()
    for n in upper|bridge:
        expected=(uptr(a,y,z) if n in upper else Matrix.Translation((0,y,bz)))@base[n]
        errors.append(max(abs(ss[n].o.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4)))
assert max(errors)<.0001,max(errors)
sc.frame_set(1);sc.render.image_settings.media_type='VIDEO';sc.render.image_settings.file_format='FFMPEG';sc.render.ffmpeg.format='MPEG4';sc.render.ffmpeg.codec='H264';sc.render.ffmpeg.constant_rate_factor='MEDIUM';sc.render.ffmpeg.ffmpeg_preset='REALTIME';sc.render.ffmpeg.gopsize=24;sc.render.filepath=str(HERE/'body_sequence.mp4')
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'body_sequence_animation.blend'))
bpy.ops.render.render(animation=True)
out=dict(candidate_source_sha256=source_hash,source=str(source_file),frames=240,fps=24,duration_seconds=10,resolution=[960,720],maximum_key_transform_error_mm=max(errors),rigid_only=True,full_robot_animation_updated=False,source_report='p5r7_receipt/dual_body_sequence.json',notes=sc['limits'])
(HERE/'body_sequence_animation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('BODY_SEQUENCE_ANIMATION_COMPLETE',out,flush=True)
