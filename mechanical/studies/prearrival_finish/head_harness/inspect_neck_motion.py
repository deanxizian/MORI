"""Exact meridional sections for the recorded fixed-probe failure."""
from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
load_collections()
for name in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[name].hide_viewport=False
assembled();bpy.context.view_layer.update()
before=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
seed=json.loads((HERE/'outer_neck_turn.json').read_text());assert seed['source_blend_sha256']==before
names=['Body_Upper','Yaw_Base','Yaw_Reaction_Link','Yaw_Anti_Lift_Keeper','Pitch_Yoke','Yaw_Bearing','Head_Front','Head_Rear','Head_Lower_Guard']
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.name.removeprefix(PREFIX) in names}
plane=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float);rows=[]
for pitch in [0,20]:
    layers={}
    for name,s in ss.items():
        m=s.m
        if s.group=='pitch':m=m.transform(np.asarray(rigidtr(0,pitch))[:3,:])
        polygons=m.transform(plane).slice(0).to_polygons()
        if len(polygons):layers[name]=dict(group=s.group,polygons_mm=[p.tolist() for p in polygons])
    rows.append(dict(yaw_deg=0,pitch_deg=pitch,x_mm=0,layers=layers))
out=dict(source_blend_sha256=before,sections=rows,main_geometry_changed=False,
    source_probe_file='outer_neck_turn.json',source_probe_sha256=hashlib.sha256((HERE/'outer_neck_turn.json').read_bytes()).hexdigest(),
    scope='Saved-solid cross sections to illustrate the fixed planning-probe collision; not a routed harness')
(HERE/'neck_motion_sections.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()==before
print('NECK_MOTION_SECTIONS',len(rows))
