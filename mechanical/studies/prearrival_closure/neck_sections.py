"""Exact section data to locate existing wire space; no cuts are created."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
rows=[]
for z in [143,149,153,157,161,165,169,173,177,183,190,201,211,222]:
    items=[]
    for n,s in ss.items():
        if s.lo[2]<=z<=s.hi[2] and min(abs(s.lo[0]),abs(s.hi[0]))<75:
            polys=s.m.slice(z).to_polygons()
            if len(polys):items.append(dict(id=n,group=s.group,category=s.o.get('category'),polygons=[p.tolist() for p in polys]))
    rows.append(dict(z_mm=z,items=items))
(HERE/'neck_sections.json').write_text(json.dumps(dict(source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),sections=rows)))
print('SECTIONS',[(r['z_mm'],len(r['items'])) for r in rows])
