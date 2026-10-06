# -*- coding: utf-8 -*-
"""Independent fourteen-wire candidate preview; never save the main assembly."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT_ROOT=HERE.parents[3]
ASSEMBLY_REVIEW='--assembly-reviewed' in sys.argv
REVIEW_DIR=HERE/'assembly_safe_review' if ASSEMBLY_REVIEW else HERE
sys.path.insert(0,str(PROJECT_ROOT/'mechanical/scripts'))
from common import *
from render import camera
load_collections();assembled()
original=Path(bpy.data.filepath);before=hashlib.sha256(original.read_bytes()).hexdigest()
audit=json.loads((REVIEW_DIR/'fourteen_validation.json').read_text())
assert audit['status']=='PASS' and audit['source_blend_sha256']==before
required_ports={'power_J17','motion_J1','motion_J2','power_J13','motion_J3','power_J14','motion_J4','imu_J1'}
mates=PROJECT_ROOT/'mechanical/studies/prearrival_preparation/mated_connector_review.blend'
with bpy.data.libraries.load(str(mates),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.removeprefix(PREFIX+'PREARRIVAL_Plug_') in required_ports]
assert len(dst.objects)==8
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
    o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['role']='review_overlay'
    o.data.materials.clear();o.data.materials.append(material('REVIEW14_mating_housing',(.63,.35,.10)))
data=json.loads((REVIEW_DIR/'fourteen_wire_solids.json').read_text());assert len(data)==14
palette={'H01':(.95,.40,.025),'H02':(.95,.68,.08),'H03':(.65,.22,.035),'H04':(.98,.48,.035)}
for wid,d in data.items():
    o=mesh('REVIEW14_EcoWire_'+wid,d['vertices_mm'],d['triangles']);move_collection(o,'PLACEHOLDER')
    o['role']='review_overlay';o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['label_zh']=wid+' 静态单线候选，未采购/未采用'
    o['source_evidence']='harness_A2/ecowire_sources.json; nominal terminal exits remain assumed'
    color=palette[wid.split('_')[0]]
    if wid.startswith('H04_'):
        factor=.62+.38*(int(wid.split('_')[1])-1)/7
        color=tuple(v*factor for v in color)
    o.data.materials.append(material('REVIEW14_'+wid,color,roughness=.4))
visible={'Load_Frame','Yaw_Base','Power_Module','MCU_Carrier','MCU_Motion','E_Straight_Header',
         'Socket_AC','Socket_BD','Socket_E','Body_IMU','Rear_Interface_PCB'}
assert all(PREFIX+n in bpy.data.objects for n in visible), 'Required board or frame missing from preview'
for o in bpy.context.scene.objects:
    if o.type=='MESH':
        n=o.name.removeprefix(PREFIX)
        o.hide_render=not (n in visible or n.startswith('REVIEW14_EcoWire_') or n.startswith('PREARRIVAL_Plug_'))
        if o.get('role')=='routing':o.hide_render=True
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
sc.render.resolution_x=1280;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
out=[]
for name,pos,target,scale in [
    ('fourteen_rear_upper',(170,-300,225),(0,-28,116),170),
    ('fourteen_rear_lower',(-175,-320,20),(0,-28,112),170)]:
    camera('A2_Fourteen_Review',pos,target,scale)
    path=REVIEW_DIR/(name+'.png');sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    out.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.hide_set(o.hide_render)
dest=REVIEW_DIR/'MORI_H01_H04_CANDIDATE_NOT_ADOPTED.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
assert hashlib.sha256(original.read_bytes()).hexdigest()==before
(REVIEW_DIR/'fourteen_preview_manifest.json').write_text(json.dumps(dict(source_main_sha256=before,main_unchanged=True,
    status='PASS',scope='Independent fourteen-wire preview only; outer shells hidden for inspection',
    candidate_blend=dest.name,candidate_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),images=out),indent=2)+'\n')
