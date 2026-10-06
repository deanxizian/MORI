import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from common import *
from render import camera
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
c=json.loads((PROJECT/P["detail_fit"]["weact_mesh"]).read_text())
for i in [32,159,160,161,162]:
 s=c["solids"][i];m=manifold.Manifold(manifold.Mesh64(np.array(s["vertices_mm"]),np.array(s["triangles"],dtype=np.uint64)))
 print(i,[(z,m.slice(z).area()) for z in [-2,0.2,1,2.4,3,4,5,6,7,8]],flush=True)
sc=bpy.context.scene;sc.render.engine="CYCLES";sc.cycles.samples=12;sc.cycles.use_denoising=True;sc.render.resolution_x=1000;sc.render.resolution_y=850;sc.render.resolution_percentage=100;sc.render.image_settings.file_format="PNG"
for o in sc.objects:
 if o.type=="MESH":o.hide_render=o.name!=PREFIX+"MCU_Motion"
camera("core_pins",(35,15,75),(-8,-44,125),55)
sc.render.filepath=str(Path(__file__).parent/"core_pins.png");bpy.ops.render.render(write_still=True)
