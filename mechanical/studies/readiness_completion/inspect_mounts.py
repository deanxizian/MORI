"""Read-only M1.37 head fastener section inspection. No blend is saved."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from common import *
from validate import Solid
from optics_mount import display_transform
from validate_head_cleanup import geometry_record
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled()
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in ['Head_Front','Head_Rear','Pitch_Cradle','Display_Frame','Display_PCB']}
out={'revision':P['revision'],'head_lugs':[],'LCD':[],'rear_seams':[]}
def hits(n,a,b):
    return [{'position':[round(float(x),4) for x in h.position],'normal':[round(float(x),3) for x in h.normal]} for h in ss[n].m.ray_cast(list(a),list(b))]
for sign in [-1,1]:
    x,y=head_shell_mount_xy_mm(sign);z=D['head_z']
    row={'axis_xy':[x,y],'rays':[]}
    for dx in [0,-sign*1.3,-sign*2.1,sign*1.3,sign*2.1]:
        row['rays'].append({'offset_x':dx,'parts':{n:hits(n,(x+dx,y,z-15),(x+dx,y,z+55)) for n in ['Head_Front','Pitch_Cradle']}})
    out['head_lugs'].append(row)
    out['rear_seams'].append({'x':sign*43,'z':z+37,'rays':[{n:hits(n,(sign*43+dx,-65,z+37),(sign*43+dx,15,z+37)) for n in ['Head_Front','Head_Rear']} for dx in [0,1.3,1.8,2.6]]})
tr=display_transform();axis=tr.to_3x3()@Vector((0,1,0))
for i,(x,z) in enumerate(INTERFACES['components']['display']['vendor_dimensions']['cad_post_center_xz_from_screen_mm']):
    p=tr@Vector((x,P['display']['vendor_mount_back_y_from_head_mm'],D['head_z']+z))
    row={'index':i,'post_back_face':list(p),'axis':list(axis),'rays':[]}
    for dx in [0,.8,1.05,1.3,1.8,2.4]:
        q=p+Vector((dx,0,0));a=q-axis*35;b=q+axis*10
        row['rays'].append({'offset_x':dx,'parts':{n:hits(n,a,b) for n in ['Display_Frame','Display_PCB']}})
    out['LCD'].append(row)
save_json(ROOT/'studies/readiness_completion/mount_sections.json',out)
base=ROOT/'studies/readiness_completion/baseline_geometry.json'
if not base.exists():
    data={'revision':P['revision'],'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
    for n in ['Head_Front','Head_Rear','Pitch_Cradle','Display_Frame','Body_Upper','Face_Mask','Face_Protector','Camera_Window']:
        o=bpy.data.objects[PREFIX+n];o.data.calc_loop_triangles()
        data[n]={'vertices_mm':[list(v) for v in vertices_world(o)],'triangles':[list(t.vertices) for t in o.data.loop_triangles]}
    save_json(base,data)
print(json.dumps(out,ensure_ascii=False,indent=2))
