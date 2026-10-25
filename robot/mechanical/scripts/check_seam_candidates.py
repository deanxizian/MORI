import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled();a=Solid(bpy.data.objects[PREFIX+'Body_Lower']);tree=a.bvh()
for y in range(46,62):
 start=Vector((120,y,88));d=Vector((-1,0,0));hits=[]
 for i in range(6):
  hit=tree.ray_cast(start,d,150)
  if hit[0] is None:break
  hits.append(round(hit[0].x,4));start=hit[0]+d*.01
 print(y,hits)
