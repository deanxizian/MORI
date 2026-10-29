"""Read-only nominal opposite-face projection inventory for four new input traces."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(b/'R154B/MORI_Interface_C3.kicad_pcb')
assert a.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
rows=[]
for t in c.segments:
 if uid(t) in a.by_id:continue
 ly=c.board.GetLayerName(t.GetLayer());g=c.shapes[uid(t),ly]
 for f in c.footprints:
  if f.GetLayer()==t.GetLayer():continue
  h=g.intersection(fab(f))
  if h.area>1e-6:
   rows.append({'track_uuid':uid(t),'net':t.GetNetname(),'layer':ly,'opposite_reference':f.GetReference(),'value':f.GetValue(),'nominal_projection_mm2':h.area,'reference_plane':REFERENCE[ly]})
out=b/'R154B-opposite-projections.json';assert not out.exists()
out.write_text(json.dumps({'source_sha256':a.sha,'candidate_sha256':c.sha,'projections':rows,'limits':'Nominal Fab/fallback shapes, not measured package envelopes; copper pads on opposite face are not component bodies.'},indent=2)+'\n')
print(json.dumps(rows))
