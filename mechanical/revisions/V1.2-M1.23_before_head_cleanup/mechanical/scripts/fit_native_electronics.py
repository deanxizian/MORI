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

# Candidate units stay full-size. Test actual current solids; only their own
# existing trial instances are excluded. Fastener/mating requirements follow.
fixed={k:m for k,m in targets.items() if k not in E['modules']}
for name,s in E['modules'].items():
    c=source_mesh(s['mesh']);r=rotation(s['rotation_xyz_deg']);local=combine({'solids':c['solids']},r,-r@np.asarray(s['source_center_mm']))
    sign=-1 if name=='Wheel_Buck' else 1;options=[]
    for x in [32,34,36,38,40]:
        for y in [-28,-24,-20,-16,0,16,20,24,28]:
            for z in [146,150,154,158]:
                pos=[sign*x,y,z];m=local.translate(pos);bad=[(n,hit(m,b)) for n,b in fixed.items()];bad=[(n,v) for n,v in bad if v>.02]
                if not bad:options.append({'position_mm':pos,'score':abs(y)+abs(z-151)+abs(x-35)})
    options.sort(key=lambda x:x['score']);report[name]=options
    print(name,options[:10],flush=True)
save_json(ROOT/'reports/native_electronics_fit_search.json',report)
