"""Read the delivered assembly and expose the unfinished S288 torque interfaces.

Inspection renders only. No edits to the delivered .blend or shared dimensions.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera,line,textlabel

OUT=ROOT/'studies/s288_interface_review';OUT.mkdir(parents=True,exist_ok=True)
source=Path(bpy.data.filepath);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.image_settings.file_format='PNG'
for c in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[c].hide_render=True
for c in ['PRINTABLE','PLACEHOLDER','PURCHASED_REFERENCE','ANNOTATIONS']:COLS[c].hide_viewport=False;COLS[c].hide_render=False
def ob(n):return bpy.data.objects[PREFIX+n]
names=['Drive_Motor_R','S288_Output_R_Outer','S288_Output_R_Inner','Wheel_Coupler_R','Wheel_Axle_R','Wheel_Bearing_R_33','Wheel_Bearing_R_39','Wheel_Hub_R']
bb={n:bounds(ob(n)) for n in names};wz=(bb['S288_Output_R_Outer'][2][0]+bb['S288_Output_R_Outer'][2][1])/2
def radial_min(o):return min(math.hypot(v.y,v.z-wz) for v in vertices_world(o))
axle_radius=(bb['Wheel_Axle_R'][1][1]-bb['Wheel_Axle_R'][1][0])/2
def overlap(a,b):return max(0,min(bb[a][0][1],bb[b][0][1])-max(bb[a][0][0],bb[b][0][0]))
data={'revision':P['revision'],'status':'BLOCKED','source_blend':str(source),'source_sha256':source_hash,'source_is_unchanged':True,'units':'mm','coordinates':'+X robot right, +Y front, +Z up',
 'axis':{'direction':[1,0,0],'y_mm':0,'z_mm':wz,'right_output_face_x_mm':bb['S288_Output_R_Outer'][0][1],'left_output_face_x_mm':bounds(ob('S288_Output_L_Outer'))[0][0]},
 'right_assembly_bounds_xyz_mm':bb,'coupler_to_axle_axial_engagement_mm':overlap('Wheel_Coupler_R','Wheel_Axle_R'),
 'hub_to_axle_axial_overlap_mm':overlap('Wheel_Hub_R','Wheel_Axle_R'),'hub_bore_diameter_mm':round(radial_min(ob('Wheel_Hub_R'))*2,3),'shaft_diameter_mm':round(axle_radius*2,3),'hub_radial_clearance_mm':round(radial_min(ob('Wheel_Hub_R'))-axle_radius,3),
 'vendor_source':'mechanical/sources/v1_2/unitree_servo_manual.pdf p2; S288 drawing, not J288',
 'fidelity':'VENDOR_DIMENSIONED_SIMPLIFICATION; no complete manufacturer CAD or measured purchased sample',
 'unresolved':['Output six pilot holes and adapter fastening are not modeled','Adapter is only a 2mm blank ring; current axle has zero axial engagement with it','Round hub bore has no D-flat/key/clamp and is larger than the trial shaft','Axial shaft/bearing retention and case mounting qualification are incomplete','Connector exits, purchased version, thread depths and allowable loads require confirmation'],
 'torque_path_intent':['S288 output face','model-specific flange adapter','separate metal wheel axle','positively locked printed hub','tyre'],
 'radial_load_path_intent':['tyre','printed hub','metal axle','two independent bearings','Drive_Bridge','Load_Frame'],
 'claim_limit':'Coincident axes and collision-free geometry do not establish torque transmission or a buildable connection.'}
save_json(OUT/'inspection.json',data)
material('annotation',(.05,.76,.96),emission=.45)
material('review_output',(.04,.65,.8),metallic=.3)
material('review_adapter',(.98,.38,.03))
for n in ['S288_Output_R_Outer','S288_Output_R_Inner','S288_Output_L_Outer','S288_Output_L_Inner']:
 ob(n).data.materials.clear();ob(n).data.materials.append(MATS['review_output'])
for n in ['Wheel_Coupler_R','Wheel_Coupler_L']:
 ob(n).data.materials.clear();ob(n).data.materials.append(MATS['review_adapter'])
def show(visible):
 for o in sc.objects:
  if o.type=='MESH':o.hide_render=o.name.removeprefix(PREFIX) not in visible
def label(name,txt,loc,size,cam):
 o=textlabel(name,txt,loc,size);o.rotation_euler=cam.rotation_euler.copy();return o
def clear_annotations():
 for o in list(COLS['ANNOTATIONS'].objects):
  if o.get('mori_owner')==OWNER:bpy.data.objects.remove(o,do_unlink=True)
visible={'Motor_Retainer','Studio_Ground'}
for side in ['L','R']:
 visible.update(n.removesuffix('R')+side for n in ['Drive_Motor_R','Wheel_Coupler_R','Wheel_Axle_R','Wheel_Hub_R','Tire_R'])
 visible|={f'S288_Output_{side}_{k}' for k in ['Inner','Outer']}|{f'Wheel_Bearing_{side}_{x}' for x in [33,39]}
show(visible);sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
cam=camera('review_s288_assembly',(220,430,170),(0,0,60),213)
for x in range(-92,92,5):line('physical_axis',(x,0,wz),(x+3,0,wz),.3)
label('axis_note','WHEEL AXIS / Z = 52.5 mm',(0,4,121),6,cam)
label('colour_note','SUPPORT HIDDEN / CYAN OUTPUT / ORANGE UNFINISHED ADAPTER',(0,3,112),3.4,cam)
sc.render.filepath=str(OUT/'drive_axis.png');bpy.ops.render.render(write_still=True)
clear_annotations();show(set());sections=[]
for n in names:
 src=ob(n);cp=clone(src,'review_section_'+n)
 # A genuine axial section from the delivered part. Limit the hub to a
 # central strip so the small adapter and shaft are readable at useful scale.
 keep=box('section_halfspace',(40,50,wz),(100,100,20 if n=='Wheel_Hub_R' else 60))
 intersect(cp,keep);cp.data.materials.clear()
 for mat in src.data.materials:cp.data.materials.append(mat)
 cp.hide_render=False;sections.append(cp)
sc.render.resolution_x=1600;sc.render.resolution_y=1000
cam=camera('review_s288_section',(40,-400,wz),(40,0,wz),105)
for x in range(-6,84,4):line('section_axis',(x,-20,wz),(x+2.4,-20,wz),.09)
for letter,x,z,tx,tz in [('A',12,73,12,62.5),('B',25.5,69,25.5,59.5),('C',27,35,28,45.5),('D',51,69,51,54.5),('E',37,30,37,47.5),('F',68,75,68,62.5)]:
 label('part_'+letter,letter,(x,-25,z),4,cam);line('leader_'+letter,(x,-24,z-1 if z>60 else z+4),(tx,-24,tz),.08)
label('section_title','RIGHT DRIVE / AXIAL SECTION',(40,-25,82),3.3,cam)
label('section_legend','A CASE   B OUTPUT   C BLANK ADAPTER   D SHAFT   E BEARINGS   F HUB',(40,-25,22),2.05,cam)
label('section_axis_z','X AXIS / Z 52.5 mm',(52,-25,40),2.2,cam)
sc.render.filepath=str(OUT/'axial_section.png');bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
doc=f'''# S288 轮驱连接复查 · {P['revision']}

当前状态：**BLOCKED — 输出连接与轮轴锁紧尚未设计完成**。本页从当前总装读取尺寸，只生成检查视图，没有修改总装或冻结新尺寸。

## 建模精度

本体按原厂20×34×20mm关键包络简化，输出盘按Ø14、两侧各突出3mm表示，总厚26mm。不是完整厂家CAD，也没有实物测量。输出六孔、外壳细节、连接器和正式安装件尚未完整建模。

## 转轴在哪里

旋转轴线沿机器人左右方向X，Y=0，离地Z={wz:g}mm。实际电机输出是本体两面的短圆盘，不是伸到轮毂的长轴。右侧朝车轮的输出盘为 `S288_Output_R_Outer`，外侧面X=27mm；左侧对应面X=-27mm。两轴线与各自轮心同轴。厂家原图输出中心距34mm方向的一端9.5mm，位于20mm方向中央；当前电机已绕这根轴放平90°。

## 图中部件

| 标记 | 对象 | 当前状态 |
|---|---|---|
| A | Drive_Motor_R | 电机固定壳体，关键尺寸简化 |
| B | S288_Output_R_Outer | 自带输出盘，六个安装孔尚未建出 |
| C | Wheel_Coupler_R | 2mm厚打印转接毛坯，未完成螺钉孔/轴夹持 |
| D | Wheel_Axle_R | 另加的金属轮轴，模型Ø3.98，名义4mm候选 |
| E | Wheel_Bearing_R_33 / 39 | 另加的两只轴承候选，用于支撑轮载 |
| F | Wheel_Hub_R | 打印轮毂；图中仅显示穿过轴线的中心剖切条带 |

## 测到的连接缺口

- 转接盘X=27…29mm，轴X=29…71mm：轴没有伸入转接盘，轴向啮入长度为0。
- 轮毂孔Ø4.4mm、轴Ø3.98mm：单边约0.21mm间隙，且未建D形面、键或夹紧。虽然轴在轮毂内重叠10.5mm，仍不能据此传递扭矩。
- 缺少正式输出六孔螺钉、轴端防脱、轴承保持和经验证的电机壳体固定。

目标传扭路径：电机输出盘 → 对应型号的法兰转接件 → 金属轮轴 → 有止转锁紧的打印轮毂 → 轮胎。

目标承重路径：轮胎 → 轮毂 → 金属轮轴 → 两只独立轴承 → 打印承重座Drive_Bridge → 主框架。当前部件只是这条路径的布局，尚不是已完成的可装配机构。

厂家S288图示输出六孔分布圆Ø10.5，底孔Ø1.7，M2自攻螺钉、深度上限3mm；不是M2机牙螺纹孔，也不能与J288孔型混用。打印件厚度及螺钉总长须按实际有效旋入长度复核。下一步要先落实输出盘→轴的止转连接和轴向防脱，再同步调整转接件、轴承位置及轮毂孔；不能直接拿当前转接毛坯装车。

数据：[inspection.json](inspection.json)。原厂图：[尺寸图](../../sources/v1_2/s288_dimensions.png)，[说明书](../../sources/v1_2/unitree_servo_manual.pdf)。既有几何检查不证明连接已经能传扭、承载或实机运行。
'''
(OUT/'README.md').write_text(doc)
(OUT/'index.html').write_text(f'''<!doctype html><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI S288 连接复查</title><style>body{{background:#141a21;color:#dde7ed;font:17px/1.8 system-ui;max-width:1200px;margin:auto;padding:25px}}img{{width:100%;border-radius:10px}}a{{color:#8edee9}}.note{{padding:18px;background:#443526}}p{{max-width:1050px}}</style><h1>S288 电机、输出轴与打印件</h1><p class="note">{P['revision']}：原厂关键尺寸简化模型。输出盘安装六孔、转接件止转、轮轴/轮毂锁紧及轴向防脱尚未完成；现有同轴布局不能直接作为装车依据。</p><p><a href="README.md">详细复查与实测几何</a> · <a href="inspection.json">模型尺寸记录</a> · <a href="../../index.html#structure">返回总装</a></p><img src="drive_axis.png"><p>青色是电机自带短输出盘，橙色是未完成的打印转接毛坯。转轴沿左右方向，离地52.5mm。</p><img src="axial_section.png"><p>A 电机壳体；B 自带输出盘；C 转接毛坯；D 另加的金属轮轴；E 两只独立轴承；F 打印轮毂的中央剖切。所有位置来自实际总装模型，没有用爆炸偏移伪装配合。</p><p>轴没有伸入C转接盘，轴向啮入为0；F孔Ø4.4与D轴Ø3.98之间单边间隙约0.21mm，尚无止转或夹紧结构。下一步必须完善这些连接。</p>''')
print('S288_INTERFACE_REVIEW_COMPLETE',json.dumps(data,ensure_ascii=False),flush=True)
