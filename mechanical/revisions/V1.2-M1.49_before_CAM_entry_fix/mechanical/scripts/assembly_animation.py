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
ANIMATION_REVISION = P['revision'] + '-A1'
# Each stage has a native timeline marker, camera and editable object actions.
STAGES = [
    ('轮驱分总成', 'S288 ×2；保留原配输出盘', 48, 'wheel'),
    ('连接金属法兰轴', '每侧6枚自攻螺钉位置示意；原厂孔配合待确认，金属轴不打印', 66, 'wheel'),
    ('轴承与内隔套', '内轴承 → 4.5 mm 金属隔套 → 外轴承；轴肩已配套调整', 72, 'wheel'),
    ('装入轮驱上座', '平直侧壁上座；两套电机 / 轴 / 轴承组件由下方进入', 84, 'drive'),
    ('固定共用底盖', '平板底盖 + 连续轴承座；4 枚 M3 从底面锁紧', 60, 'drive_close'),
    ('主托板与底面电路板', 'IMU + 轮驱9V / 头部6V模块；底面预装后接轮驱', 96, 'frame'),
    ('基板与电源板装件', 'P5R6电源板已集成运动5V + CAM 5V；两枚M2×6固定', 96, 'body'),
    ('承重桥落座并锁紧', '上壳保持15°／抬高14mm；桥单独下降18mm，再锁两枚M3', 96, 'bridge_lock'),
    ('电池托盘与电池', '台面套好20mm绑带，再把电池与托盘一起滑入；左右M2限位', 66, 'body'),
    ('Yaw 转动座台面预装', '离机装入4枚M2螺母；C压板从侧面套入转动座', 78, 'head_bench'),
    ('双舵机台面预装', 'Pitch先在右侧上方下放，再左移30mm；锁紧后装倒置Yaw', 144, 'head_bench'),
    ('CAM固定与头托', '四枚DIN912 M2×5；用1.5mm短边L扳手锁紧，显示架及头壳后装', 96, 'head'),
    ('显示与摄像头', '先在台面用3枚M2×12固定LCD；装叉架，再插入相机，无独立压盖', 78, 'optics'),
    ('头壳合拢 · 走线待设计', '前壳两枚M2下锁沉入上侧；后壳两枚M2锁拼缝，面圈已并入前壳', 78, 'head_shell'),
    ('上壳附件台面预装', 'SP3040由两枚M2×5固定在上壳；耳尺寸估算；后接口板一起预装', 84, 'shell_bench'),
    ('下壳合装', '车轮尚未安装；下壳从底部合入，四枚拼缝螺钉由下方锁紧', 66, 'whole'),
    ('安装车轮', '外隔套 → 轮胎 / 轮毂 → 垫圈与端螺钉', 78, 'whole'),
    ('当前模型总览 · 装配未定型', f'{P["revision"]}；舵盘接口、完整线束及实物配合仍待完成', 96, 'hero'),
    ('上壳与承重桥协同装入', '桥预装螺母与6806轴承；上壳倾15°、桥保持水平，分别托住后下移／前移', 168, 'shell_install'),
    ('上壳回正并固定', '桥已锁紧；上壳从15°／抬高14mm回正落位，再锁框架螺钉', 96, 'shell_settle'),
    ('头部驱动座装入', '转动座连同C压板一起下放；俯仰头托尚未安装', 78, 'head'),
    ('锁紧头身防脱压板', '转动座转60°露出孔位；从上方锁2枚M3×8，再回到零位', 156, 'retention'),
]
# Stable construction IDs; shell and bridge move independently in stages
# 19 / 8 / 20. The bridge must lock before the shell settles.
STAGE_ORDER=[1,2,3,4,5,6,7,15,19,8,20,9,10,11,21,22,12,13,14,16,17,18]


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


