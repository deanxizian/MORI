"""Immutable M1.42 world geometry before the user's six approved repairs."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
load_collections()
for c in COLS.values():c.hide_viewport=False
assembled();bpy.context.view_layer.update()
names={'Display_Frame','Pitch_Yoke','Head_Pitch_Ear_0_Nut','Head_Pitch_Ear_0_Screw','Drive_Bridge','Motor_Retainer','Body_Upper','Body_Lower'}
names|={f'Wheel_{family}_{s}'+('_Inner' if family=='Bearing' else '_0' if family=='Spacer' else '') for family in ['Bearing','Axle','Spacer'] for s in ['L','R']}
names|={f'Shell_{f}_{i}' for f in ['Insert','Screw'] for i in range(4)}
report={'revision':P['revision'],'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}}
for o in parts():
 n=o.name.removeprefix(PREFIX)
 if n in names:
  s=Solid(o);report[n]={'vertices_mm':s.v.tolist(),'triangles':s.f.tolist()}
out=HERE/'six_fix_baseline.json'
if out.exists():raise RuntimeError('Refusing to overwrite immutable baseline')
out.write_text(json.dumps(report,ensure_ascii=False))
print('SIX_FIX_BASELINE',report['revision'],len(report['parts']),sorted(names),flush=True)
