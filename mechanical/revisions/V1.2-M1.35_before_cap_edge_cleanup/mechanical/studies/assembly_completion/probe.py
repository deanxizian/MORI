import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid,intersect_volume
load_collections();assembled()
ids=['Display_Frame','Head_Front','Display_PCB','Camera_PCB','Camera_Lens']
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in ids}
r={'source':bpy.data.filepath,'geometry':{n:{'bounds':bounds(a.o),'matrix':[list(v) for v in a.o.matrix_world],'faces':len(a.o.data.polygons),'volume':a.m.volume(),'proxy':a.o.get('validation_proxy'),'source':a.o.get('validation_solid_source')} for n,a in ss.items()},'overlap':[]}
for a,b in [('Display_Frame','Display_PCB'),('Display_Frame','Head_Front')]:
 m=ss[a].m^ss[b].m;r['overlap'].append({'a':a,'b':b,'volume':m.volume(),'bounds':list(m.bounding_box())})
save_json(Path(__file__).parent/('probe_'+Path(bpy.data.filepath).stem+'.json'),r);print(json.dumps(r,indent=2))
