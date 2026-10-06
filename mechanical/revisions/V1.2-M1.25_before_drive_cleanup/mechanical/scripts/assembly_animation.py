"""Editable assembly presentation, derived from the released assembly meshes.

Run Blender with mori_v1_2.blend and this script. This writes a separate .blend;
the manufacturing/geometry source is never saved or modified by this script.
"""
import sys, json, math, hashlib, argparse, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *

ANIM_OWNER = 'mori_assembly_presentation_v1'
AP = 'MORI_ANIM__'
OUT = ROOT / 'animation'
SCENE_NAME = 'MORI_Assembly_Animation'
TARGET = ROOT / 'mori_assembly_animation.blend'
FPS = 24
# Each stage has a native timeline marker, camera and editable object actions.
STAGES = [
    ('轮驱分总成', 'S288 ×2；保留原配输出盘', 48, 'wheel'),
    ('连接金属法兰轴', '每侧 6 枚原厂兼容自攻螺钉；金属轴不打印', 66, 'wheel'),
    ('轴承与内隔套', '内轴承 → 5 mm 金属隔套 → 外轴承', 72, 'wheel'),
    ('装入轮驱上座', '两套电机 / 轴 / 轴承组件由下方进入', 84, 'drive'),
    ('固定共用底盖', '上下座夹持；4 枚 M3 螺钉从底面装入', 60, 'drive_close'),
    ('主托板与底面电路板', 'IMU + 轮驱9V / 头部6V模块；底面预装后接轮驱', 96, 'frame'),
    ('基板与电源板装件', 'P5R2电源板已集成运动5V + CAM 5V；两枚M2×6固定', 96, 'body'),
    ('插接固定 Yaw 承重桥', '内侧预装螺母；桥脚插入托板，两侧 M3×8 锁紧', 66, 'body'),
    ('电池托盘与电池', '加宽托盘沿前方滑入；底部承托，左右 M2 限位', 66, 'body'),
    ('Yaw 承重组件', '连续底座 U 托；反力轴穿入后整体落入轴承', 78, 'head'),
    ('水平与俯仰驱动', '倒置 Yaw 舵机 + 侧置 Pitch 舵机', 60, 'head'),
    ('双侧支撑与头托', '等厚直角头托；从两侧插入支撑轴', 66, 'head'),
    ('显示与摄像头', '等宽叉架预装螺母后侧向锁紧；圆屏与摄像头独立', 78, 'optics'),
    ('线束与头壳', '服务环按当前路径示意；前后壳合拢', 78, 'head_shell'),
    ('上壳附件台面预装', '原生后接口板固定到壳；开关外部操作仍待改版', 84, 'shell_bench'),
    ('机身合装', '从附件预装切换到总装姿态；下壳由底部合入', 66, 'whole'),
    ('安装车轮', '外隔套 → 轮胎 / 轮毂 → 垫圈与端螺钉', 78, 'whole'),
    ('装配完成 · 当前设计', f'尺寸沿用 {P["revision"]}；实物配合与装配工艺待验证', 96, 'hero'),
]


def tagged(block):
    block['mori_owner'] = ANIM_OWNER
    return block


def curves(o):
    ad = o.animation_data
    if not ad or not ad.action:
        return []
    a = ad.action
    if hasattr(a, 'fcurves'):
        return list(a.fcurves)
    result = []
    for layer in a.layers:
        for strip in layer.strips:
            bag = strip.channelbag(ad.action_slot)
            if bag:
                result.extend(bag.fcurves)
    return result


def smooth(o):
    for fc in curves(o):
        for k in fc.keyframe_points:
            if fc.data_path in ['hide_render', 'hide_viewport']:
                k.interpolation = 'CONSTANT'
            else:
                k.interpolation = 'BEZIER'
                k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'


def vis(o, frame, visible):
    o.hide_render = o.hide_viewport = not visible
    o.keyframe_insert(data_path='hide_render', frame=frame)
    o.keyframe_insert(data_path='hide_viewport', frame=frame)


