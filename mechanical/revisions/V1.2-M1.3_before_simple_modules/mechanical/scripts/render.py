"""Render the same assembled meshes; visibility/clipping/explosion are presentation operations."""
import sys,math,hashlib,struct,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *

def camera(name,loc,target,scale):
    data=mark(bpy.data.cameras.new(PREFIX+'CAM_'+name)); o=mark(bpy.data.objects.new(PREFIX+'CAM_'+name,data)); COLS['CAMERAS_LIGHTS'].objects.link(o)
    o.location=loc; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); data.type='ORTHO'; data.ortho_scale=scale; data.clip_start=.1; data.clip_end=5000
    bpy.context.scene.camera=o; return o

def line(name,a,b,r=.25):
    a=Vector(a); b=Vector(b); o=cyl(name,(a+b)/2,r,(b-a).length,n=12); o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler(); move_collection(o,'ANNOTATIONS'); o.data.materials.append(MATS['annotation']); return o

def textlabel(name,txt,loc,size=5):
    cu=mark(bpy.data.curves.new(PREFIX+name,'FONT')); cu.body=txt; cu.size=size; cu.align_x='CENTER'; cu.extrude=.001
    o=mark(bpy.data.objects.new(PREFIX+name,cu)); COLS['ANNOTATIONS'].objects.link(o); o.location=loc; o.rotation_euler=(math.pi/2,0,math.pi); o.data.materials.append(MATS['annotation']); return o

def dimensions():
    material('annotation',(.035,.34,.5),emission=.1); y=112; seat=P['body_side_cut_x_mm']; inner=seat+P['wheel_body_gap_mm']
    belly=P['ground_clearance_mm']; height=D['normal_height_mm']; gz=D['wheel_z']+D['wheel_radius']*.65
    for a,b in [((-98,y,0),(98,y,0)),((-19,y,0),(-19,y,belly)),((0,y,belly),(-23,y,belly)),((0,y,0),(-23,y,0)),((seat,y,gz),(inner,y,gz)),((seat,y,gz-4),(seat,y,gz+4)),((inner,y,gz-4),(inner,y,gz+4)),(((seat+inner)/2,y,gz+4),(86,y,gz+22)),((-99,y,0),(-99,y,height))]: line('dim_line',a,b)
    textlabel('belly',f'{belly:g} mm',(-36,y,belly/2),5); textlabel('gap',f'{P["wheel_body_gap_mm"]:g} mm',(86,y,gz+25),5); textlabel('height',f'{height:g} mm',(-102,y,height+14),5)
    textlabel('label','MORI '+P['revision']+' / mm / FRONT +Y',(0,y,height+27),5)
    textlabel('label',f'BODY {P["body_diameter_mm"]:g} / HEAD {P["head_diameter_mm"]:g} / TYRE {P["wheel_diameter_mm"]:g}',(0,y,-18),4)

