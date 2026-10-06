"""Render conditional catalogue mates and exact candidate curves in a copy."""
from pathlib import Path
import sys,json,hashlib
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;OUT=HERE/'cam_pitch_port';ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=HERE/'assembly_feed_v3/open_mouth/cleaned/candidate.blend'
assert Path(bpy.data.filepath)==expected
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
visible={'CAM_Mainboard'}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
for o in bpy.context.scene.objects:
    if o.type in ['MESH','CURVE']:o.hide_render=True
for name,o in physical.items():o.hide_render=name not in visible
raw=np.load(OUT/'allocation_meshes.npz');paths=np.load(OUT/'departure_curves.npz')
for o in list(bpy.data.objects):
    if o.get('study_owner')=='A8_CAM_PORT':bpy.data.objects.remove(o,do_unlink=True)
def tag(o):
    o['study_owner']='A8_CAM_PORT';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Catalogue-size conditional mate at photo position; not selected actual CAM connector'
def raw_mesh(name,v,f):
    m=bpy.data.meshes.new(name);m.from_pydata(v.tolist(),[],f.tolist());m.update()
    o=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(o);tag(o);return o
housing=raw_mesh('A8_CAM_PORT_HOUSING',raw['housing_v'],raw['housing_f'])
housing.data.materials.append(material('A8_CAM_PORT_AMBER',(.93,.43,.08),roughness=.5))
colors=[(.08,.5,.62),(.83,.24,.09),(.2,.55,.2),(.69,.36,.69)]
families={}
for direction in ['left','forward']:
    objects=[]
    for i in range(4):
        points=paths[f'{direction}_slot{i}'];c=bpy.data.curves.new(f'A8_CAM_PORT_{direction}_{i}','CURVE');c.dimensions='3D'
        c.bevel_depth=.6604/2;c.bevel_resolution=3;c.resolution_u=1;c.use_fill_caps=True
        s=c.splines.new('POLY');s.points.add(len(points)-1)
        for a,p in zip(s.points,points):a.co=(*p,1)
        o=bpy.data.objects.new(f'A8_CAM_PORT_{direction}_{i}',c);bpy.context.scene.collection.objects.link(o);tag(o)
        c.materials.append(material('A8_CAM_PORT_SLOT_'+str(i),colors[i],roughness=.5));objects.append(o)
    families[direction]=objects
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1050;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
for direction,objects in families.items():
    for name,os in families.items():
        for o in os:o.hide_render=name!=direction;o.hide_set(name!=direction)
    camera('A8_CAM_PORT_REVIEW',(-30,10,213),(-13,-22,211),35)
    dest=OUT/(direction+'_departure.png');sc.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
    images.append({'file':dest.name,'sha256':sha(dest),'family':direction,'eye_mm':[-30,10,213],'target_mm':[-13,-22,211],'ortho_scale_mm':35})
for name,os in families.items():
    for o in os:o.hide_render=name!='left';o.hide_set(name!='left')
assert all(geometry_record(o)==before[n] for n,o in physical.items())
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'comparison.blend'))
result={'status':'PASS','scope':'Candidate curves and catalogue allocation; visibility is selective, geometry unchanged',
    'source_script_sha256':sha(SCRIPT),'source_candidate_sha256':sha(expected),
    'source_mating_mesh_sha256':sha(OUT/'allocation_meshes.npz'),'source_departure_curves_sha256':sha(OUT/'departure_curves.npz'),
    'comparison_blend_sha256':sha(OUT/'comparison.blend'),'visible_source_parts':sorted(visible&set(physical)),
    'images':images,'source_geometry_unchanged':True,'main_applied':False,'physical_pin_colors':'Geometric slot index only'}
(OUT/'render_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_PORT_RENDERED',flush=True)
