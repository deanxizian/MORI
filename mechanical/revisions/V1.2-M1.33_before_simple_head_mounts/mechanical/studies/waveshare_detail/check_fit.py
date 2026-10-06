import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,intersect_volume
from validate_head_cleanup import geometry_record
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for c in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[c].hide_viewport=False
bpy.context.view_layer.update()
solids={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group')!='dock' and not o.name.startswith(PREFIX+'Coupon')}
names=P['waveshare_detail']['changed_existing_ids'];hits=[];gaps=[]
for name in names:
 for other,b in solids.items():
  if other==name or other in names[:names.index(name)]:continue
  v=intersect_volume(solids[name],b)
  if v>.02:hits.append({'part':name,'obstacle':other,'intersection_mm3':v})
 for other in ['Head_Front','Head_Rear','Pitch_Cradle','Pitch_Yoke','Display_Frame','Yaw_Servo','Pitch_Servo']:
  gaps.append({'part':name,'obstacle':other,'gap_mm':solids[name].m.min_gap(solids[other].m,5)})
base=json.loads((PROJECT/P['waveshare_detail']['baseline_geometry']).read_text());now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
changes=[n for n in now if now[n]!=base['parts'].get(n)]
r={'revision':P['revision'],'hits':hits,'gaps':gaps,'changed_parts':changes,'unexpected_changes':sorted(set(changes)-set(names)),'removed':sorted(set(base['parts'])-set(now)),'nominal_fit':'PASS' if not hits else 'BLOCKED','physical_fit':'NOT_TESTED'}
save_json(Path(__file__).parent/'fit.json',r);print(json.dumps(r,ensure_ascii=False))
