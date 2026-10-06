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

def balance_dimensions(cam):
    """Evidence annotations in front of the SAME orthographic model, no mesh changes."""
    report=json.loads((ROOT/'reports/lower_body_comparison.json').read_text())
    now=report['after'];previous=report['before'];z=now['estimated_COM_ground_mm'][2]
    wz=D['wheel_z'];plane=115
    material('annotation',(.02,.45,.66),emission=.4)
    for title,zz,radius in [('estimated_com',z,2.2),('wheel_axis',wz,1.5)]:
        o=sphere(title,(plane,0,zz),radius);move_collection(o,'ANNOTATIONS');o.data.materials.append(MATS['annotation'])
    for a,b in [((plane,0,z),(plane,-94,z)),((plane,0,wz),(plane,-94,wz)),
                ((plane,-90,wz),(plane,-90,z)),((plane,-94,0),(plane,90,0))]:line('balance_dimension',a,b,.3)
    labels=[('estimated_com_label',f'EST COM {z:.1f} mm',-127,z+13,4.2),
            ('previous_com_label',f'PREV {previous["estimated_COM_ground_mm"][2]:.1f} mm',-127,z+5,3.8),
            ('com_height',f'{now["estimated_COM_above_axle_mm"]:.1f} mm',-117,(z+wz)/2,4.5),
            ('axis_label',f'AXLE {wz:g} mm',-127,wz-10,4),
            ('balance_title','MORI '+P['revision']+' / ESTIMATED MASS MODEL',0,302,5),
            ('ground_note',f'BELLY {P["ground_clearance_mm"]:g} mm / TYRE {P["wheel_diameter_mm"]:g} mm',0,-13,4.5),
            ('mass_note','ASSUMED MASSES / BALANCE NOT TESTED',0,-24,4)]
    for name,txt,y,zz,size in labels:
        o=textlabel(name,txt,(plane,y,zz),size);o.rotation_euler=cam.rotation_euler.copy()