def same_geometry(a,b):
    if a is b:return True
    return (np.array_equal(np.asarray([v.co[:] for v in a.vertices]),np.asarray([v.co[:] for v in b.vertices]))
            and [tuple(p.vertices) for p in a.polygons]==[tuple(p.vertices) for p in b.polygons])


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
    stages = [None]*len(STAGES)
    frame = 1
    for display_i,i in enumerate(STAGE_ORDER,1):
        title,note,duration,shot=STAGES[i-1]
        stages[i-1]=dict(index=i,display_index=display_i,title=title,note=note,start=frame,end=frame+duration-1,shot=shot)
        frame += duration
    scene.frame_start = 1; scene.frame_end = frame - 1
    scene['presentation_only'] = True
    scene['source_revision'] = P['revision']
    scene['source_blend'] = str(source)
    scene['animation_revision'] = ANIMATION_REVISION
    scene['motion_qualification'] = 'Independent upper shell and level bridge follow prearrival_closure/dual_body_sequence.json (407 sampled nominal positions and two M3 tool paths). The bench-to-insertion-start is a scene cut; full harness, hands and other illustrative stages are not qualified.'
    def collection(name):
        c = tagged(bpy.data.collections.new(AP + name)); scene.collection.children.link(c); return c
    stagecols = {s['index']:collection(f'{s["index"]:02d}_{s["title"]}') for s in stages}
    controls = collection('CONTROLS'); studio = collection('STUDIO'); hud = collection('CAPTIONS')
    roots = {}
    def root(name):
        o = tagged(bpy.data.objects.new(AP+name,None)); controls.objects.link(o)
        o.empty_display_type = 'PLAIN_AXES'; o.empty_display_size = 8; roots[name] = o; return o
    for n in ['Wheel_L','Wheel_R','Frame_Bench','Fixed_Bridge','Yaw_Group','Battery_Bench','Head_Bench','Optics_Bench','Upper_Shell']:
        root(n)
    root('Yaw_Turn').parent=roots['Yaw_Group']
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
    for n in select(prefix=('Drive_L_', 'Drive_R_')):
        if n.endswith('_Nut'):
            # Insert before the frame closes the bearing surface.
            sign=1 if '_8_' in n else -1
            assign([n],5,(0,sign*18,0),begin=.62,finish=.95)
        else:assign([n],6,(0,0,22),begin=.87,finish=.98)
    # Preassembled bridge arrives inside the tilted upper shell at the camera
    # cut. The independent roots below reproduce the audited two-body path.
    assign(['Yaw_Base','Yaw_Bearing','Yaw_Base_-1_Nut','Yaw_Base_1_Nut','Yaw_Keeper_Insert_0','Yaw_Keeper_Insert_1'],19,begin=0,finish=0,parent='Fixed_Bridge')
    for sign in [-1,1]:
        assign(['Yaw_Base_'+str(sign)+'_Screw'],8,(sign*25,0,0),begin=.50,finish=.80)
    assign(select('MCU_Carrier',prefix=('Carrier_Insert_',)),7,(0,0,30),finish=.42)
    assign(select(prefix=('Carrier_Screw_',)),7,(0,0,24),begin=.34,finish=.60)
    assign(select(prefix=('Socket_',)),7,(0,0,30),begin=.42,finish=.62)
    assign(select('MCU_Motion','E_Straight_Header'),7,(0,0,35),begin=.64,finish=.94)
    assign(['Power_Board_H2_Insert','Power_Board_H3_Insert'],7,(0,0,12),finish=.18)
    assign(['Power_Module'],7,(0,0,26),begin=.20,finish=.67)
    assign(['Power_Board_H2_Screw','Power_Board_H3_Screw'],7,(0,0,22),begin=.69,finish=.97)
    assign([n for n in select('Battery_Tray',prefix=('Battery_Pad_', 'Battery_Retainer_Insert_')) if n!='Battery_Pad_Top'],9,begin=.02,finish=.08,parent='Battery_Bench')
    assign(['Battery'],9,(0,0,25),begin=.1,finish=.32,parent='Battery_Bench')
    assign(['Battery_Pad_Top'],9,(0,0,20),begin=.34,finish=.46,parent='Battery_Bench')
    assign(['Battery_Strap'],9,begin=.47,finish=.5,parent='Battery_Bench')
    s=stages[8];span=s['end']-s['start'];r=roots['Battery_Bench']
    for fr,xyz in [(1,(0,80,0)),(s['start']+round(span*.53),(0,80,0)),(s['start']+round(span*.78),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    for sign in [-1,1]:assign(['Battery_Retainer_Screw_'+str(sign)],9,(sign*22,0,0),begin=.78,finish=.96)
    assign(select('Pitch_Yoke','Yaw_Reaction_Link','Yaw_Horn',prefix=('Yaw_Reaction_Clamp_',)),10,begin=.0,finish=.05,parent='Yaw_Group')
    # Seat nuts on the detached yoke before lowering it into the fixed bridge.
    for n,offset in [('Head_Pitch_Ear_0_Nut',(0,12,0)),('Head_Pitch_Ear_1_Nut',(-12,0,0)),('Head_Yaw_Ear_0_Nut',(0,12,0)),('Head_Yaw_Ear_1_Nut',(0,0,-12))]:
        assign([n],10,offset,begin=.06,finish=.24,parent='Yaw_Group')
    assign(['Yaw_Anti_Lift_Keeper'],10,(0,60,0),begin=.27,finish=.94,parent='Yaw_Group')
    assign(['Yaw_Keeper_Screw_0','Yaw_Keeper_Screw_1'],22,(0,0,35),begin=.32,finish=.60,stagger=2)
    s=stages[21];r=roots['Yaw_Turn'];span=s['end']-s['start']
    for fr,angle in [(1,0),(s['start']+8,0),(s['start']+30,60),(s['start']+104,60),(s['end']-5,0),(scene.frame_end,0)]:
        r.rotation_euler.z=math.radians(angle);r.keyframe_insert(data_path='rotation_euler',frame=fr)
    s=stages[20];r=roots['Yaw_Group']
    for fr,xyz in [(1,(0,0,64)),(s['start']+8,(0,0,64)),(s['start']+56,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    assign(select(prefix=('Yaw_Reaction_Retainer_',)),21,(0,24,0),begin=.78,finish=.98)
    for side,sign in [('L',-1),('R',1)]:assign(['Pitch_Bearing_'+side],11,(sign*25,0,0),begin=.01,finish=.15,parent='Yaw_Group')
    assign([n for n in actors if n.startswith('Head_Pitch_Ear_') and n.endswith('_Insert')],11,(15,0,0),begin=.01,finish=.16)
    assign([n for n in actors if n.startswith('Head_Yaw_Ear_') and n.endswith('_Insert')],11,(0,0,15),begin=.01,finish=.16)
    assign(['Pitch_Servo','Pitch_Output'],11,(30,0,60),begin=.18,finish=.42,parent='Yaw_Group')
    sp=stages[10];span=sp['end']-sp['start']
    for n in ['Pitch_Servo','Pitch_Output']:
        base=bases[n].to_translation()
        move(actors[n],sp['start']+round(span*.30),base+Vector((30,0,0)))
    assign([n for n in actors if n.startswith('Head_Pitch_Ear_') and n.endswith('_Screw')],11,(22,0,0),begin=.43,finish=.56,parent='Yaw_Group')
    assign(['Yaw_Servo','Yaw_Output'],11,(0,0,38),begin=.60,finish=.81,parent='Yaw_Group')
    assign(['Yaw_Lock_Screw'],11,(0,0,-22),begin=.82,finish=.97,parent='Yaw_Group')
    assign([n for n in actors if n.startswith('Head_Yaw_Ear_') and n.endswith('_Screw')],11,(0,0,22),begin=.82,finish=.97,parent='Yaw_Group')
    assign(['Pitch_Cradle','Pitch_Horn'],12,begin=.02,finish=.06,parent='Head_Bench')
    assign(select(prefix=('Head_Cradle_Insert_',)),12,(0,0,12),begin=.04,finish=.16,parent='Head_Bench')
    assign(select(prefix=('CAM_Mount_Insert_',)),12,(0,12,0),begin=.04,finish=.15,parent='Head_Bench')
    assign(select('CAM_Mainboard',prefix=('Onboard_MIC_',)),12,(0,24,0),begin=.18,finish=.35,parent='Head_Bench')
    assign(select(prefix=('CAM_Mount_Screw_',)),12,(0,18,0),begin=.37,finish=.5,parent='Head_Bench')
    s=stages[11];span=s['end']-s['start'];r=roots['Head_Bench']
    for fr,xyz in [(1,(0,0,42)),(s['start']+round(span*.52),(0,0,42)),(s['start']+round(span*.75),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    for side,sign in [('L',-1),('R',1)]:assign(['Pitch_Trunnion_'+side],12,(sign*28,0,0),begin=.77,finish=.93)
    assign(['Pitch_Lock_Screw'],12,(-25,0,0),begin=.9,finish=.99)
    assign(['Display_Frame','Display_PCB'],13,begin=.02,finish=.04,parent='Optics_Bench')
    from optics_mount import display_transform
    optical_axis=display_transform().to_3x3()@Vector((0,1,0))
    assign(select(prefix=('LCD_Mount_Screw_',)),13,-optical_axis*20,begin=.06,finish=.27,parent='Optics_Bench')
    s=stages[12];span=s['end']-s['start'];r=roots['Optics_Bench']
    for fr,xyz in [(1,(0,52,12)),(s['start']+round(span*.3),(0,52,12)),(s['start']+round(span*.56),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    assign([n for n in actors if n.startswith('Face_Joint_') and n.endswith('_Nut')],13,begin=.02,finish=.04,parent='Optics_Bench')
    assign(['Camera_PCB','Camera_Lens'],13,(0,24,4.232),begin=.58,finish=.80)
    for sign in [-1,1]:
        assign([n for n in actors if n.startswith(f'Face_Joint_{sign}_') and n.endswith('_Screw')],13,(sign*25,0,0),begin=.72,finish=.98)
    # Pixels remain display content, not printable or structural parts.
    assign([n for n,o in actors.items() if o.get('role')=='display_content'],13,begin=.02,finish=.04,parent='Optics_Bench')
    assign([n for n,o in actors.items() if o.get('role')=='routing'],14,begin=.01,finish=.08)
    assign(select('Head_Front',prefix=('Head_Seam_Insert_',)),14,(0,68,0),begin=.08,finish=.44)
    assign(select(prefix=('Head_Cradle_Screw_',)),14,(0,0,30),begin=.45,finish=.64)
    assign(['Head_Rear'],14,(0,-68,0),begin=.57,finish=.80)
    assign(select(prefix=('Head_Seam_Screw_',)),14,(0,-30,0),begin=.81,finish=.97)
    assign(select('Body_Upper',prefix=('Frame_Insert_','Shell_Insert_','Speaker_Insert_', 'Rear_Interface_Insert_')),15,begin=.01,finish=.03,parent='Upper_Shell')
    from speaker_geometry import speaker_transform
    speaker_back=speaker_transform().to_3x3()@Vector((0,-1,0))
    assign(['Speaker_Gasket'],15,speaker_back*28,begin=.10,finish=.33,parent='Upper_Shell')
    assign(['Speaker'],15,speaker_back*34,begin=.27,finish=.52,parent='Upper_Shell')
    assign(select(prefix=('Speaker_Screw_',)),15,speaker_back*46,begin=.71,finish=.96,parent='Upper_Shell')
    assign(['Rear_Interface_PCB','USB_Receptacle','Power_Switch'],15,(0,0,-24),begin=.20,finish=.68,parent='Upper_Shell')
    assign(select(prefix=('Rear_Interface_Screw_',)),15,(0,0,-20),begin=.69,finish=.94,parent='Upper_Shell')
    assign(['Body_Lower'],16,(0,0,-72),begin=.08,finish=.72)
    assign(select(prefix=('Shell_Screw_',)),16,(0,0,-25),begin=.74,finish=.97)
    assign(select(prefix=('Frame_Screw_',)),20,(0,0,-25),begin=.73,finish=.98)
    # Upper shell tilts about the body datum; the bridge stays level. Use the
    # checked 140→14 mm shell lift and 144→18 mm bridge lift. Only after both
    # move forward14 does the bridge seat and the two transverse bolts enter.
    r=roots['Upper_Shell'];s=stages[18];origin=Vector((0,0,D['body_z']))
    def shell_pose(fr,angle,y,z):
        r.matrix_world=Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-origin)
        r.keyframe_insert(data_path='location',frame=fr);r.keyframe_insert(data_path='rotation_euler',frame=fr)
    shell_pose(1,0,0,0);shell_pose(stages[14]['end'],0,0,0)
    coordinated=[(s['start'],15,-14,140,144),(s['start']+12,15,-14,140,144),
                 (s['start']+104,15,-14,14,18),(s['start']+110,15,-14,14,18),
                 (s['start']+146,15,0,14,18),(s['end'],15,0,14,18)]
    for fr,angle,y,z,bz in coordinated:
        shell_pose(fr,angle,y,z);move(roots['Fixed_Bridge'],fr,(0,y,bz))
    lock=stages[7];settle=stages[19]
    for fr,z in [(lock['start'],18),(lock['start']+8,18),(lock['start']+36,0),
                 (lock['end'],0),(scene.frame_end,0)]:move(roots['Fixed_Bridge'],fr,(0,0,z))
    for fr in [lock['start'],lock['end'],settle['start'],settle['start']+8]:shell_pose(fr,15,0,14)
    # Dense angular keys preserve the body-centred trajectory between saved
    # frames. Saved animation matrices are collision-screened after readback.
    f0=settle['start']+8;f1=settle['start']+62
    for t in np.linspace(0,1,109):shell_pose(f0+(f1-f0)*t,15*(1-t),0,14*(1-t))
    shell_pose(settle['end'],0,0,0)
    shell_pose(scene.frame_end,0,0,0)
    for side,sign in [('L',-1),('R',1)]:
        assign(['Wheel_Spacer_'+side+'_1'],17,(sign*60,0,0),begin=.01,finish=.34)
        assign(['Wheel_Hub_'+side,'Tire_'+side],17,(sign*84,0,0),begin=.30,finish=.72)
        assign(['Wheel_End_Washer_'+side],17,(sign*38,0,0),begin=.65,finish=.86)
        assign(['Wheel_End_Screw_'+side],17,(sign*42,0,0),begin=.77,finish=.98)
    # The yaw assembly and its preinstalled pitch output turn together before
    # the pitch cradle is fitted. Keeper, yaw bearing, yaw horn/reaction and
    # yaw output remain fixed. All rotate about Z at XY0.
    for n,o in actors.items():
        if (original_by_id[n].get('group')=='yaw' or n=='Pitch_Output') and o.parent==roots['Yaw_Group']:
            o.parent=roots['Yaw_Turn']
    missing=set(actors)-set(assignments)
    if missing:raise ValueError('Unassigned parts: '+str(sorted(missing)))
    # Isolated upper-shell accessory bench shot; cut back to the assembly.
    bench=stages[14]
    for n,step in assignments.items():
        if stages[step-1]['end']<bench['start']:
            o=actors[n];vis(o,bench['start']-1,True);vis(o,bench['start'],False);vis(o,bench['end']+1,True)
    # A genuine isolated bench shot makes the detached servo work visible;
    # return to the chassis only when the completed drive seat is lowered.
    bench_start=stages[9]['start'];bench_end=stages[10]['end']
    for n,step in assignments.items():
        if stages[step-1]['end']<bench_start:
            o=actors[n];vis(o,bench_start-1,True);vis(o,bench_start,False);vis(o,bench_end+1,True)
    # Presentation-only object material overrides reveal the bridge through
    # the shell, without cutting, hiding or changing the source meshes.
    # These two source meshes have no material slot; copy their exact geometry
    # before adding display slots, preserving the original scene as well.
    for n in ['Yaw_Base','Body_Upper']:
        actors[n].data=tagged(actors[n].data.copy())
        actors[n].data.name=AP+n+'_DisplayMesh'
    bridge_mat=mat('Bridge_Highlight',(.045,.29,.39))
    actors['Yaw_Base'].data.materials.clear();actors['Yaw_Base'].data.materials.append(bridge_mat)
    upper_mat=mat('Upper_Shell_Overlay',(.84,.86,.85))
    nt=upper_mat.node_tree;bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
    transparent=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(transparent.outputs[0],mix.inputs[1]);nt.links.new(bsdf.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],output.inputs['Surface'])
    upper_mat.surface_render_method='DITHERED'
    for fr,value in [(1,1),(stages[18]['start']-1,1),(stages[18]['start'],.20),
                     (stages[19]['end']-10,.20),(stages[19]['end'],1),
                     (stages[20]['start']-1,1),(stages[20]['start'],.16),(stages[21]['end'],.16),(stages[11]['start'],1),(scene.frame_end,1)]:
        mix.inputs[0].default_value=value;mix.inputs[0].keyframe_insert(data_path='default_value',frame=fr)
    for fc in curves(nt):
        for k in fc.keyframe_points:k.interpolation='LINEAR'
    if nt.animation_data:tagged(nt.animation_data.action)
    actors['Body_Upper'].data.materials.clear();actors['Body_Upper'].data.materials.append(upper_mat)
    for o in list(actors.values())+list(roots.values()):
        smooth(o)
        if o.animation_data and o.animation_data.action:tagged(o.animation_data.action)
    for linear_object in [roots['Upper_Shell'],roots['Fixed_Bridge'],actors['Pitch_Servo'],actors['Pitch_Output']]:
        for fc in curves(linear_object):
            for k in fc.keyframe_points:k.interpolation='LINEAR'
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
        'retention':((185,270,345),(0,0,188),260),
        'head_bench':((320,520,430),(0,0,290),410),
        'optics':((300,540,325),(0,0,224),490),
        'head_shell':((340,560,325),(0,0,222),470),
        'shell_bench':((260,-370,-190),(0,0,134),350),
        'shell_install':((380,-550,355),(0,0,184),800),
        'bridge_lock':((285,-420,300),(0,0,128),470),
        'shell_settle':((330,-500,285),(0,0,125),430),
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
        marker=scene.timeline_markers.new(f'{s["display_index"]:02d} {s["title"]}',frame=s['start']);marker.camera=cam
        if s['index']==1:scene.camera=cam
        hw=scale/2;hh=scale*9/32
        label(f'Title_{s["index"]}',f'MORI  /  {s["display_index"]:02d}  {s["title"]}',cam,(-hw*.91,hh*.84),scale*.023,accent,s)
        label(f'Note_{s["index"]}',s['note'],cam,(-hw*.91,hh*.69),scale*.0147,lettering,s)
        footer='装配示意 · 完整线束／实物配合未完成   |   内部橙色：待确认件'
        if s['index'] in [19,8,20]:footer='蓝色：承重桥；上壳半透明显示   |   两件分别支承，线束随动／人工支承待验证'
        if s['index']==22:footer='固定C压板防止头部上拔；保留0.4mm间隙   |   舵盘叠层／线束及实物强度待验证'
        if s['index']==7:footer='P5R7基板 / 后接口板；核心板元件面向上   |   E排针配套仍待核'
        label(f'Footer_{s["index"]}',footer,cam,(-hw*.91,-hh*.87),scale*.012,note_mat,s)
        if s['shot']=='hero':
            for fr,cl in [(s['start'],loc),(s['end'],(530,360,295))]:
                cam.location=cl;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.keyframe_insert(data_path='location',frame=fr);cam.keyframe_insert(data_path='rotation_euler',frame=fr)
            smooth(cam);tagged(cam.animation_data.action)
    # Verify actual animation endpoint against every original object matrix.
    scene.frame_set(scene.frame_end);bpy.context.view_layer.update()
    errors={n:float(np.max(np.abs(np.asarray(o.matrix_world)-np.asarray(bases[n])))) for n,o in actors.items()}
    assert max(errors.values())<.0001, errors
    assert all(not o.hide_render and not o.hide_viewport for o in actors.values())
    assert all(same_geometry(o.data,original_by_id[n].data) for n,o in actors.items())
    assert signature(originals)==baseline
    scene['actor_count']=len(actors);scene['stage_count']=len(stages)
    guide=f'''MORI 装配动画 / {ANIMATION_REVISION}

当前场景：{SCENE_NAME}。空格播放，Shift+左方向键回到开头。
总长 {scene.frame_end/FPS:.2f} 秒，{FPS} fps，共 {scene.frame_end} 帧。
时间轴的 {len(stages)} 个中文标记同时切换对应相机。每个零件保留独立物体与关键帧。
在 Outliner 按步骤展开集合；选零件，在 Dope Sheet / Graph Editor 调整时间。
原始 MORI_V1_Assembly 场景保留真实总装与运动轴，可切回检查尺寸。

上壳附件先在台面预装，镜头切换至桥已放入壳内、两件分别支承的装入起点。
第9步：上壳倾15°、桥保持水平，共同下移，再向前移动14mm。
第10步：上壳保持抬高14mm不动；桥单独下降18mm，装入并锁两枚M3。
第11步：桥已固定，上壳沿15°／14mm联动轨迹回正落位，再锁框架螺钉。
三步名义路径依据407个组合位置的检查；保存后的关键帧另以半帧抽样实体复核。
双舵机先在离机座上锁紧；Pitch先在X+30mm处下放，再向左平移到位。
C压板先从侧面套到转动座，随驱动座一起下放。第16步转动座转60°，
从上方锁两枚M3×8后回正，再安装俯仰头部。固定压板不随Yaw转动。
M1.49采用6806ZZ轴承（30×42×7mm）；压板配对孔位为X±26.2mm，
外径60.4mm。颈部11条局部导线空间检查不代表完整线束已完成。
拆卸需先移除俯仰头部，松开压板和反力连接后上提，不是整头快拆。
其他位移、台面预装与镜头切换仅作装配讲解。全动画的连续扫掠、人手／夹具、
完整软线束、紧固扭矩与真实零件公差仍未验证。头部舵盘／短轴仍未定型。
橙色表示未完整确认的部件；没有缩放采购件或改变候选 STL。

降压器区分：第6步的外置模块是轮驱9V（D36V50F9）和头部6V（D24V22F6）。
第7步电源板上的U60/U70已集成运动5V和CAM 5V；没有另装两块外置5V模块。
本视频采用{P["revision"]}主模型，运动基板与后接口板已更新为P5R7；电源P5R6、IMU P5R4。
WeAct元件面朝上、排针朝下；先放三组排母，再插入核心板与E直排针候选。
E排针与原厂STEP孔径资料矛盾仍为BLOCKED，11.04mm是候选叠层，不能据动画确认实物配合或下单。
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
    published_stages=[]
    for s in sorted(stages,key=lambda s:s['start']):published_stages.append(dict(s,index=s['display_index'],source_step=s['index']))
    # Gallery filenames/metadata follow chronological display order.
    published_assignments={n:stages[step-1]['display_index'] for n,step in assignments.items()}
    for n,step in published_assignments.items():actors[n]['assembly_step']=step
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
    body_evidence=ROOT/'reports/head_retention_body_sequence.json'
    audit=json.loads(body_evidence.read_text())
    assert audit['status']=='PASS' and audit['source_blend_sha256']==source_hash
    report={'revision':P['revision'],'animation_revision':ANIMATION_REVISION,'source_blend':str(source),'source_blend_sha256':source_hash,'source_is_unchanged':True,'animation_blend':str(TARGET),'source_geometry_signature':baseline,'actor_count':len(actors),'stage_count':len(stages),'fps':FPS,'frame_range':[1,scene.frame_end],'duration_seconds':scene.frame_end/FPS,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':a.samples,'final_transform_max_error_mm':max(errors.values()),'meshes_share_exact_source_data':False,'all_actor_geometry_matches_source':True,'material_only_mesh_copies':['Yaw_Base','Body_Upper'],'all_actors_visible_at_end':True,'stages':published_stages,'part_stages':published_assignments,'geometry_status':'PASS_ENDPOINT_AND_SOURCE_PRESERVATION','upper_shell_path':'Two independent shell/bridge roots; lower and forward together, bridge seats and locks, shell settles last','body_sequence_evidence':str(body_evidence.relative_to(ROOT)),'body_sequence_evidence_sha256':hashlib.sha256(body_evidence.read_bytes()).hexdigest(),'body_sequence_display_stages':[9,10,11],'retention_evidence':'reports/head_axial_retention_validation.json','continuous_assembly_path_collision':'NOT_TESTED','p5r7_adopted':bool(P.get('p5r7_adoption',{}).get('enabled')),'rendered_video':False,'blender':bpy.app.version_string,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save_json(OUT/'manifest.json',report)
    if a.render=='stills':
        scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
        for s in published_stages:
            scene.frame_set(s['end']);scene.render.filepath=str(OUT/f'step_{s["index"]:02d}.png');print('ANIMATION_STILL',s['index'],flush=True);bpy.ops.render.render(write_still=True)
    elif a.render=='video':
        scene.frame_set(1);bpy.ops.render.render(animation=True)
    print('ASSEMBLY_ANIMATION_BUILT',len(actors),scene.frame_end,flush=True)


if __name__=='__main__':main()
