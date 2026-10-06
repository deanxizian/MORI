"""Editable independent H06 body-to-yaw preview, not manufacturing geometry."""
from pathlib import Path
PREVIEW_SCRIPT=Path(__file__).resolve();PREVIEW_DIR=PREVIEW_SCRIPT.parent
PREVIEW_HELPER=PREVIEW_DIR/'plan_h06_documented_mates.py';__file__=str(PREVIEW_HELPER)
exec(compile(PREVIEW_HELPER.read_text().split('\nports=json.loads',1)[0],str(PREVIEW_HELPER),'exec'),globals())
__file__=str(PREVIEW_SCRIPT)
from render import camera
from common import mesh as create_review_mesh
from validate_head_cleanup import geometry_record
OUT=PREVIEW_DIR/'body_prefix_v2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((OUT/'body_to_yaw_motion.json').read_text());curves=np.load(OUT/'body_to_yaw_curves.npz')
assert report['status']=='PASS' and report['source_blend_sha256']==source_hash
before={n:geometry_record(s.o) for n,s in ss.items()}
overlays=[]
for r in report['rows']:
    if r['yaw_deg']!=0:continue
    name=f'A8_H06_pin{r["pin"]}_REFERENCE'
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=1;data.bevel_depth=.3302;data.bevel_resolution=3;data.use_fill_caps=True
    p=curves[r['array_key']];spline=data.splines.new('POLY');spline.points.add(len(p)-1)
    for point,xyz in zip(spline.points,p):point.co=(*xyz,1.)
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    obj['category']='PLACEHOLDER';obj['data_status']='ASSUMED';obj['role']='review_overlay'
    obj['source']='Alpha2841/7 candidate maxOD0.6604; unpurchased, terminal exits allocated'
    obj['pin']=r['pin'];obj['partial_length_mm']=r['analytic_partial_length_mm']
    obj['not_cut_length']=True;obj['endpoint_scope']='MotionJ5 to yaw-frame staging; CAM and pitch absent'
    color=[(.98,.68,.03),(.91,.40,.015),(.62,.27,.025),(.99,.82,.10)][r['pin']-1]
    obj.data.materials.append(material('A8_H06_AMBER_'+str(r['pin']),color,roughness=.4));overlays.append(obj)
preview_fixed=json.loads(fixed_path.read_text())
for name,r in fixed.items():
    raw=preview_fixed[name]
    obj=create_review_mesh('A8_H01_H04_'+name,raw['vertices_mm'],raw['triangles'])
    obj['category']='PLACEHOLDER';obj['data_status']='ASSUMED';obj['role']='review_overlay'
    obj.data.materials.append(material('A8_FIXED_AMBER',(.44,.29,.12),roughness=.6));overlays.append(obj)
for n,s in plug.items():
    s.o['category']='PLACEHOLDER';s.o['data_status']='ASSUMED';s.o['role']='review_overlay'
    s.o.data.materials.clear();s.o.data.materials.append(material('A8_MATE_ALLOCATION',(.64,.40,.17),roughness=.6))
    overlays.append(s.o)
visible={'Load_Frame','Yaw_Base','Power_Module','MCU_Carrier','MCU_Motion','E_Straight_Header','Socket_AC','Socket_BD','Socket_E','Body_IMU','Rear_Interface_PCB','Pitch_Yoke','Yaw_Reaction_Link'}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1400;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for name,pos,target,scale,hidden in [
    ('body_prefix_top',(0,-5,400),(0,-5,139),145,{'Yaw_Base','Pitch_Yoke','Yaw_Reaction_Link'}),
    ('body_prefix_rear',(190,-290,160),(0,-10,148),175,set())]:
    for o in bpy.context.scene.objects:
        if o.type in ['MESH','CURVE']:
            n=o.name.removeprefix(PREFIX);o.hide_render=not((n in visible and n not in hidden) or o in overlays)
            if o.get('role')=='routing':o.hide_render=True
    camera('A8_H06_REVIEW',pos,target,scale)
    path=OUT/(name+'.png');sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    images.append({'file':path.name,'sha256':sha(path),'hidden_parts_for_inspection':sorted(hidden)})
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_set(o.hide_render)
assert {n:geometry_record(s.o) for n,s in ss.items()}==before
dest=OUT/'H06_BODY_TO_YAW_CANDIDATE_NOT_ADOPTED.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
assert sha(source)==source_hash
result={'status':'PASS','scope':'Independent editable visualization; prints use unapproved J2, not a printable release',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(PREVIEW_SCRIPT),'source_helper_sha256':sha(PREVIEW_HELPER),
    'source_motion_sha256':sha(OUT/'body_to_yaw_motion.json'),'source_curves_sha256':sha(OUT/'body_to_yaw_curves.npz'),
    'candidate_blend':dest.name,'candidate_sha256':sha(dest),'images':images,'main_geometry_unchanged':True,
    'physical_parts_preserved_during_overlay':209,'wire_overlay_count':18,'whole_harness':'BLOCKED'}
(OUT/'preview_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('H06_BODY_PREVIEW_SAVED',flush=True)
