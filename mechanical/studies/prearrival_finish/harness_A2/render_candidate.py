# -*- coding: utf-8 -*-
"""Independent wire preview; save only a clearly named candidate blend."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT_ROOT=HERE.parents[3]
sys.path.insert(0,str(PROJECT_ROOT/'mechanical/scripts'))
from common import *
from render import camera
load_collections();assembled()
original=Path(bpy.data.filepath);before=hashlib.sha256(original.read_bytes()).hexdigest()
audit=json.loads((HERE/'ecowire_validation.json').read_text());assert audit['status']=='PASS' and audit['source_blend_sha256']==before
required_ports={'power_J17','motion_J1','motion_J2','power_J13','motion_J3','power_J14'}
mates=PROJECT_ROOT/'mechanical/studies/prearrival_preparation/mated_connector_review.blend'
with bpy.data.libraries.load(str(mates),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.removeprefix(PREFIX+'PREARRIVAL_Plug_') in required_ports]
for o in dst.objects:
    if o:
        bpy.context.scene.collection.objects.link(o)
        o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['role']='review_overlay'
        o.data.materials.clear();o.data.materials.append(material('REVIEW_mating_housing',(.63,.35,.10)))
data=json.loads((HERE/'ecowire_wire_solids.json').read_text())
palette={'H01':(.95,.40,.025),'H02':(.95,.68,.08),'H03':(.65,.22,.035)}
for wid,d in data.items():
    o=mesh('REVIEW_EcoWire_'+wid,d['vertices_mm'],d['triangles']);move_collection(o,'PLACEHOLDER')
    o['role']='review_overlay';o['category']='PLACEHOLDER';o['data_status']='ASSUMED'
    o['label_zh']=wid+' 静态单线候选，未采购/未采用';o['source_evidence']='harness_A2/ecowire_sources.json; nominal crimp exits remain assumed'
    o.data.materials.append(material('REVIEW_'+wid,palette[wid.split('_')[0]],roughness=.4))
visible={'Load_Frame','Yaw_Base','Power_Module','MCU_Carrier','MCU_Motion','E_Straight_Header','Socket_AC','Socket_BD','Socket_E'}
for o in bpy.context.scene.objects:
    if o.type=='MESH':
        n=o.name.removeprefix(PREFIX)
        o.hide_render=not (n in visible or n.startswith('REVIEW_EcoWire_') or n.startswith('PREARRIVAL_Plug_'))
        if o.get('role')=='routing':o.hide_render=True
for c in ['DATUMS','KEEP_OUT','COUPONS','DOCK','ANNOTATIONS']:COLS[c].hide_render=True
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16;sc.cycles.use_denoising=True
sc.render.resolution_x=1120;sc.render.resolution_y=840;sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
camera('A2_Wire_Review',(180,-255,330),(0,-18,132),132)
out=[]
for mode in ['bridge_visible','bridge_hidden']:
    bpy.data.objects[PREFIX+'Yaw_Base'].hide_render=mode=='bridge_hidden'
    path=HERE/(mode+'.png');sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    out.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
for o in bpy.context.scene.objects:
    if o.type=='MESH':o.hide_set(o.hide_render)
dest=HERE/'MORI_H01_H03_CANDIDATE_NOT_ADOPTED.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
assert hashlib.sha256(original.read_bytes()).hexdigest()==before
(HERE/'preview_manifest.json').write_text(json.dumps(dict(source_main_sha256=before,main_unchanged=True,
    status='PASS',scope='Independent preview only',candidate_blend=dest.name,candidate_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),images=out),indent=2)+'\n')
