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
    ('承重桥落座并锁紧', '外壳未装；桥下降18mm，侧向锁紧两枚M3，车轮后装', 96, 'bridge_lock'),
    ('电池托盘与电池', '台面套好20mm绑带，再把电池与托盘一起滑入；左右M2限位', 66, 'body'),
    ('Yaw 转动座台面预装', '离机装入4枚M2螺母；C压板从侧面套入转动座', 78, 'head_bench'),
    ('双舵机台面预装', 'Pitch先在右侧上方下放，再左移30mm；锁紧后装倒置Yaw', 144, 'head_bench'),
    ('CAM固定与头托', 'USB朝右；向前错开2mm下放，抬高8mm时预接USB，再落座并锁四枚M2', 96, 'head'),
    ('显示与摄像头', '先在台面用3枚M2×12固定LCD；装叉架，再插入相机，无独立压盖', 78, 'optics'),
    ('头壳合拢 · 走线待设计', '前壳两枚M2下锁沉入上侧；后壳两枚M2锁拼缝，面圈已并入前壳', 78, 'head_shell'),
    ('前后壳附件台面预装', '前后壳转向内侧展示；喇叭、接口板分别预装，下一镜恢复装配方向', 108, 'shell_bench'),
    ('前壳平移合入', '从正前方平移装入前壳；底部一体插舌随后与后壳配合，完整软线随动待验证', 96, 'whole'),
    ('安装车轮', '外隔套 → 轮胎 / 轮毂 → 垫圈与端螺钉', 78, 'whole'),
    ('当前模型总览 · 装配未定型', f'{P["revision"]}；舵盘接口、完整线束及实物配合仍待完成', 96, 'hero'),
    ('承重桥单独装入', '桥预装螺母、嵌件与6806轴承；保持水平，先下移再前移14mm', 168, 'shell_install'),
    ('后壳合入并锁紧', '后壳沿+Y合入；从四个底部工具孔锁框架螺钉，取消旧拼缝五金', 120, 'shell_settle'),
    ('头部驱动座装入', '转动座连同C压板一起下放；俯仰头托尚未安装', 78, 'head'),
    ('锁紧头身防脱压板', '转动座转60°露出孔位；从上方锁2枚M3×8，再回到零位', 156, 'retention'),
]
# Stable stage IDs preserve head/wheel subassemblies; bridge locks before front/rear shells.
STAGE_ORDER=[1,2,3,4,5,6,7,19,8,9,10,11,21,22,12,13,14,15,16,20,17,18]


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
            elif o.get('cam_path_linear') and fc.data_path=='location':
                k.interpolation = 'LINEAR'
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
    scene['motion_qualification'] = 'Current front/rear shell modules translate along Y; frame screws enter from below. Saved matrices are checked at half frames. Full flexible harness, human support and physical fits are not qualified.'
    def collection(name):
        c = tagged(bpy.data.collections.new(AP + name)); scene.collection.children.link(c); return c
    stagecols = {s['index']:collection(f'{s["index"]:02d}_{s["title"]}') for s in stages}
    controls = collection('CONTROLS'); studio = collection('STUDIO'); hud = collection('CAPTIONS')
    roots = {}
    def root(name):
        o = tagged(bpy.data.objects.new(AP+name,None)); controls.objects.link(o)
        o.empty_display_type = 'PLAIN_AXES'; o.empty_display_size = 8; roots[name] = o; return o
    for n in ['Wheel_L','Wheel_R','Frame_Bench','Fixed_Bridge','Yaw_Group','Battery_Bench','Head_Bench','Optics_Bench','Front_Shell','Rear_Shell']:
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
    # The bridge is preassembled independently, with both body shells absent.
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
    cam_ids=select('CAM_Mainboard',prefix=('Onboard_MIC_',))
    if P.get('cam_orientation',{}).get('enabled'):
        seq=P['cam_orientation']['assembly'];cam_stage=stages[11];cam_span=cam_stage['end']-cam_stage['start']
        assign(cam_ids,12,(0,seq['forward_mm'],seq['entry_above_mm']),begin=.18,finish=.35,parent='Head_Bench')
        for name in cam_ids:
            o=actors[name];base=bases[name].translation.copy()
            for fraction,offset in [(.24,(0,seq['forward_mm'],seq['lift_at_plug_insertion_mm'])),
                                    (.28,(0,seq['forward_mm'],seq['lift_at_plug_insertion_mm'])),
                                    (.32,(0,seq['forward_mm'],0))]:
                move(o,cam_stage['start']+round(cam_span*fraction),base+Vector(offset))
            # Keep each inspected straight segment straight; automatic handles
            # can round the two corners into an unverified diagonal path.
            o['cam_path_linear']=True
    else:
        assign(cam_ids,12,(0,24,0),begin=.18,finish=.35,parent='Head_Bench')
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
    assign(select('Body_Front','Frame_Insert_0','Frame_Insert_1',prefix=('Speaker_Insert_',)),15,begin=.01,finish=.03,parent='Front_Shell')
    assign(select('Body_Rear','Frame_Insert_2','Frame_Insert_3',prefix=('Rear_Interface_Insert_',)),15,begin=.01,finish=.03,parent='Rear_Shell')
    from speaker_geometry import speaker_transform
    speaker_back=speaker_transform().to_3x3()@Vector((0,-1,0))
    assign(['Speaker_Gasket'],15,speaker_back*28,begin=.10,finish=.33,parent='Front_Shell')
    assign(['Speaker'],15,speaker_back*34,begin=.27,finish=.52,parent='Front_Shell')
    assign(select(prefix=('Speaker_Screw_',)),15,speaker_back*46,begin=.71,finish=.96,parent='Front_Shell')
    assign(['Rear_Interface_PCB','USB_Receptacle','Power_Switch'],15,(0,0,-24),begin=.20,finish=.68,parent='Rear_Shell')
    assign(select(prefix=('Rear_Interface_Screw_',)),15,(0,0,-20),begin=.69,finish=.94,parent='Rear_Shell')
    assign(select(prefix=('Frame_Screw_',)),20,(0,0,-150),begin=.73,finish=.98)
    # Independent rigid modules; no source mesh edits and no hidden old shell.
    for name,step,sign,finish in [('Front_Shell',16,1,.94),('Rear_Shell',20,-1,.55)]:
        r=roots[name];st=stages[step-1];span=st['end']-st['start']
        for fr,xyz in [(1,(0,sign*220,0)),(st['start']+8,(0,sign*220,0)),
                       (st['start']+round(span*finish),(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
    # A separate bench presentation shows both interior faces. Cut back to
    # the exact checked insertion pose before either shell approaches the robot.
    bench=stages[14]
    for name,x,angle,sign in [('Front_Shell',-125,math.pi,1),('Rear_Shell',125,0,-1)]:
        r=roots[name]
        for fr,xyz in [(bench['start']-1,(0,sign*220,0)),(bench['start'],(x,0,0)),
                       (bench['end'],(x,0,0)),(bench['end']+1,(0,sign*220,0))]:move(r,fr,xyz)
        for fr,rz in [(1,0),(bench['start']-1,0),(bench['start'],angle),
                      (bench['end'],angle),(bench['end']+1,0),(scene.frame_end,0)]:
            r.rotation_euler.z=rz;r.keyframe_insert(data_path='rotation_euler',frame=fr)
    # The former bridge path is retained with both shells absent. Stage 8
    # finishes its final 18 mm descent before the transverse bolts arrive.
    st=stages[18];r=roots['Fixed_Bridge']
    for fr,xyz in [(1,(0,-14,144)),(st['start']+12,(0,-14,144)),
                   (st['start']+104,(0,-14,18)),(st['start']+110,(0,-14,18)),
                   (st['end'],(0,0,18)),(stages[7]['start']+8,(0,0,18)),
                   (stages[7]['start']+36,(0,0,0)),(scene.frame_end,(0,0,0))]:move(r,fr,xyz)
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
    # Highlight the actual fixed bridge without adding shell transparency.
    actors['Yaw_Base'].data=tagged(actors['Yaw_Base'].data.copy())
    actors['Yaw_Base'].data.name=AP+'Yaw_Base_DisplayMesh'
    bridge_mat=mat('Bridge_Highlight',(.045,.29,.39))
    actors['Yaw_Base'].data.materials.clear();actors['Yaw_Base'].data.materials.append(bridge_mat)
    for o in list(actors.values())+list(roots.values()):
        smooth(o)
        if o.animation_data and o.animation_data.action:tagged(o.animation_data.action)
    for linear_object in [roots['Front_Shell'],roots['Rear_Shell'],roots['Fixed_Bridge'],actors['Pitch_Servo'],actors['Pitch_Output']]:
        for fc in curves(linear_object):
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    for r in [roots['Front_Shell'],roots['Rear_Shell']]:
        for fc in curves(r):
            for k in fc.keyframe_points:
                if round(k.co.x) in [stages[14]['start']-1,stages[14]['end']]:k.interpolation='CONSTANT'
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
        'shell_bench':((220,700,350),(0,0,102),600),
        'shell_install':((380,-550,355),(0,0,184),670),
        'bridge_lock':((285,-420,300),(0,0,128),470),
        'shell_settle':((450,-650,-100),(0,-40,90),700),
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
        if s['index'] in [19,8]:footer='蓝色：独立承重桥；身体外壳后装   |   台面支承、紧固扭矩及线束待验证'
        if s['index'] in [15,16,20]:footer='前后分壳 · 两组底部定位插舌 · 四处底部工具孔   |   完整带线闭壳未通过'
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

身体改为前后两片外壳。承重桥在身体外壳未装时单独下放、前移并锁紧。
前壳喇叭和后壳接口板在台面分别预装；内部总成完成后，前壳沿-Y、后壳沿+Y合入。
底部两组一体插舌定位，四枚原框架螺钉经底部工具孔锁紧；旧拼缝螺钉和嵌件取消。
每片模块含原生附件的名义平移路径各检查275个位置，不含独立插头包络。
保存后的动画可另以半帧抽样；该项需单独的动画回读记录。
完整软线长度、变形和带线合壳仍未完成，动画未把静态导线示意当作装配证明。
双舵机先在离机座上锁紧；Pitch先在X+30mm处下放，再向左平移到位。
C压板先从侧面套到转动座，随驱动座一起下放。随后转动座转60°，
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
{('M1.54将CAM USB转向机器人右侧+X；CAM端相机FPC朝左-X，屏幕FPC朝下-Z。' if P.get('cam_orientation',{}).get('enabled') else 'CAM相机排线入口朝上，屏幕排线入口朝板外；两处依据官方照片修正。')}
M1.52仅把两枚现有反力连接试配螺母绕原孔轴转正30°，与六角槽方向一致。
M1.53将固定偏航桥左侧穿线口外边缘加宽0.8mm；轴承座和五金位置保持。
下部横向紧固的名义进入路径通过；上部舵盘夹口初次装配和最终五金选型仍未完成。
槽口/触点仅为示意，真实插深、补强片和接触面仍未确认；完整线束尚未应用。
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
    body_evidence=ROOT/'reports/body_split_validation.json'
    audit=json.loads(body_evidence.read_text())
    assert audit['status']=='PASS' and audit['source_blend_sha256']==source_hash
    report={'revision':P['revision'],'animation_revision':ANIMATION_REVISION,'source_blend':str(source),'source_blend_sha256':source_hash,'source_is_unchanged':True,'animation_blend':str(TARGET),'source_geometry_signature':baseline,'actor_count':len(actors),'stage_count':len(stages),'fps':FPS,'frame_range':[1,scene.frame_end],'duration_seconds':scene.frame_end/FPS,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':a.samples,'final_transform_max_error_mm':max(errors.values()),'meshes_share_exact_source_data':False,'all_actor_geometry_matches_source':True,'material_only_mesh_copies':['Yaw_Base'],'all_actors_visible_at_end':True,'stages':published_stages,'part_stages':published_assignments,'geometry_status':'PASS_ENDPOINT_AND_SOURCE_PRESERVATION','body_sequence_kind':'front_rear','body_shell_path':'Front module -Y, rear module +Y; four frame screws from below; bridge previously fixed with shells absent','body_sequence_evidence':str(body_evidence.relative_to(ROOT)),'body_sequence_evidence_sha256':hashlib.sha256(body_evidence.read_bytes()).hexdigest(),'body_sequence_display_stages':[8,9,19,20],'retention_evidence':'reports/head_axial_retention_validation.json','continuous_assembly_path_collision':'NOT_TESTED','p5r7_adopted':bool(P.get('p5r7_adoption',{}).get('enabled')),'rendered_video':False,'blender':bpy.app.version_string,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    save_json(OUT/'manifest.json',report)
    if a.render=='stills':
        scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG'
        for s in published_stages:
            scene.frame_set(s['end']);scene.render.filepath=str(OUT/f'step_{s["index"]:02d}.png');print('ANIMATION_STILL',s['index'],flush=True);bpy.ops.render.render(write_still=True)
    elif a.render=='video':
        # Render to a new path: an old MP4 must not satisfy this run's check.
        import uuid
        final_video=Path(scene.render.filepath)
        if final_video.suffix!='.mp4':final_video=final_video.with_suffix('.mp4')
        pending=final_video.with_name('.render-'+uuid.uuid4().hex+'.mp4')
        try:
            scene.render.filepath=str(pending)
            scene.frame_set(1);bpy.ops.render.render(animation=True)
            if not pending.is_file() or pending.stat().st_size==0:raise RuntimeError('Animation render produced no new video')
            pending.replace(final_video)
        finally:
            scene.render.filepath=str(final_video)
            pending.unlink(missing_ok=True)
    if a.render=='video':
        video=Path(scene.render.filepath)
        if video.suffix!='.mp4':video=video.with_suffix('.mp4')
        if not video.is_file() or video.stat().st_size==0:raise RuntimeError('Animation render returned without a nonempty video')
        report['rendered_video']=True
        report['video']={'file':str(video.relative_to(ROOT)),'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
        save_json(OUT/'manifest.json',report)
    print('ASSEMBLY_ANIMATION_BUILT',len(actors),scene.frame_end,flush=True)


if __name__=='__main__':main()
