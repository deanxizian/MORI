import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
s={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group')!='dock'}
for n,d in [('Motor_Retainer',0),('Load_Frame',12),('Battery_Tray',12),('Drive_L_-8_Nut',0)]:
 a=s['Drive_Bridge'] if 'Nut' in n else s['Body_Lower'];aa=Solid(a.o,a,Matrix.Translation((0,0,-d)));m=aa.m^s[n].m;verts=m.to_mesh64().vert_properties
 print(n,d,'intersection',m.volume(),'bbox',([verts[:,:3].min(axis=0).tolist(),verts[:,:3].max(axis=0).tolist()] if len(verts) else []))
