"""Read-only classification of final nut-pocket opposed-wall samples."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid,rigidtr
from assembly_issue_fixes import boxm,hex_x
from interface_completion import axial
load_collections();assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
b=json.loads((HERE/'six_fix_baseline.json').read_text())['Pitch_Yoke']
old=manifold.Manifold(manifold.Mesh64(np.array(b['vertices_mm']),np.array(b['triangles'],dtype=np.uint64)))
p=P['assembly_issue_fixes']['pitch_nut'];z=next(r for r in json.loads((ROOT/'reports/prearrival_geometry.json').read_text())['servo_ears'] if r['id']==p['id'])['ear_top_mm'][2]
zone=boxm([-35.999,-8,226],[-31,8,228.251])
fill=(old^zone)-ss['Pitch_Yoke'].m
pc=[p['pocket_center_x_mm'],0,z];half=p['pocket_depth_mm']/2
pocket=hex_x(p['pocket_AF_mm'],p['pocket_depth_mm'],pc)+boxm([pc[0]-half,0,z-p['entry_half_height_mm']],[pc[0]+half,8,z+p['entry_half_height_mm']])
fill-=pocket
candidate=ss['Pitch_Yoke'].m+fill
out={'old_bearing_upper_z':D['head_z']+6.25,'ear_axis_z':z,'local_restore_volume_mm3':fill.volume(),'vertical_rays':[]}
for x in [-40,-34.33,-33.8,-33.2]:
 for label,m in [('old',old),('current',ss['Pitch_Yoke'].m),('bounded_restore',candidate)]:
  hits=m.ray_cast([x,0,224],[x,0,237])
  out['vertical_rays'].append({'x':x,'geometry':label,'hits':[[list(h.position),list(h.normal)] for h in hits]})
out['static_added_collisions']=[]
for n,s in ss.items():
 if n=='Pitch_Yoke':continue
 v=max(0,(fill^s.m).volume())
 if v>.005:out['static_added_collisions'].append({'part':n,'mm3':v})
(HERE/'pitch_pocket_wall_inspection.json').write_text(json.dumps(out,indent=2))
print('PITCH_WALL_INSPECTION',json.dumps(out),flush=True)
