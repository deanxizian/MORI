"""Read-only sections of the existing yaw joint; no speculative cable holes."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
levels=[145.,150.,155.,160.,165.,170.,175.,180.,185.,190.]
rows=[]
for z in levels:
    layers={}
    for name,s in ss.items():
        if s.lo[2]>z or s.hi[2]<z or s.lo[0]>45 or s.hi[0]<-45 or s.lo[1]>45 or s.hi[1]<-45:continue
        polygons=s.m.slice(z).to_polygons()
        if len(polygons):layers[name]=dict(group=s.group,polygons_mm=[p.tolist() for p in polygons])
    rows.append(dict(z_mm=z,layers=layers))
result=dict(revision=P['revision'],source_blend_sha256=before,scope='Horizontal sections of saved physical solids at mechanical zero, not a routed harness qualification',
    sections=rows,main_geometry_changed=False,status='PASS',cable_fit='NOT_TESTED')
tr=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float)
side={}
for name,s in ss.items():
    if s.lo[2]>196 or s.hi[2]<136 or s.lo[0]>0 or s.hi[0]<0:continue
    polygons=s.m.transform(tr).slice(0.).to_polygons()
    if len(polygons):side[name]=dict(group=s.group,polygons_mm=[p.tolist() for p in polygons])
result['side_section']=dict(x_mm=0,axes=['Y_forward','Z_up'],layers=side)
(HERE/'neck_sections.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('NECK_SECTIONS',len(rows),flush=True)
print('MANIFOLD_PROJECT_API',getattr(manifold.Manifold,'project').__doc__,flush=True)
print('CROSSSECTION_API',manifold.CrossSection.__doc__,flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