def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []; p=argparse.ArgumentParser(); p.add_argument('--views',default='all'); p.add_argument('--size',type=int,default=1200); p.add_argument('--samples',type=int,default=32); a=p.parse_args(argv)
    sc=bpy.data.scenes['MORI_V1_Assembly']; bpy.context.window.scene=sc; load_collections(); COLS['DOCK'].hide_viewport=False; assembled()
    sc.render.engine='CYCLES'; sc.cycles.samples=a.samples; sc.cycles.use_denoising=True; sc.render.resolution_x=a.size; sc.render.resolution_y=a.size; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG'; base_locs={o.name:o.location.copy() for o in sc.objects}; hides={o.name:o.hide_render for o in sc.objects}
    base_materials={o.name:list(o.data.materials) for o in sc.objects if o.type=='MESH'}
    views={
      'bridge_joint_detail':((260,360,270),(0,0,121),175),
      'bridge_joint_exploded':((260,360,305),(0,0,139),203),
      'yaw_stop_detail':((135,-185,295),(0,0,160),83),
      'yaw_stop_exploded':((135,-185,295),(0,0,164),86),
      'battery_tray_fit':((135,490,255),(0,0,92),165),'battery_frame_flat':((135,490,255),(0,0,92),165),'battery_tray_wide':((160,320,245),(0,0,77),135),
      'power_seats':((200,320,340),(0,-5,111),150),'power_board_mounted':((200,320,280),(0,-5,119),150),
      'battery_retention_detail':((240,170,160),(43,8,83),65),'battery_retention_open':((250,100,115),(49,10,83),42),
      'flush_bridge':((190,240,200),(0,0,118),174),'flush_bridge_underside':((160,-240,20),(0,-8,113),168),
      'flush_speaker':((170,-240,145),(0,52,134),85),'flush_cap':((185,-225,-85),(0,0,47),137),'flush_reaction':((35,60,224),(0,0,192),44),
      'consolidated_yaw':((180,-300,315),(0,0,193),116), 'consolidated_base':((170,230,231),(0,0,139),125),
      'consolidated_camera':((72,-110,308),(0,33,267),42), 'consolidated_wheel':((290,160,154),(68,0,52.5),110),
      'rear_interface_section':((180,-66,117),(9,-66,117),42),'frame_underside':((180,250,15),(0,0,103),155),'face_surface_side':((550,0,227),(0,0,D['head_z']),136),
      'imu_underside':((140,-280,-25),(-8,-20,102),153),'rear_interface_detail':((50,30,57),(0,-66,116),61),'level_head_side':((550,0,227),(0,0,D['head_z']),140),'deck_plan':((0,-6,420),(0,-10,110),152),
      'weact_detail':((170,-350,280),(0,-37,124),85),'speaker_shell_detail':((230,410,210),(0,50,137),110),'mic_detail':((190,-440,290),(0,-26,239),98),'mic_open_path':((120,-440,290),(0,-25,235),132),
      'belly_detail':((230,450,185),(0,0,101),178),'yaw_drive_detail':((250,420,263),(0,0,196),125),
      '45_assembled':((380,500,325),(0,0,145),340),'front':((0,650,145),(0,0,145),325),'side':((650,0,145),(0,0,145),325),'rear':((0,-650,145),(0,0,145),325),
      'top':((0,0,700),(0,0,120),200),'bottom':((0,0,-600),(0,0,100),200),'exploded':((380,560,350),(0,0,195),535),
      'internal':((340,510,320),(0,0,145),335),'structure_only':((340,510,320),(0,0,145),295),'structure_exploded':((380,580,360),(0,0,180),460),'deck_detail':((230,390,205),(0,0,134),150),'head_support':((250,-410,280),(0,0,D['head_z']+11),130),'face_detail':((90,650,D['head_z']+35),(0,0,D['head_z']+4),137),'head_section':((310,440,285),(0,0,220),175),'screen_outline_review':((100,-110,D['head_z']+55),(0,40,D['head_z']+P['display']['z_from_head_mm']),100),
      'clearance':((0,650,145),(0,0,145),365),'balance_side':((650,0,140),(0,0,140),380),'wheel_gap_detail':((D['wheel_x']+3,650,65),(D['wheel_x']+3,0,65),110),
      'pose_up':((340,510,320),(0,0,145),340),'pose_down':((340,510,320),(0,0,145),340),'docked':((350,520,330),(0,0,145),355)}
    wanted=['45_assembled','head_section','internal'] if a.views=='preview' else list(views) if a.views=='all' else a.views.split(',')
    dig=hashlib.sha256()
    for o in sorted(parts(),key=lambda o:o.name):
        dig.update(o.name.encode()); dig.update(np.array(o.matrix_world,dtype=np.float64).tobytes()); dig.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes()); o.data.calc_loop_triangles(); dig.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
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
        if name in ['bridge_joint_detail','bridge_joint_exploded']:
            visible={'Yaw_Base','Load_Frame'}|{o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Yaw_Base_')}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=o.name.removeprefix(PREFIX) not in visible
            material('joint_bridge_view',(.075,.30,.38),roughness=.46)
            for n in ['Yaw_Base']:
                ob=bpy.data.objects[PREFIX+n];ob.data.materials.clear();ob.data.materials.append(MATS['joint_bridge_view'])
            if name=='bridge_joint_exploded':
                bpy.data.objects[PREFIX+'Yaw_Base'].location.z+=34
                for sign in [-1,1]:
                    bpy.data.objects[PREFIX+'Yaw_Base_'+str(sign)+'_Screw'].location.x+=sign*22
                    nut=bpy.data.objects[PREFIX+'Yaw_Base_'+str(sign)+'_Nut'];nut.location.x-=sign*13;nut.location.z+=34
        if name in ['internal','head_section','belly_detail','yaw_drive_detail','speaker_shell_detail','mic_detail','mic_open_path']:
            for n in ['Body_Upper','Body_Lower','Head_Front','Head_Rear','Head_Lower_Guard','Face_Mask']:
                if bpy.data.objects.get(PREFIX+n):bpy.data.objects[PREFIX+n].hide_render=True
            for o in parts():
                if o.get('category')=='PLACEHOLDER':
                    o.data.materials.clear();o.data.materials.append(bpy.data.materials[PREFIX+'unknown'])
        if name=='speaker_shell_detail':
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content'] and o.name.removeprefix(PREFIX) not in ['Body_Upper','Speaker','Speaker_Mount','Speaker_Gasket','Speaker_Screw_-1','Speaker_Screw_1','Speaker_Insert_-1','Speaker_Insert_1']:o.hide_render=True
        if name=='speaker_shell_detail':
            shell=bpy.data.objects[PREFIX+'Body_Upper'];shell.hide_render=False
            mat=bpy.data.materials.get(PREFIX+'speaker_xray') or bpy.data.materials.new(PREFIX+'speaker_xray');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.84;solid=nodes.new('ShaderNodeBsdfDiffuse');solid.inputs['Color'].default_value=(.65,.72,.78,1);clear=nodes.new('ShaderNodeBsdfTransparent');mat.node_tree.links.new(solid.outputs[0],mix.inputs[1]);mat.node_tree.links.new(clear.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],out.inputs[0]);shell.data.materials.clear();shell.data.materials.append(mat)
        if name=='mic_detail':
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content','annotation']:o.hide_render=o.name.removeprefix(PREFIX) not in ['CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R','MIC_Sound_Port_L','MIC_Sound_Port_R']
        if name=='mic_open_path':
            visible={'CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R','MIC_Sound_Port_L','MIC_Sound_Port_R','Head_Rear','Pitch_Cradle'}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content','annotation']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
            # Transparency changes visibility only; mesh dimensions and bores stay exact.
            for n,alpha in [('Head_Rear',.87),('Pitch_Cradle',.62)]:
                mat=bpy.data.materials.new(PREFIX+'mic_open_'+n);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=alpha;solid=nodes.new('ShaderNodeBsdfDiffuse');solid.inputs['Color'].default_value=(.8,.86,.9,1);clear=nodes.new('ShaderNodeBsdfTransparent');mat.node_tree.links.new(solid.outputs[0],mix.inputs[1]);mat.node_tree.links.new(clear.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],out.inputs[0]);ob=bpy.data.objects[PREFIX+n];ob.data.materials.clear();ob.data.materials.append(mat)
        if name in ['imu_underside','rear_interface_detail','deck_plan','level_head_side','rear_interface_section','frame_underside','face_surface_side']:
            sets={'imu_underside':{'Load_Frame','Body_IMU','IMU_Screw_0','IMU_Screw_1','IMU_Insert_0','IMU_Insert_1','IMU_Lead'},'rear_interface_detail':{'Body_Upper','Rear_Interface_PCB','Power_Switch','USB_Receptacle','Rear_Interface_Screw_0','Rear_Interface_Screw_1','Rear_Interface_Insert_0','Rear_Interface_Insert_1','Interface_Lead'},'deck_plan':{'Load_Frame'},'level_head_side':{'Head_Rear','Head_Front','Face_Mask','Face_Protector','Display_PCB','Display_Frame','Pitch_Cradle','Camera_PCB','Camera_Lens','Camera_Window','Camera_Baffle'}}
            sets['rear_interface_section']=sets['rear_interface_detail']-{'Interface_Lead'};sets['frame_underside']=sets['deck_plan']
            sets['face_surface_side']={'Head_Front','Head_Rear','Face_Mask','Face_Protector','Display_PCB','Eye_L','Eye_R','Camera_Lens','Camera_Window','Camera_Baffle'}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in sets[name]
            if name=='level_head_side':
                for n in ['Head_Front','Head_Rear']:
                    shell=bpy.data.objects[PREFIX+n];mat=bpy.data.materials.get(PREFIX+'level_xray') or bpy.data.materials.new(PREFIX+'level_xray');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.82;solid=nodes.new('ShaderNodeBsdfDiffuse');solid.inputs['Color'].default_value=(.8,.85,.9,1);clear=nodes.new('ShaderNodeBsdfTransparent');mat.node_tree.links.new(solid.outputs[0],mix.inputs[1]);mat.node_tree.links.new(clear.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],out.inputs[0]);shell.data.materials.clear();shell.data.materials.append(mat)
        if name.startswith('consolidated_'):
            visible={'consolidated_yaw':{'Pitch_Yoke'},'consolidated_base':{'Yaw_Base'},'consolidated_camera':{'Head_Front','Camera_Window'},'consolidated_wheel':{'Wheel_Hub_R','Tire_R'}}[name]
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if name.startswith('battery_retention_'):
            visible={'Load_Frame','Battery_Tray','Battery','Drive_Bridge','Motor_Retainer','Drive_Motor_L','Drive_Motor_R','Wheel_Axle_L','Wheel_Axle_R'}
            visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith((PREFIX+'Wheel_Bearing_',PREFIX+'Wheel_Cap_Clamp_'))}
            if name=='battery_retention_detail':
                visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Battery_Retainer_')}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if name in ['battery_tray_fit','battery_frame_flat','battery_tray_wide']:
            visible={'Load_Frame','Battery_Tray','Battery','Drive_Bridge','Yaw_Base','Speaker','Speaker_Mount'}
            if name=='battery_frame_flat':visible={'Load_Frame'}
            elif name=='battery_tray_wide':visible={'Battery_Tray'}
            else:visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(('MORI_V1__Battery_Retainer_','MORI_V1__Drive_L_','MORI_V1__Drive_R_'))}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if name in ['power_seats','power_board_mounted']:
            visible={'Load_Frame','MCU_Carrier','MCU_Motion'}
            visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Carrier_')}
            if name=='power_board_mounted':
                visible.add('Power_Module')
                visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Power_Board_')}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=o.name.removeprefix(PREFIX) not in visible
            if name=='power_board_mounted':
                o=bpy.data.objects[PREFIX+'Power_Module']
                mat=bpy.data.materials.get(PREFIX+'power_capacity_xray') or bpy.data.materials.new(PREFIX+'power_capacity_xray')
                mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear()
                out=nodes.new('ShaderNodeOutputMaterial');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.88
                solid=nodes.new('ShaderNodeBsdfDiffuse');solid.inputs['Color'].default_value=(.7,.33,.06,1)
                clear=nodes.new('ShaderNodeBsdfTransparent')
                mat.node_tree.links.new(solid.outputs[0],mix.inputs[1]);mat.node_tree.links.new(clear.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],out.inputs[0])
                o.data.materials.clear();o.data.materials.append(mat)
        if name.startswith('flush_'):
            sets={'flush_bridge':{'Load_Frame','Yaw_Base','Power_Module','MCU_Carrier','MCU_Motion'},'flush_bridge_underside':{'Load_Frame','Yaw_Base'},'flush_speaker':{'Speaker','Speaker_Gasket','Speaker_Screw_-1','Speaker_Screw_1','Speaker_Insert_-1','Speaker_Insert_1'},'flush_cap':{'Drive_Bridge','Motor_Retainer'},'flush_reaction':{'Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut'}}
            visible=sets[name]
            if name in ['flush_bridge','flush_bridge_underside']:visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Yaw_Base_')}
            if name=='flush_cap':visible|={o.name.removeprefix(PREFIX) for o in parts() if o.name.startswith(PREFIX+'Wheel_Cap_Clamp_')}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
            if name=='flush_bridge':
                o=bpy.data.objects[PREFIX+'Power_Module'];o.data.materials.clear();o.data.materials.append(bpy.data.materials[PREFIX+'unknown'])
        if name=='weact_detail':
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX)!='MCU_Motion'
        if name=='internal':
            material('annotation',(.05,.7,.9),emission=.5); COLS['ANNOTATIONS'].hide_render=False
            imu=Vector([*P['layout_cleanup']['imu']['center_xy_mm'],P['layout_cleanup']['imu']['pcb_reference_z_mm']])
            for ax,offset in [('X',(11,-15,-6.5)),('Y',(-3,-3,-6.5)),('Z',(-3,-18,8.5))]: textlabel('imu_label_'+ax,ax,imu+Vector(offset),3.5)
        if name in ['head_section','yaw_drive_detail']:
            # Expose a genuine half-section using camera-side clipping on cloned evaluated meshes.
            for o in parts():
                if o.get('group') not in ['yaw','pitch'] and not any(t in o.name for t in ['Yaw_Carrier','Yaw_Base','Yaw_Reaction','Yaw_Output','Yaw_Horn','Yaw_Lock','Yaw_Bearing','Yaw_Servo','Yaw_Stop']): o.hide_render=True
            bpy.data.objects[PREFIX+'Head_Rear'].hide_render=False
            for n in ['Face_Protector','Display_Module','Display_PCB','Display_Frame','Display_Connector','Screen_Lead','Eye_L','Eye_R']:
                if bpy.data.objects.get(PREFIX+n):bpy.data.objects[PREFIX+n].hide_render=True
        if name=='belly_detail':
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content'] and o.get('group') in ['pitch','yaw']:o.hide_render=True
        if name=='screen_outline_review':
            for o in parts():
                o.hide_render=o.name.removeprefix(PREFIX) not in ['Display_PCB','Display_Frame','Pitch_Cradle']
            for o in sc.objects:
                if o.get('role') in ['routing','display_content']:o.hide_render=True
        if name in ['structure_only','structure_exploded']:
            visible=['Pitch_Cradle','Display_Frame','Pitch_Yoke','Yaw_Carrier','Load_Frame','Battery_Tray','Motor_Mount_L','Motor_Mount_R','Yaw_Turntable','Yaw_Servo_Mount','Motor_Retainer']
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:
                    o.hide_render=not (o.get('simple_support_module') or o.name.removeprefix(PREFIX) in visible)
                    if name=='structure_exploded' and not o.hide_render:o.location+=Vector(o.get('explode_offset_mm',[0,0,0]))
        if name=='deck_detail':
            visible={'Load_Frame','Body_Cheek_L','Body_Cheek_R','Yaw_Base','Yaw_Servo','Yaw_Output','Yaw_Horn','Yaw_Bearing','Battery','Power_Module','Power_Board_Carrier','MCU_Motion','Body_IMU'}
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX) not in visible
        if name=='head_support':
            for o in sc.objects:
                if o.get('role') in ['part','routing','display_content']:o.hide_render=o.name.removeprefix(PREFIX)!='Pitch_Cradle'
        if name=='pose_up': pose(60,25)
        if name=='pose_down': pose(-60,-20)
        if name=='docked': COLS['DOCK'].hide_render=False; bpy.data.objects[PREFIX+'CTRL_Root'].location.z+=8
        if name in ['clearance','wheel_gap_detail']:
            dimensions(); COLS['ANNOTATIONS'].hide_render=False
        if name in ['45_assembled','front','side','rear','top','bottom','face_detail','docked']:pose(0,P['head_joint'].get('default_pitch_deg',0))
        # Genuine crops of unchanged assembly meshes: these temporary objects
        # are never saved into .blend or used for STL export.
        crops=[]
        if name in ['yaw_stop_detail','yaw_stop_exploded']:
            visible={'Yaw_Base','Pitch_Yoke','Yaw_Bearing'}
            for ob in sc.objects:
                if ob.get('role') in ['part','routing','display_content']:
                    ob.hide_render=ob.name.removeprefix(PREFIX) not in visible
            material('yaw_stop_rotor_view',(.05,.44,.62),metallic=.1,roughness=.42)
            for n in ['Yaw_Base','Pitch_Yoke']:
                src=bpy.data.objects[PREFIX+n];cp=clone(src,'view_stop_'+n)
                # Actual upper/lower mesh cropping exposes the mechanism; no
                # change to retained coordinates or dimensions of the stops.
                clip_z(cp,153,166)
                cp.data.materials.clear()
                if n=='Pitch_Yoke':cp.data.materials.append(MATS['yaw_stop_rotor_view'])
                else:
                    for mat in base_materials[src.name]:cp.data.materials.append(mat)
                if name=='yaw_stop_exploded' and n=='Pitch_Yoke':cp.location.z+=9
                src.hide_render=True;cp.hide_render=False;crops.append(cp)
        if name in ['rear_interface_detail','rear_interface_section']:
            selected=[o for o in parts() if not o.hide_render]
            for src in selected:
                if name=='rear_interface_detail' and src.name!=PREFIX+'Body_Upper':continue
                cp=clone(src,'view_section_'+src.name.removeprefix(PREFIX))
                if name=='rear_interface_detail':intersect(cp,box('view_clip',(0,-69,117),(38,32,32)))
                else:intersect(cp,box('view_clip',(7,-69,117),(4,32,32)))
                cp.data.materials.clear()
                for mat in src.data.materials:cp.data.materials.append(mat)
                src.hide_render=True;cp.hide_render=False;crops.append(cp)
        if name=='consolidated_camera':
            src=bpy.data.objects[PREFIX+'Head_Front'];cp=clone(src,'view_camera_collar')
            intersect(cp,box('view_camera_region',(0,33,267),(34,32,30)))
            cp.data.materials.clear()
            for mat in base_materials[src.name]:cp.data.materials.append(mat)
            src.hide_render=True;cp.hide_render=False;crops.append(cp)
        cam=camera(name,*views[name])
        if name=='balance_side':balance_dimensions(cam);COLS['ANNOTATIONS'].hide_render=False
        if name in ['mic_detail','mic_open_path']:
            material('annotation',(.05,.7,.9),emission=.5)
            COLS['ANNOTATIONS'].hide_render=False
            for sign,label in [(-1,'MIC1'),(1,'MIC2')]:
                t=textlabel('mic_label_'+label,label,(sign*25,-35,240),3.5);t.rotation_euler=cam.rotation_euler.copy()
            t=textlabel('mic_note','ONBOARD / PHOTO POSITION ESTIMATE',(0,-35,213),2.5);t.rotation_euler=cam.rotation_euler.copy()
            if name=='mic_open_path':
                t=textlabel('mic_mode','OPEN HEAD CAVITY / NO DUCTS',(0,-58,282),3);t.rotation_euler=cam.rotation_euler.copy()
        if name=='rear_interface_section':
            material('annotation',(.1,.8,.95),emission=.4);COLS['ANNOTATIONS'].hide_render=False
            for label,y,z in [('SHELL TAB',-58,127),('M2 INSERT',-57,122),('PCB 1.6mm',-53,114),('SCREW UP',-57,105)]:
                textlabel('section_'+label,label,(15,y,z),1.8).rotation_euler=cam.rotation_euler.copy()
            for aa,bb in [((15,-61,118),(15,-59,121)),((15,-61,113),(15,-58,107))]:line('section_leader',aa,bb,.1)
        bpy.context.view_layer.update(); sc.render.filepath=str(ROOT/'renders'/f'{name}.png')
        print('RENDER',name,flush=True); bpy.ops.render.render(write_still=True)
        rows.append(dict(default_pitch_deg=P['head_joint'].get('default_pitch_deg',0) if name in ['45_assembled','front','side','rear','top','bottom','face_detail','docked'] else 0,view=name,geometry_sha256=dig.hexdigest(),visibility_mode=name,ortho_scale_mm=sc.camera.data.ortho_scale,camera_mm=list(sc.camera.location),target_mm=list(views[name][1]),resolution=a.size,samples=a.samples))
        if name.startswith('yaw_stop_'):
            rows[-1]['section_method']='Actual Yaw_Base/Pitch_Yoke cropped to Z153..166 to reveal stops; rotor blue for explanation. Exploded view adds9mm Z presentation offset only, never saved/exported.'
        elif name=='consolidated_camera':rows[-1]['section_method']='Actual head-front mesh cropped around integrated camera collar; assembly coordinates unchanged'
        elif crops:rows[-1]['section_method']='Actual meshes clipped to local PCB area; section X=9mm through right mounting screw; assembly dimensions unchanged'
        for o in crops:SOLIDS.pop(o.name,None);bpy.data.objects.remove(o,do_unlink=True)
        for o in list(COLS['ANNOTATIONS'].objects):
            if not o.get('role'): bpy.data.objects.remove(o,do_unlink=True)
    path=ROOT/'reports/render_manifest.json'; old=json.loads(path.read_text()) if path.exists() else []; by={v['view']:v for v in old}; by.update({v['view']:v for v in rows}); save_json(path,list(by.values()))
    print('RENDER_COMPLETE',flush=True)
if __name__=='__main__': main()
