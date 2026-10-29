"""Record actual local copper, nominal body intersections and thermal geometry proxies."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');out=b/'R147J-inspection.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R147J/MORI_Interface_C3.kicad_pcb')
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
old={uid(t) for t in a.segments};new=[t for t in c.segments if uid(t) not in old];hits=[]
for t in new:
 ly=c.board.GetLayerName(t.GetLayer());own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==t.GetNetname()])
 for f in c.footprints:
  if c.board.GetLayerName(f.GetLayer())!=ly:continue
  g=c.shapes[uid(t),ly].intersection(fab(f)).difference(own)
  if g.area>1e-6:hits.append({'track_uuid':uid(t),'net':t.GetNetname(),'layer':ly,'reference':f.GetReference(),'outside_own_pad_area_mm2':g.area})
thermal={}
for label,d in [('source',a),('candidate',c)]:
 fs={f.GetReference():f for f in d.footprints};cap=fab(fs['C1602'])
 thermal[label]={q:cap.distance(fab(fs[q])) for q in ['Q1601','Q1602']}
gate='/16 {slash} Actuator_Direct_Switch/ACT_GATE'
data={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':len(new)},'same_face_nominal_body_intersections':hits,'C1602_nominal_plan_view_body_distance_mm':thermal,'thermal_qualification':'NOT_TESTED; planar body separation is only a layout proxy, not measured temperature or capacitance stability.','gate_groups':[g['pads'] for g in groups(c,gate)],'new_trace_lengths_mm':{n:sum(LineString([xy(t.GetStart()),xy(t.GetEnd())]).length for t in new if t.GetNetname()==n) for n in sorted({t.GetNetname() for t in new})}}
out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data),flush=True)
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha
