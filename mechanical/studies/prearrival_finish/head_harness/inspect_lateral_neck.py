"""Current head entry sections; read-only inspection, no cable-hole edits."""
from pathlib import Path
import sys,json,hashlib,time
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
cases=[]
for pitch in [-20,0,25]:
    for axis,pos in [('y',0.),('y',23.),('y',-23.),('x',26.)]:
        # Slice coordinate permutation remains a proper rotation; horizontal
        # section coordinates are X/Z for y or Y/Z for x, with sign corrected.
        if axis=='y':tr=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],float);level=-pos
        else:tr=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float);level=pos
        layers={}
        for name,s in ss.items():
            if s.hi[2]<145 or s.lo[2]>231:continue
            m=s.m.transform(np.asarray(rigidtr(0,pitch))[:3,:]) if s.group=='pitch' else s.m
            polygons=m.transform(tr).slice(level).to_polygons()
            if polygons:layers[name]=dict(group=s.group,polygons_mm=[p.tolist() for p in polygons])
        cases.append(dict(pitch_deg=pitch,plane_axis=axis,plane_position_mm=pos,layers=layers))
out=dict(source_blend_sha256=before,status='PASS',scope='Exact nominal solid sections only; no path or strength qualification',
         sections=cases,main_geometry_changed=False)
(HERE/'lateral_neck_sections.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('LATERAL_NECK_SECTIONS',len(cases),flush=True)
