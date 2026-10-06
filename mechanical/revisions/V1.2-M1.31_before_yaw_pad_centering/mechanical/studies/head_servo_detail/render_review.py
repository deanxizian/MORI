"""Actual saved meshes; isolated specimen views use one declared rigid transform."""
import sys,argparse,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'scripts'))
from common import *
from render import camera
from head_servo_detail import poses

p=argparse.ArgumentParser();p.add_argument('--tag',default='after');p.add_argument('--views',default='all')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(__file__).parent
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1200;sc.render.resolution_y=960;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']:COLS[c].hide_render=True
plain=material('servo_review_print',(.18,.31,.35),roughness=.6)
case=material('servo_review_case',(.11,.13,.15),roughness=.45)
metal=material('servo_review_metal',(.57,.61,.65),roughness=.3,metallic=.65)
for o in parts():
    if o.name.removeprefix(PREFIX) in ['Pitch_Yoke','Pitch_Cradle','Display_Frame']:
        o.data.materials.clear();o.data.materials.append(plain)
    if o.name.removeprefix(PREFIX) in ['Yaw_Servo','Pitch_Servo']:
        o.data.materials.clear();o.data.materials.append(case)
    if o.name.removeprefix(PREFIX) in ['Yaw_Output','Pitch_Output']:
        o.data.materials.clear();o.data.materials.append(metal)
base={o.name:o.matrix_world.copy() for o in parts()}
servo={'Yaw_Servo','Yaw_Output'}
mount={'Pitch_Yoke','Yaw_Servo','Yaw_Output','Pitch_Servo','Pitch_Output','Pitch_Bearing_L','Pitch_Bearing_R'}
mount|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith((PREFIX+'Head_Yaw_Ear_',PREFIX+'Head_Pitch_Ear_'))}
head=mount|{o.name.removeprefix(PREFIX) for o in parts() if o.get('group') in ['yaw','pitch']}
head-= {'Head_Front','Head_Rear','Head_Lower_Guard','Face_Protector','Camera_Window'}
head|={'Eye_L','Eye_R','Yaw_Base','Yaw_Bearing','Yaw_Reaction_Link','Yaw_Horn'}
pitch_seats=mount-{'Yaw_Servo','Yaw_Output'}-{n for n in mount if n.startswith('Head_Yaw_Ear_')}
views={
 'servo':(servo,(50,-64,49),(5.7,0,13),45,True),
 'servo_top':(servo,(5.7,0,130),(5.7,0,13),40,True),
 'servo_side':(servo,(5.7,-140,14),(5.7,0,14),40,True),
 'yoke':({'Pitch_Yoke'},(145,190,340),(0,0,207),124,False),
 'yoke_rear':({'Pitch_Yoke'},(-145,-190,335),(0,0,207),124,False),
 'mounted':(mount,(-150,195,345),(0,0,207),124,False),
 'head':(head,(205,280,325),(0,0,222),144,False),
 'pitch_seats':(pitch_seats,(160,85,267),(-30,0,219),64,False),
}
wanted=list(views) if a.views=='all' else a.views.split(',');manifest={}
for key in wanted:
    visible,loc,aim,scale,local=views[key]
    for o in sc.objects:
        if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if o.name in base:o.matrix_world=base[o.name]
    specimen=poses()['Yaw'].inverted() if local else Matrix.Identity(4)
    if local:
        for name in servo:
            o=bpy.data.objects[PREFIX+name];o.matrix_world=specimen@base[o.name]
    camera('servo_review_'+key,loc,aim,scale)
    sc.render.filepath=str(out/(a.tag+'_'+key+'.png'));bpy.ops.render.render(write_still=True)
    manifest[key]={'camera':loc,'target':aim,'ortho_scale_mm':scale,'visible_ids':sorted(visible),
                   'specimen_rigid_transform':list(map(list,specimen)),
                   'sha256':hashlib.sha256((out/(a.tag+'_'+key+'.png')).read_bytes()).hexdigest()}
save_json(out/(a.tag+'_render_manifest.json'),{'source_blend':bpy.data.filepath,
 'source_blend_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 'mode':'saved geometry unchanged; visibility, materials and isolated rigid specimen transform only','views':manifest})
print('HEAD_SERVO_RENDERED',a.tag,flush=True)
