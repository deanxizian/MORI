"""Per-object actual Blender renders for the editable part inventory."""
import sys,json,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from render import camera
sc=bpy.data.scenes['MORI_V1_Assembly'];bpy.context.window.scene=sc;load_collections();assembled()
for c in ['PRINTABLE','PURCHASED_REFERENCE','PLACEHOLDER','DOCK','COUPONS']: COLS[c].hide_render=False;COLS[c].hide_viewport=False
for c in ['DATUMS','ANNOTATIONS','KEEP_OUT']:COLS[c].hide_render=True
sc.render.engine='CYCLES';sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.render.resolution_x=384;sc.render.resolution_y=384;sc.render.resolution_percentage=100
objects=sorted(parts(True),key=lambda o:o.name);
if '--ids' in sys.argv:
 wanted=sys.argv[sys.argv.index('--ids')+1].split(',');objects=[o for o in objects if o.name.removeprefix(PREFIX) in wanted]
out=ROOT/'renders/parts';out.mkdir(parents=True,exist_ok=True)
for o in sc.objects:
 if o.type=='MESH':o.hide_render=True
rows=[]
for i,o in enumerate(objects):
 if o.get('category')=='PLACEHOLDER':
  # Per-part evidence previews emphasize unknown hardware dimensions. Exterior
  # beauty views retain the intended white/grey material palette.
  o.data.materials.clear();o.data.materials.append(bpy.data.materials[PREFIX+'unknown'])
 o.hide_render=False;bpy.context.view_layer.update();bb=bounds(o);center=Vector([(a+b)/2 for a,b in bb]);dim=Vector([b-a for a,b in bb]);scale=max(dim.length*1.16,12)
 camera('part_'+str(i),center+Vector((380,500,260)),center,scale)
 sc.render.filepath=str(out/(o.name.removeprefix(PREFIX)+'.png'));bpy.ops.render.render(write_still=True);o.hide_render=True
 rows.append({'id':o.name.removeprefix(PREFIX),'name':o['label_zh'],'category':o['category'],'status':o['data_status'],'model_fidelity':o.get('model_fidelity','DESIGN_GEOMETRY'),'measured_unit':bool(o.get('measured_unit',False)),'dimensions_mm':[round(x,1) for x in dim],'file':str(Path('renders/parts')/(o.name.removeprefix(PREFIX)+'.png'))})
 print('PART_PREVIEW',i+1,len(objects),o.name,flush=True)
path=ROOT/'reports/parts_preview_manifest.json';old=json.loads(path.read_text()) if path.exists() and '--ids' in sys.argv else [];merged={v['id']:v for v in old};merged.update({v['id']:v for v in rows});save_json(path,sorted(merged.values(),key=lambda v:v['id']))
print('CATALOG_COMPLETE',flush=True)
