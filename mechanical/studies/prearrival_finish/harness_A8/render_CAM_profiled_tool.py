"""Render the new local tool result without editing source robot objects."""
from pathlib import Path
import sys,json,hashlib
RT_SCRIPT=Path(__file__).resolve();RT_ROOT=RT_SCRIPT.parent;RT_OUT=RT_ROOT/'cam_profiled_tool'
sys.path.insert(0,str(RT_ROOT.parents[3]/'mechanical/scripts'))
sys.path.insert(0,str(RT_ROOT.parents[3]/'mechanical/scripts/vendor'))
import manifold3d as manifold
from common import *
from render import camera
from validate_head_cleanup import geometry_record
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
RT_SOURCE=RT_ROOT/'cam_wired_cradle/review.blend'
assert Path(bpy.data.filepath)==RT_SOURCE
screen=json.loads((RT_OUT/'screen.json').read_text());both=json.loads((RT_OUT/'both_anchors.json').read_text())
assert screen['status']=='PASS' and both['status']=='BLOCKED'
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
names={'Pitch_Yoke','Yaw_Servo','Pitch_Servo','Pitch_Cradle','CAM_Mainboard'}|{n for n in physical if n.startswith(('CAM_Mount_','Head_Cradle_Insert_','Onboard_MIC_','Head_Pitch_Ear_','Head_Yaw_Ear_'))}
extras={}

def toolmesh(name,filename,clip=False):
    a=np.load(RT_OUT/filename);m=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles']))
    if clip:m=m^manifold.Manifold.cube([400,400,400]).translate([-200,-200,-122])
    a=m.to_mesh64();d=bpy.data.meshes.new('A8_TOOL_'+name);d.from_pydata(a.vert_properties[:,:3].tolist(),[],a.tri_verts.tolist());d.update()
    o=bpy.data.objects.new('A8_TOOL_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_TOOL_ORANGE',(.98,.52,.12),roughness=.55))
    o['study_owner']='CAM_PROFILED_TOOL';o['part_class']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['scope']='Tool working envelope only; not robot part or vendor CAD; clipped at Z278 for local view' if clip else 'Full assumed tool working envelope'
    extras[name]=o;return o

def line(name,points,color,r=.18):
    d=bpy.data.curves.new('A8_TOOL_'+name,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2;d.use_fill_caps=True
    s=d.splines.new('POLY');s.points.add(len(points)-1)
    for v,p in zip(s.points,points):v.co=(*p,1)
    o=bpy.data.objects.new('A8_TOOL_'+name,d);bpy.context.scene.collection.objects.link(o)
    d.materials.append(material('A8_TOOL_LINE_'+name,color,roughness=.5));o['study_owner']='CAM_PROFILED_TOOL';o['scope']='Presentation guide, not hardware'
    extras[name]=o;return o

toolmesh('yaw30','yaw_30_tool.npz');toolmesh('yaw30_local','yaw_30_tool.npz',True)
toolmesh('connector0_local','connector_0_tool.npz',True)
toolmesh('old45_local','old_boxes_45_tool.npz',True)
toolmesh('new45_local','yaw_45_tool.npz',True)
gap=next(r for r in both['rows'] if r['anchor']=='yaw' and r['angle_deg']==30.)['wire_minimum']
line('gap',[gap['point_mm'],gap['nearest_tool_mm']],(.1,.9,.48),.13)
tail=np.load(RT_OUT/'connector_tail_corridor.npz');lo=tail['vertices_mm'].min(0);hi=tail['vertices_mm'].max(0)
tail_names=[]
for axis in range(3):
    other=[i for i in range(3) if i!=axis]
    for a in [0,1]:
        for b in [0,1]:
            p=lo.copy();p[other[0]]=[lo[other[0]],hi[other[0]]][a];p[other[1]]=[lo[other[1]],hi[other[1]]][b]
            q=p.copy();q[axis]=hi[axis];n=f'tail_{axis}_{a}_{b}'
            line(n,[p,q],(.92,.13,.1));tail_names.append(n)

def show(extra_names):
    for o in bpy.context.scene.objects:
        if o.type not in ['MESH','CURVE']:continue
        old_extra=o.name.startswith(('A8_CAM_INSERT_wire','A8_CAM_INSERT_catalogue_housing','A8_CAM_INSERT_yaw_tie','A8_CAM_CONNECTOR_'))
        o.hide_render=o.name.removeprefix(PREFIX) not in names and not old_extra
    for n,o in extras.items():o.hide_render=n not in extra_names
    bpy.context.view_layer.update()

sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
images=[]
def snap(name,selected,eye,target,scale,scope):
    show(selected);camera('A8_TOOL_'+name,eye,target,scale);sc.render.filepath=str(RT_OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    images.append({'file':name+'.png','sha256':sha(RT_OUT/(name+'.png')),'scope':scope})
snap('yaw30_local',['yaw30_local','gap'],(-92,112,302),(-4,1,236),105,'Profile at30deg. Tool truncated only for display atZ278; full tool and continuous60mm axial sweep tested. Green line locates nearest model wire/tool point, not surface-gap dimension.')
snap('yaw30_full',['yaw30'],(-140,170,372),(27,5,273),190,'Complete assumed125mm tool body; optical frame and shells are not yet fitted.')
snap('old45',['old45_local'],(-92,112,302),(-4,1,236),105,'Old wide-handle boxes at45deg, BLOCKED. Same local display cutoff and scene camera as new45.')
snap('new45',['new45_local'],(-92,112,302),(-4,1,236),105,'Reference-profile45deg local PASS, but enlarged/earlier transition sensitivity FAILS;30deg is the more useful direction.')
snap('connector_work',['connector0_local']+tail_names,(-118,70,292),(-8,0,227),120,'Tool itself clears at0deg. Red110mm straight working corridor intersectsPitch_Servo; not proof that a real flexible tie must intersect.')
show(['yaw30_local','gap']);camera('A8_TOOL_final',(-92,112,302),(-4,1,236),105)
assert all(geometry_record(o)==before[n] for n,o in physical.items())
sc['independent_unapproved_study']='Photo-derived tool envelope; local yaw cutting access only, whole CAM/harness installation BLOCKED'
bpy.ops.wm.save_as_mainfile(filepath=str(RT_OUT/'review.blend'))
report={'status':'PASS','source_main_sha256':screen['source_main_sha256'],'source_candidate_sha256':sha(RT_SOURCE),
        'script_sha256':sha(RT_SCRIPT),'screen_sha256':sha(RT_OUT/'screen.json'),'both_anchors_sha256':sha(RT_OUT/'both_anchors.json'),
        'review_sha256':sha(RT_OUT/'review.blend'),'physical_parts_restored_unchanged':len(physical),'images':images,
        'display_cutoff_only_mm':278.,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False}
(RT_OUT/'render_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('PROFILED_RENDER_DONE','PASS',len(images),flush=True)
