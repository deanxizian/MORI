"""Confirm inspectable vendor parts retain source dimensions after display offsets."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
r=json.loads((ROOT/'reports/waveshare_bench_manifest.json').read_text());errors=[];maximum=0
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
assembled();bpy.context.view_layer.update()
source_matrices={row['source']:bpy.data.objects[row['source']].matrix_world.copy() for row in r['parts']}
bpy.context.window.scene=bpy.data.scenes['MORI_Waveshare_Bench'];bpy.context.view_layer.update()
for row in r['parts']:
    ob=bpy.data.objects[row['object']];src=bpy.data.objects[row['source']];ref=next(a for a in json.loads(src['component_reference_index']) if a['reference']==row['ref'])
    actual=np.array([tuple(v.co) for v in ob.data.vertices]);expected=np.array([tuple(v.co) for v in src.data.vertices[slice(*ref['vertices'])]])
    e=float(np.max(np.abs(actual-expected))) if actual.shape==expected.shape else 999
    tr=np.array(Matrix(row['presentation_matrix'])@source_matrices[row['source']]);delta=float(np.max(np.abs(tr-np.array(ob.matrix_world))))
    maximum=max(maximum,e,delta)
    if e>.0001 or delta>.0001 or ob.get('evidence')!=ref['evidence']:errors.append({'part':ob.name,'vertex_error_mm':e,'transform_error':delta})
sc=bpy.data.scenes['MORI_Waveshare_Bench'];mm=abs(sc.unit_settings.scale_length-.001)<1e-8
out={'revision':P['revision'],'status':'PASS' if not errors and mm else 'FAIL','individually_editable_parts':len(r['parts']),'maximum_coordinate_error_mm':maximum,'units_mm':mm,'errors':errors,'uninstalled_FPC_separate':True,'physical_accuracy':'Photo assumptions and nominal vendor CAD, not measured hardware'}
save_json(ROOT/'reports/waveshare_bench_validation.json',out);print(json.dumps(out))
if out['status']!='PASS':raise RuntimeError('Bench differs from source geometry')
bpy.context.window.scene=sc;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=1400;sc.render.resolution_y=750;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.render.filepath=str(ROOT/'studies/waveshare_detail/bench.png');bpy.ops.render.render(write_still=True)
