import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
from monocoque_structure import obj
load_collections()
for n in ['DATUMS','KEEP_OUT','COUPONS','DOCK']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
m=Solid(obj('Display_Frame')).m
out=[]
for x in [10,20,25,30]:
 for z0,z1 in [(219.98,219.999),(219.999,220),(220,220.01)]:
  b=manifold.Manifold.cube([1,2,z1-z0]).translate([x,28,z0])
  out.append({'x_mm':x,'y_mm':[28,30],'z_mm':[z0,z1],'filled_mm3':max(0,(m^b).volume()),'probe_mm3':b.volume()})
print('THIN_LEGACY_SLAB',json.dumps(out),flush=True)
(Path(__file__).parent/'residual_check.json').write_text(json.dumps(out,indent=2)+'\n')
