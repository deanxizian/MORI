"""Targeted placement search and exact component-level collision diagnostics."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from native_electronics import *
from validate import Solid

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
def hit(a,b):
    aa=a.bounding_box();bb=b.bounding_box()
    if any(aa[i+3]<bb[i] or bb[i+3]<aa[i] for i in range(3)):return 0
    return max(0,(a^b).volume())
def combine(c,r,t):
    return manifold.Manifold.batch_boolean([solid_from(np.asarray(s['vertices_mm'])@r.T+t,s['triangles'],c.get('reference',''),[]) for s in c['solids']],manifold.OpType.Add)
targets={o.name.removeprefix(PREFIX):Solid(o).m for o in parts() if o.get('role')=='part' and o.get('group') not in ['dock','coupon']}
report={}
for kind,s in E['boards'].items():
    c=source_mesh(s['mesh']);r,t=board_transform(kind,c);bad=[]
    for comp in c['components']:
        m=combine(comp,r,t)
        for n in ['Load_Frame','Body_Upper','MCU_Motion','Rear_Interface_Screw_0','Rear_Interface_Screw_1','IMU_Insert_0','IMU_Insert_1']:
            if n==s['object']:continue
            v=hit(m,targets[n])
            if v>.02:bad.append([comp['reference'],n,round(v,4)])
    report[kind]=bad
    print(kind,bad,flush=True)

save_json(ROOT/'reports/native_electronics_component_fit.json',report)