def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []; p=argparse.ArgumentParser(); p.add_argument('--views',default='all'); p.add_argument('--size',type=int,default=1200); p.add_argument('--samples',type=int,default=32); a=p.parse_args(argv)
    sc=bpy.data.scenes['MORI_V1_Assembly']; bpy.context.window.scene=sc; load_collections(); COLS['DOCK'].hide_viewport=False; assembled()
    sc.render.engine='CYCLES'; sc.cycles.samples=a.samples; sc.cycles.use_denoising=True; sc.render.resolution_x=a.size; sc.render.resolution_y=a.size; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; base_locs={o.name:o.location.copy() for o in sc.objects}; hides={o.name:o.hide_render for o in sc.objects}
    base_materials={o.name:list(o.data.materials) for o in sc.objects if o.type=='MESH'}
    views={
      '45_assembled':((380,500,325),(0,0,145),340),'front':((0,650,145),(0,0,145),325),'side':((650,0,145),(0,0,145),325),'rear':((0,-650,145),(0,0,145),325),
      'top':((0,0,700),(0,0,120),200),'bottom':((0,0,-600),(0,0,100),200),'exploded':((380,560,350),(0,0,195),535),
      'internal':((340,510,320),(0,0,145),335),'structure_only':((340,510,320),(0,0,145),295),'head_section':((310,440,285),(0,0,220),175),'screen_outline_review':((100,-110,D['head_z']+55),(0,40,D['head_z']+P['display']['z_from_head_mm']),100),
      'clearance':((0,650,145),(0,0,145),365),'wheel_gap_detail':((D['wheel_x']+3,650,65),(D['wheel_x']+3,0,65),110),
      'pose_up':((340,510,320),(0,0,145),340),'pose_down':((340,510,320),(0,0,145),340),'docked':((350,520,330),(0,0,145),355)}
    wanted=['45_assembled','head_section','internal'] if a.views=='preview' else list(views) if a.views=='all' else a.views.split(',')
    dig=hashlib.sha256()
    for o in sorted(parts(),key=lambda o:o.name):
        dig.update(o.name.encode()); dig.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes()); o.data.calc_loop_triangles(); dig.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
    rows=[]
    for name in wanted:
        assembled(); bpy.data.objects[PREFIX+'CTRL_Root'].location=base_locs[PREFIX+'CTRL_Root']
        for o in sc.objects:
            if o.name in hides: o.hide_render=hides[o.name]
            if o.name in base_locs: o.location=base_locs[o.name]
            if o.name in base_materials:
                o.data.materials.clear()
                for mat in base_materials[o.name]:o.data.materials.append(mat)
        for c in ['DATUMS','KEEP_OUT','COUPONS','ANNOTATIONS','DOCK']: COLS[c].hide_render=True
        bpy.data.objects[PREFIX+'Studio_Ground'].hide_render=name not in ['45_assembled','docked','pose_up','pose_down']
        if name=='exploded':
            for o in parts():
                if o.get('group')!='dock': o.location+=Vector(o.get('explode_offset_mm',[0,0,0]))
        if name in ['internal','head_section']:
            for n in ['Body_Upper','Body_Lower','Head_Front','Head_Rear','Head_Lower_Guard','Face_Mask']:
                if bpy.data.objects.get(PREFIX+n):bpy.data.objects[PREFIX+n].hide_render=True
            for o in parts():
                if o.get('category')=='PLACEHOLDER':
                    o.data.materials.clear();o.data.materials.append(bpy.data.materials[PREFIX+'unknown'])
        if name=='internal':
            material('annotation',(.05,.7,.9),emission=.5); COLS['ANNOTATIONS'].hide_render=False
            for ax,loc in [('X',(53,5,body_z_mm(26))),('Y',(39,17,body_z_mm(26))),('Z',(39,2,body_z_mm(41)))]: textlabel('imu_label_'+ax,ax,loc,3.5)
        if name=='head_section':
            # Expose a genuine half-section using camera-side clipping on cloned evaluated meshes.
            for o in parts():
                if o.get('group') not in ['yaw','pitch'] and not any(t in o.name for t in ['Yaw_Carrier','Yaw_Bearing','Yaw_Servo','Yaw_Stop']): o.hide_render=True
            bpy.data.objects[PREFIX+'Head_Rear'].hide_render=False
            for n in ['Face_Protector','Display_Module','Display_PCB','Display_Frame','Display_Connector','Screen_Lead','Eye_L','Eye_R']:
                if bpy.data.objects.get(PREFIX+n):bpy.data.objects[PREFIX+n].hide_render=True
        if name=='screen_outline_review':
            for o in parts():
                o.hide_render=o.name.removeprefix(PREFIX) not in ['Display_PCB','Display_Frame','Pitch_Cradle']
            for o in sc.objects:
                if o.get('role') in ['routing','display_content']:o.hide_render=True
        if name=='structure_only':
            visible=['Pitch_Cradle','Display_Frame','Pitch_Yoke','Yaw_Carrier','Load_Frame','Battery_Tray','Motor_Mount_L','Motor_Mount_R','Yaw_Turntable','Yaw_Servo_Mount','Motor_Retainer']
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if name=='pose_up': pose(60,25)
        if name=='pose_down': pose(-60,-20)
        if name=='docked': COLS['DOCK'].hide_render=False; bpy.data.objects[PREFIX+'CTRL_Root'].location.z+=8
        if name in ['clearance','wheel_gap_detail']:
            dimensions(); COLS['ANNOTATIONS'].hide_render=False
        camera(name,*views[name]); bpy.context.view_layer.update(); sc.render.filepath=str(ROOT/'renders'/f'{name}.png')
        print('RENDER',name,flush=True); bpy.ops.render.render(write_still=True)
        rows.append(dict(view=name,geometry_sha256=dig.hexdigest(),visibility_mode=name,ortho_scale_mm=sc.camera.data.ortho_scale,camera_mm=list(sc.camera.location),target_mm=list(views[name][1]),resolution=a.size,samples=a.samples))
        for o in list(COLS['ANNOTATIONS'].objects):
            if not o.get('role'): bpy.data.objects.remove(o,do_unlink=True)
    path=ROOT/'reports/render_manifest.json'; old=json.loads(path.read_text()) if path.exists() else []; by={v['view']:v for v in old}; by.update({v['view']:v for v in rows}); save_json(path,list(by.values()))
    print('RENDER_COMPLETE',flush=True)
if __name__=='__main__': main()
