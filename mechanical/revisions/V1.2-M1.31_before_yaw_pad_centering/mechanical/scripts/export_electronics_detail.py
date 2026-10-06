"""Separate inspectable scene with one object per native PCB reference.

The assembly remains unchanged; the extra .blend is a traceable review derivative.
"""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
source=ROOT/'mori_v1_2.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
scene=bpy.data.scenes.new('MORI_PCB_Component_Detail');scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
scene.world=bpy.context.scene.world;outrows=[]
names=[v['object'] for v in P['native_electronics']['boards'].values()]+['Power_Switch','USB_Receptacle','Wheel_Buck','Head_Buck','MCU_Motion','Display_PCB','CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R','CAM_USB_Connector']
for name in names:
    src=bpy.data.objects.get(PREFIX+name)
    if src is None:continue
    coll=bpy.data.collections.new('PCB / '+name);scene.collection.children.link(coll)
    rows=json.loads(src.get('component_reference_index','[]'))
    if not rows:
        cp=src.copy();cp.data=src.data.copy();cp.parent=None;cp.matrix_world=src.matrix_world.copy();cp.hide_render=False;coll.objects.link(cp);cp.name='PCB_DETAIL__'+name;continue
    vv=np.asarray([tuple(v.co) for v in src.data.vertices]);ff=[list(p.vertices) for p in src.data.polygons]
    for row in rows:
        lo,hi=row['vertices'];f0,f1=row['faces'];me=bpy.data.meshes.new(name+' / '+row['reference']);me.from_pydata(vv[lo:hi].tolist(),[],[[i-lo for i in f] for f in ff[f0:f1]]);me.update()
        ob=bpy.data.objects.new(name+' / '+row['reference']+' / '+row['value'],me);coll.objects.link(ob);ob.matrix_world=src.matrix_world.copy()
        for mat in src.data.materials:me.materials.append(mat)
        for a,b in zip(me.polygons,list(src.data.polygons)[f0:f1]):a.material_index=b.material_index
        ob['reference']=row['reference'];ob['value']=row['value'];ob['evidence']=row['evidence'];ob['limitations']=row['limitations'];ob['source_board']=name;ob['dimensions_basis']=row['dimension_basis'];outrows.append({'object':ob.name,'board':name,'ref':row['reference'],'evidence':row['evidence']})
bpy.context.window.scene=scene
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        s=area.spaces.active;s.overlay.show_relationship_lines=False;s.overlay.show_extras=False;s.shading.color_type='MATERIAL';s.region_3d.view_distance=220;s.region_3d.view_location=(0,-8,132);s.region_3d.view_rotation=Vector((150,200,170)).to_track_quat('Z','Y');s.region_3d.view_perspective='ORTHO'
scene['source_revision']=P['revision'];scene['source_main_sha256']=digest;scene['source_positions']='Same assembled coordinates. Board collections toggle visibility. Component ref objects independently editable; no source package rescaled.'
text=bpy.data.texts.new('READ_ME_PCB_EVIDENCE');text.write('MORI '+P['revision']+'\nFour native PCBs: one object per reference; actual assembled coordinates. Native placement + generic KiCad packages or dimensioned manufacturer reconstructions are NOT measured samples. CAM populated geometry incomplete; charger unselected. Main assembly and electronic source reports remain authoritative.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'mori_electronics_detail.blend'))
save_json(ROOT/'reports/electronics_detail_manifest.json',{'revision':P['revision'],'source_main_sha256':digest,'file':'mori_electronics_detail.blend','per_reference_objects':outrows,'position_frame':'assembly mm','source_file_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==digest})