def move(o, frame, loc):
    o.location = loc
    o.keyframe_insert(data_path='location', frame=frame)


def mat(name, color, emission=False):
    m = tagged(bpy.data.materials.new(AP + name))
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    node = nodes.new('ShaderNodeEmission' if emission else 'ShaderNodeBsdfPrincipled')
    node.inputs['Color' if emission else 'Base Color'].default_value = (*color, 1)
    if not emission:
        node.inputs['Roughness'].default_value = .48
    m.node_tree.links.new(node.outputs[0], out.inputs['Surface'])
    return m


def signature(objects):
    h = hashlib.sha256()
    for o in sorted(objects, key=lambda x:x.name):
        h.update(o.name.encode())
        h.update(np.asarray(o.matrix_world, dtype=np.float64).tobytes())
        h.update(np.asarray([v.co[:] for v in o.data.vertices], dtype=np.float32).tobytes())
    return h.hexdigest()


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', choices=['none', 'stills', 'video'], default='stills')
    parser.add_argument('--width', type=int, default=960)
    parser.add_argument('--samples', type=int, default=32)
    a = parser.parse_args(args)
    OUT.mkdir(exist_ok=True)
    source = ROOT / 'mori_v1_2.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    source_scene = bpy.data.scenes['MORI_V1_Assembly']
    bpy.context.window.scene = source_scene
    load_collections(); assembled()
    originals = [o for o in source_scene.objects if o.type == 'MESH'
                 and o.get('mori_owner') == OWNER and o.get('role') in ['part','routing','display_content']
                 and o.get('group') not in ['dock','coupon']]
    baseline = signature(originals)
    old = bpy.data.scenes.get(SCENE_NAME)
    if old:
        bpy.data.scenes.remove(old)
    for o in list(bpy.data.objects):
        if o.get('mori_owner') == ANIM_OWNER:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.get('mori_owner') == ANIM_OWNER:
            bpy.data.collections.remove(c)
    for blocks in [bpy.data.meshes,bpy.data.curves,bpy.data.cameras,bpy.data.lights,bpy.data.materials,bpy.data.actions,bpy.data.fonts]:
        for b in list(blocks):
            if b.get('mori_owner') == ANIM_OWNER and b.users == 0:
                blocks.remove(b)
    scene = tagged(bpy.data.scenes.new(SCENE_NAME))
    bpy.context.window.scene = scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = .001
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.world = source_scene.world
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = a.samples
    scene.render.resolution_x = a.width; scene.render.resolution_y = a.width * 9 // 16
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.sync_mode = 'FRAME_DROP'
    scene.view_settings.view_transform = 'AgX'
    scene.render.film_transparent = False
    stages = []
    frame = 1
    for i,(title,note,duration,shot) in enumerate(STAGES,1):
        stages.append(dict(index=i,title=title,note=note,start=frame,end=frame+duration-1,shot=shot))
        frame += duration
    scene.frame_start = 1; scene.frame_end = frame - 1
    scene['presentation_only'] = True
    scene['source_revision'] = P['revision']
    scene['source_blend'] = str(source)
    scene['motion_qualification'] = 'Illustrative staging, not a collision-validated assembly process. Shell bench-to-assembly transition is a cut, not an insertion-path claim.'
    def collection(name):
        c = tagged(bpy.data.collections.new(AP + name)); scene.collection.children.link(c); return c
    stagecols = {s['index']:collection(f'{s["index"]:02d}_{s["title"]}') for s in stages}
    controls = collection('CONTROLS'); studio = collection('STUDIO'); hud = collection('CAPTIONS')
    roots = {}
    def root(name):
        o = tagged(bpy.data.objects.new(AP+name,None)); controls.objects.link(o)
        o.empty_display_type = 'PLAIN_AXES'; o.empty_display_size = 8; roots[name] = o; return o
    for n in ['Wheel_L','Wheel_R','Frame_Bench','Fixed_Bridge','Yaw_Group']:
        root(n)
    unknown = mat('Unconfirmed',(.64,.29,.055))
    lettering = mat('Text',(.72,.83,.88),True)
    accent = mat('Accent',(.15,.78,.88),True)
    note_mat = mat('Note',(.45,.58,.67),True)
    # Transparent covers keep their real mesh; presentation overrides only
    # their shader, so screen pixels remain visible in Eevee.
    clear = tagged(bpy.data.materials.new(AP+'Clear_Window')); clear.use_nodes = True
    nn=clear.node_tree.nodes; nn.clear(); oo=nn.new('ShaderNodeOutputMaterial'); tt=nn.new('ShaderNodeBsdfTransparent'); clear.node_tree.links.new(tt.outputs[0],oo.inputs[0])
    actors = {}; original_by_id = {}; assignments = {}; bases = {}
    for src in originals:
        name = src.name.removeprefix(PREFIX)
        o = src.copy(); o.animation_data_clear(); o.parent = None
        o.name = AP + name; tagged(o)
        o['source_object'] = src.name; o['presentation_actor'] = True
        o['export_candidate'] = False
        o.matrix_world = src.matrix_world.copy()
        o.hide_render = o.hide_viewport = False
        for slot in o.material_slots:
            slot.link = 'OBJECT'
            exterior_style={'Tire_L','Tire_R','Face_Mask','Camera_Lens','Power_Switch','USB_Receptacle','Face_Protector','Camera_Window'}
            if src.get('category') == 'PLACEHOLDER' and src.get('role') == 'part' and name not in exterior_style:
                slot.material = unknown
            if name in ['Face_Protector','Camera_Window']:
                slot.material = clear
        actors[name] = o; original_by_id[name] = src; bases[name] = src.matrix_world.copy()
    def select(*names, prefix=()):
        result = set(names)
        result.update(n for n in actors if any(n.startswith(p) for p in prefix))
        missing = result - set(actors)
        if missing:
            raise ValueError('Missing source parts: '+str(missing))
        return sorted(result)
    def assign(ids, step, offset=(0,0,0), begin=.08, finish=.7, parent=None, stagger=0):
        s=stages[step-1];span=s['end']-s['start']
        for i,n in enumerate(ids):
            if n in assignments: raise ValueError('Duplicate animation assignment: '+n)
            o=actors[n];stagecols[step].objects.link(o)
            if parent:o.parent=roots[parent]
            o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=bases[n]
            base=o.location.copy();start=s['start']+round(begin*span)+i*stagger;end=s['start']+round(finish*span)+i*stagger
            start=min(start,s['end']-8);end=min(end,s['end']-1)
            vis(o,1,False)
            if start>1:vis(o,start-1,False)
            vis(o,start,True)
            move(o,1,base+Vector(offset));move(o,start,base+Vector(offset));move(o,end,base);move(o,scene.frame_end,base)
            o['assembly_step']=step;o['assembly_title']=s['title'];assignments[n]=step
    # Wheel cartridges are assembled off to either side, then installed from
    # below the cage. Presentation roots return exactly to zero afterwards.
    for side,sign in [('L',-1),('R',1)]:
        pr='Wheel_'+side
        assign(select('Drive_Motor_'+side,prefix=(f'S288_Output_{side}_',)),1,(sign*24,0,0),parent=pr)
        assign(select('Wheel_Axle_'+side),2,(sign*45,0,0),finish=.42,parent=pr)
        assign(select(prefix=(f'Wheel_Output_Screw_{side}_',)),2,(sign*22,0,0),begin=.43,finish=.78,parent=pr,stagger=1)
        for n,begin,end,offset in [(f'Wheel_Bearing_{side}_Inner',.03,.35,66),(f'Wheel_Spacer_{side}_0',.30,.62,66),(f'Wheel_Bearing_{side}_Outer',.56,.94,66)]:
            assign([n],3,(sign*offset,0,0),begin,end,parent=pr)
        r=roots[pr];s=stages[3];duration=s['end']-s['start']
        for fr,xyz in [(1,(sign*100,0,0)),(s['start'],(sign*100,0,0)),(s['start']+round(duration*.25),(sign*100,0,-65)),(s['start']+round(duration*.58),(0,0,-65)),(s['end']-3,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    assign(select('Drive_Bridge',prefix=('Motor_Top_Pad_',)),4,(0,0,35),begin=0,finish=.22)
    assign(select('Motor_Retainer',prefix=('Motor_Retainer_Pad_',)),5,(0,0,-50),finish=.60)
    assign(select(prefix=('Wheel_Cap_Clamp_Nut_',)),5,(0,0,22),begin=.03,finish=.40)
    assign(select(prefix=('Wheel_Cap_Clamp_Screw_',)),5,(0,0,-34),begin=.60,finish=.94)
    assign(['Load_Frame'],6,begin=0,finish=.04,parent='Frame_Bench')
    assign(select('Body_IMU',prefix=('IMU_Insert_',)),6,(0,0,-22),begin=.06,finish=.30,parent='Frame_Bench')
    assign(select(prefix=('IMU_Screw_',)),6,(0,0,-24),begin=.25,finish=.45,parent='Frame_Bench')
    assign(select('Wheel_Buck','Head_Buck',prefix=('Wheel_Buck_Insert_','Head_Buck_Insert_')),6,(0,0,-22),begin=.05,finish=.30,parent='Frame_Bench')
    assign(select(prefix=('Wheel_Buck_Screw_','Head_Buck_Screw_')),6,(0,0,-28),begin=.26,finish=.44,parent='Frame_Bench')
    sr=stages[5];sp=sr['end']-sr['start'];r=roots['Frame_Bench']
    for fr,xyz in [(1,(0,-70,45)),(sr['start']+round(sp*.45),(0,-70,45)),(sr['start']+round(sp*.70),(0,0,45)),(sr['start']+round(sp*.86),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    assign(select(prefix=('Drive_L_', 'Drive_R_')),6,(0,0,22),begin=.87,finish=.98)
    assign(['Yaw_Base'],8,finish=.04,parent='Fixed_Bridge')
    for sign in [-1,1]:
        assign(['Yaw_Base_'+str(sign)+'_Nut'],8,(-sign*12,0,0),begin=.02,finish=.22,parent='Fixed_Bridge')
    s=stages[7];r=roots['Fixed_Bridge']
    for fr,xyz in [(1,(0,0,44)),(s['start']+16,(0,0,44)),(s['start']+39,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    for sign in [-1,1]:
        assign(['Yaw_Base_'+str(sign)+'_Screw'],8,(sign*23,0,0),begin=.62,finish=.95)
    assign(select('MCU_Carrier',prefix=('Carrier_Insert_',)),7,(0,0,30),finish=.42)
    assign(select(prefix=('Carrier_Screw_',)),7,(0,0,24),begin=.34,finish=.60)
    assign(['MCU_Motion'],7,(0,0,35),begin=.51,finish=.87)
    assign(['Power_Board_H2_Insert','Power_Board_H3_Insert'],7,(0,0,12),finish=.18)
    assign(['Power_Module'],7,(0,0,26),begin=.20,finish=.67)
    assign(['Power_Board_H2_Screw','Power_Board_H3_Screw'],7,(0,0,22),begin=.69,finish=.97)
    assign(select('Battery_Tray',prefix=('Battery_Pad_', 'Battery_Retainer_Insert_')),9,(0,80,0),begin=.02,finish=.44)
    assign(['Battery'],9,(0,85,0),begin=.43,finish=.82)
    for sign in [-1,1]:assign(['Battery_Retainer_Screw_'+str(sign)],9,(sign*22,0,0),begin=.78,finish=.96)
    assign(['Yaw_Bearing'],10,(0,0,32),begin=.02,finish=.29)
    assign(select('Pitch_Yoke','Yaw_Reaction_Link','Yaw_Horn',prefix=('Yaw_Reaction_Clamp_',)),10,begin=.0,finish=.05,parent='Yaw_Group')
    s=stages[9];r=roots['Yaw_Group']
    for fr,xyz in [(1,(0,0,64)),(s['start']+22,(0,0,64)),(s['start']+58,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    assign(select(prefix=('Yaw_Reaction_Retainer_',)),10,(0,24,0),begin=.77,finish=.96)
    assign(['Yaw_Servo','Yaw_Output'],11,(0,0,38),begin=.01,finish=.57)
    assign(['Yaw_Lock_Screw'],11,(0,0,-22),begin=.58,finish=.90)
    assign(['Pitch_Servo','Pitch_Output'],11,(-40,0,0),begin=.18,finish=.83)
    for side,sign in [('L',-1),('R',1)]:assign(['Pitch_Bearing_'+side],11,(sign*25,0,0),begin=.45,finish=.95)
    assign(select(prefix=('Head_Yaw_Ear_',)),11,(0,0,22),begin=.65,finish=.99)
    assign(['Pitch_Cradle','Pitch_Horn'],12,(0,0,42),begin=.02,finish=.52)
    for side,sign in [('L',-1),('R',1)]:assign(['Pitch_Trunnion_'+side],12,(sign*28,0,0),begin=.52,finish=.90)
    assign(['Pitch_Lock_Screw'],12,(-25,0,0),begin=.72,finish=.97)
    assign(['Display_Frame','Display_PCB'],13,(0,52,12),begin=.02,finish=.56)
    assign([n for n in actors if n.startswith('Face_Joint_') and n.endswith('_Nut')],13,(0,52,12),begin=.02,finish=.56)
    assign(['Camera_PCB','Camera_Lens'],13,(0,45,12),begin=.16,finish=.66)
    assign(select('CAM_Mainboard',prefix=('Onboard_MIC_',)),13,(0,-44,15),begin=.05,finish=.68)
    for sign in [-1,1]:
        assign([n for n in actors if n.startswith(f'Face_Joint_{sign}_') and n.endswith('_Screw')],13,(sign*25,0,0),begin=.72,finish=.98)
    # Pixels remain display content, not printable or structural parts.
    assign([n for n,o in actors.items() if o.get('role')=='display_content'],13,(0,52,12),begin=.02,finish=.56)
    assign([n for n,o in actors.items() if o.get('role')=='routing'],14,begin=.01,finish=.08)
    assign(['Head_Rear'],14,(0,-68,0),begin=.18,finish=.85)
    assign(['Head_Front','Face_Mask','Face_Protector','Camera_Window'],14,(0,68,0),begin=.27,finish=.95)
    assign(select('Body_Upper',prefix=('Frame_Insert_','Speaker_Insert_', 'Rear_Interface_Insert_')),15,begin=.01,finish=.03)
    assign(['Speaker_Gasket'],15,(0,-28,-8),begin=.10,finish=.33)
    assign(['Speaker'],15,(0,-34,-10),begin=.27,finish=.52)
    assign(select(prefix=('Speaker_Screw_',)),15,(0,-46,-12),begin=.71,finish=.96)
    assign(['Rear_Interface_PCB','USB_Receptacle','Power_Switch'],15,(0,0,-24),begin=.20,finish=.68)
    assign(select(prefix=('Rear_Interface_Screw_',)),15,(0,0,-20),begin=.69,finish=.94)
    assign(select('Body_Lower',prefix=('Shell_Insert_',)),16,(0,0,-72),begin=.08,finish=.72)
    assign(select(prefix=('Frame_Screw_', 'Shell_Screw_')),16,(0,0,18),begin=.74,finish=.97)
    for side,sign in [('L',-1),('R',1)]:
        assign(['Wheel_Spacer_'+side+'_1'],17,(sign*60,0,0),begin=.01,finish=.34)
        assign(['Wheel_Hub_'+side,'Tire_'+side],17,(sign*84,0,0),begin=.30,finish=.72)
        assign(['Wheel_End_Washer_'+side],17,(sign*38,0,0),begin=.65,finish=.86)
        assign(['Wheel_End_Screw_'+side],17,(sign*42,0,0),begin=.77,finish=.98)
    missing=set(actors)-set(assignments)
    if missing:raise ValueError('Unassigned parts: '+str(sorted(missing)))
    # Isolated upper-shell accessory bench shot; cut back to the assembly.
    bench=stages[14]
    for n,step in assignments.items():
        if step<15:
            o=actors[n];vis(o,bench['start']-1,True);vis(o,bench['start'],False);vis(o,bench['end']+1,True)
    for o in list(actors.values())+list(roots.values()):
        smooth(o)
        if o.animation_data and o.animation_data.action:tagged(o.animation_data.action)
    # Reuse source studio lighting, with independently editable light objects.
    for src in source_scene.objects:
        if src.type=='LIGHT':
            o=tagged(src.copy());o.data=tagged(src.data.copy());o.name=AP+src.name.removeprefix(PREFIX);studio.objects.link(o)
    font_path='/System/Library/Fonts/Hiragino Sans GB.ttc'
    font=bpy.data.fonts.load(font_path,check_existing=True) if Path(font_path).exists() else None
    if font:tagged(font);font.pack()
    def label(name,body,cam,xy,size,material,stage):
        data=tagged(bpy.data.curves.new(AP+name,'FONT'));data.body=body;data.size=size;data.align_y='CENTER';data.space_character=1.06
        if font:data.font=font
        o=tagged(bpy.data.objects.new(AP+name,data));hud.objects.link(o);o.parent=cam;o.location=(xy[0],xy[1],-3);data.materials.append(material)
        vis(o,1,False)
        if stage['start']>1:vis(o,stage['start']-1,False)
        vis(o,stage['start'],True);vis(o,stage['end']+1,False);smooth(o)
        if o.animation_data:tagged(o.animation_data.action)
    shots={
        'wheel':((360,650,280),(0,0,53),530),
        'drive':((360,600,225),(0,0,27),465),
        'drive_close':((240,390,-120),(0,0,53),330),
        'frame':((290,-520,15),(0,-10,123),475),
        'body':((320,520,270),(0,0,114),405),
        'head':((320,520,325),(0,0,210),480),
        'optics':((300,540,325),(0,0,224),490),
        'head_shell':((340,560,325),(0,0,222),470),
        'shell_bench':((260,-370,-190),(0,0,134),350),
        'whole':((480,720,350),(0,0,148),660),
        'hero':((380,570,300),(0,0,148),635),
    }
    for s in stages:
        loc,target,scale=shots[s['shot']]
        if s['index'] in [2,3]:
            loc,target,scale=(490,530,225),(148,0,55),230
        if s['index']==7:
            # See the actual populated component faces, not just PCB undersides.
            loc,target,scale=(260,400,330),(0,0,116),370
        data=tagged(bpy.data.cameras.new(AP+f'Camera_{s["index"]:02d}'))
        cam=tagged(bpy.data.objects.new(data.name,data));studio.objects.link(cam)
        cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
        data.type='ORTHO';data.ortho_scale=scale;data.clip_start=.1;data.clip_end=5000
        marker=scene.timeline_markers.new(f'{s["index"]:02d} {s["title"]}',frame=s['start']);marker.camera=cam
        if s['index']==1:scene.camera=cam
        hw=scale/2;hh=scale*9/32
        label(f'Title_{s["index"]}',f'MORI  /  {s["index"]:02d}  {s["title"]}',cam,(-hw*.91,hh*.84),scale*.023,accent,s)
        label(f'Note_{s["index"]}',s['note'],cam,(-hw*.91,hh*.69),scale*.0147,lettering,s)
        label(f'Footer_{s["index"]}','装配示意 · 路径未作全程碰撞验证   |   内部橙色：待确认件',cam,(-hw*.91,-hh*.87),scale*.012,note_mat,s)
        if s['shot']=='hero':
            for fr,cl in [(s['start'],loc),(s['end'],(530,360,295))]:
                cam.location=cl;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert(data_path='location',frame=fr);cam.keyframe_insert(data_path='rotation_euler',frame=fr)
            smooth(cam);tagged(cam.animation_data.action)
    # Verify actual animation endpoint against every original object matrix.
    scene.frame_set(scene.frame_end);bpy.context.view_layer.update()
    errors={n:float(np.max(np.abs(np.asarray(o.matrix_world)-np.asarray(bases[n])))) for n,o in actors.items()}
    assert max(errors.values())<.0001, errors
    assert all(not o.hide_render and not o.hide_viewport for o in actors.values())
    assert all(o.data is original_by_id[n].data for n,o in actors.items())
    assert signature(originals)==baseline
    scene['actor_count']=len(actors);scene['stage_count']=len(stages)
    guide=f'''MORI 装配动画 / {P['revision']}

当前场景：{SCENE_NAME}。空格播放，Shift+左方向键回到开头。
总长 {scene.frame_end/FPS:.2f} 秒，{FPS} fps，共 {scene.frame_end} 帧。
时间轴的 18 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

动画中的位移、台面预装、镜头切换仅作装配讲解。上壳附件在独立镜头预装后
切换到总装姿态，没有声称上壳可以穿过完整头部。所有帧的全程装配干涉、
工具/人手空间、软线束、紧固扭矩与真实零件公差仍未验证。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

降压器区分：第6步的外置模块是轮驱9V（D36V50F9）和头部6V（D24V22F6）。
第7步电源板上的U60/U70已集成运动5V和CAM 5V；没有另装两块外置5V模块。
依据为当前已交接P5R2原生PCB与硬件BOM，不擅自改变电源拓扑。
'''
    textblock=bpy.data.texts.get('MORI_动画使用说明') or bpy.data.texts.new('MORI_动画使用说明');textblock.clear();textblock.write(guide)
    (OUT/'README.md').write_text('# MORI 装配动画\n\n'+guide+'\n重新生成：\n\n```sh\n/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/assembly_animation.py -- --width 1280 --render stills\n/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_assembly_animation.blend -S MORI_Assembly_Animation -a\n```\n')
    script=bpy.data.texts.get('assembly_animation.py') or bpy.data.texts.new('assembly_animation.py');script.clear();script.write(Path(__file__).read_text())
    # Native saved state starts at the first assembly step, camera view ready.
    scene.frame_set(1)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.region_3d.view_camera_zoom=0
                area.spaces.active.overlay.show_extras=False
                area.spaces.active.overlay.show_relationship_lines=False
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.clip_end=5000
            if area.type=='DOPESHEET_EDITOR':area.spaces.active.show_seconds=True
    movie=OUT/'MORI_assembly.mp4'
    scene.render.image_settings.media_type='VIDEO';scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264';scene.render.ffmpeg.constant_rate_factor='MEDIUM';scene.render.ffmpeg.ffmpeg_preset='REALTIME';scene.render.ffmpeg.gopsize=24;scene.render.filepath=str(movie)
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
    report={'revision':P['revision'],'source_blend':str(source),'source_blend_sha256':source_hash,'source_is_unchanged':True,'animation_blend':str(TARGET),'source_geometry_signature':baseline,'actor_count':len(actors),'stage_count':len(stages),'fps':FPS,'frame_range':[1,scene.frame_end],'duration_seconds':scene.frame_end/FPS,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':a.samples,'final_transform_max_error_mm':max(errors.values()),'meshes_share_exact_source_data':True,'all_actors_visible_at_end':True,'stages':stages,'part_stages':assignments,'geometry_status':'PASS_ENDPOINT_AND_SOURCE_PRESERVATION','continuous_assembly_path_collision':'NOT_TESTED','rendered_video':False,'blender':bpy.app.version_string,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save_json(OUT/'manifest.json',report)
    if a.render=='stills':
        scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
        for s in stages:
            scene.frame_set(s['end']);scene.render.filepath=str(OUT/f'step_{s["index"]:02d}.png');print('ANIMATION_STILL',s['index'],flush=True);bpy.ops.render.render(write_still=True)
    elif a.render=='video':
        scene.frame_set(1);bpy.ops.render.render(animation=True)
    print('ASSEMBLY_ANIMATION_BUILT',len(actors),scene.frame_end,flush=True)


if __name__=='__main__':main()
