import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();s=Solid(bpy.data.objects[PREFIX+'Display_PCB']);f=Solid(bpy.data.objects[PREFIX+'Display_Frame'])
from optics_mount import display_transform
tr=display_transform();a=np.array(tr.to_3x3()@Vector((0,1,0)));dx=np.array(tr.to_3x3()@Vector((1,0,0)));dz=np.array(tr.to_3x3()@Vector((0,0,1)))
g=json.load(open(ROOT/'reports/readiness_geometry.json'))
for r in g['LCD']:
 p=np.array(r['post_face_mm']);face=np.array(r['head_bearing_mm']);out=[]
 for dep in [.2,1,2,3]:
  c=p+a*dep
  rad=[]
  for d in [dx,-dx,dz,-dz]:
   hit=s.m.ray_cast(c.tolist(),(c+d*2).tolist());rad.append([float(np.linalg.norm(np.array(h.position)-c)) for h in hit])
  out.append({'depth':dep,'radial':rad})
 print(r['id'],out)
 for tangent in [dx,-dx,dz,-dz]:
  p=face+tangent*1.7
  hh=f.m.ray_cast((p-a*2).tolist(),(p+a*3).tolist())
  print('seat',tangent.tolist(),[float((np.array(h.position)-face)@a) for h in hh])
