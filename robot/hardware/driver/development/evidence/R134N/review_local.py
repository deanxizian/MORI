"""Read-only nominal Fab/body and routing measurements for R134N; not physical qualification."""
from pathlib import Path
import sys,json
from collections import defaultdict
from shapely.geometry import box
from shapely.ops import polygonize,unary_union
scripts=Path(__file__).resolve().parents[2]/'scripts'
if not scripts.exists():scripts=Path('robot/hardware/driver/development/scripts')
sys.path.insert(0,str(scripts))
from copper_geometry import *

def fab(f):
 layer=pcb.F_Fab if f.GetLayer()==pcb.F_Cu else pcb.B_Fab
 lines=[];polys=[];other=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=layer:continue
  a,b=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,b]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
  else:other.append(int(g.GetShape()))
 return unary_union(polys+list(polygonize(unary_union(lines)))),other

a,b=Copper(sys.argv[1]),Copper(sys.argv[2]);plan=json.loads(Path(sys.argv[3]).read_text());step=json.loads(Path(sys.argv[4]).read_text())
fp={f.GetReference():f for f in b.footprints};bodies={};unsupported={}
for ref,f in fp.items():
 g,other=fab(f)
 if not g.is_empty:bodies[ref]=g
 if other or g.is_empty:unsupported[ref]={'unsupported_shape_types':other,'closed_outline_available':not g.is_empty}
source_fp={f.GetReference():f for f in a.footprints};poses={}
for spec in plan.get('translations',[]):
 ref=spec['reference'];f,g=source_fp[ref],fp[ref];poses[ref]={'value':g.GetValue(),'face':b.board.GetLayerName(g.GetLayer()),'before_mm':xy(f.GetPosition()),'before_deg':f.GetOrientationDegrees(),'after_mm':xy(g.GetPosition()),'after_deg':g.GetOrientationDegrees(),'nominal_fab_bounds_mm':bodies[ref].bounds}
projections=defaultdict(float)
new_strokes=defaultdict(list)
for t in b.segments:
 if uid(t) in a.by_id:continue
 ly=b.board.GetLayerName(t.GetLayer());net=t.GetNetname()
 new_strokes[net,ly].append(b.shapes[uid(t),ly])
for (net,ly),geometries in new_strokes.items():
 own_lands=unary_union([s for (i,l),s in b.shapes.items() if l==ly and isinstance(b.by_id[i],pcb.PAD) and b.by_id[i].GetNetname()==net])
 stroke=unary_union(geometries).difference(own_lands)
 for ref,body in bodies.items():
  area=stroke.intersection(body).area
  if area>1e-7:projections[net,ly,ref,b.board.GetLayerName(fp[ref].GetLayer())]=area
rows=[{'net':n,'layer':ly,'component':ref,'mounted_face':face,'area_mm2':area,'same_face':ly==face} for (n,ly,ref,face),area in sorted(projections.items())]
for row in rows:
 if not row['same_face']:continue
 net,ly,ref=row['net'],row['layer'],row['component'];body=bodies[ref]
 old_stroke=unary_union([a.shapes[uid(t),ly] for t in a.segments if t.GetNetname()==net and a.board.GetLayerName(t.GetLayer())==ly])
 new_stroke=unary_union([b.shapes[uid(t),ly] for t in b.segments if t.GetNetname()==net and b.board.GetLayerName(t.GetLayer())==ly])
 lands=unary_union([g for (i,l),g in b.shapes.items() if l==ly and isinstance(b.by_id[i],pcb.PAD) and b.by_id[i].GetNetname()==net])
 row.update(source_all_strokes_projection_outside_lands_mm2=old_stroke.difference(lands).intersection(body).area,candidate_all_strokes_projection_outside_lands_mm2=new_stroke.difference(lands).intersection(body).area,new_projection_beyond_source_outside_lands_mm2=new_stroke.difference(old_stroke).difference(lands).intersection(body).area,matching_component_pads=[dict(pad=b.pad_name(q),position_mm=xy(q.GetPosition())) for q in fp[ref].Pads() if q.GetNetname()==net])
net='Net-(U401-2Y)';old={uid(t) for t in a.tracks};new_tracks=[t for t in b.segments if uid(t) not in old];report={'source_sha256':a.sha,'candidate_sha256':b.sha,'poses':poses,'segment_count':len(b.segments),'via_count':len(b.vias),'footprint_count':len(b.footprints),'new_segments':len(new_tracks),'removed_segments':len(plan.get('delete_copper',[])),'new_vias':len(plan.get('vias',[])),'reassigned_vias':len(plan.get('reassign_vias',[])),'U401_2Y_track_length_mm':sum(t.GetLength()/1e6 for t in b.segments if t.GetNetname()==net),'U401_2Y_vias':[{'uuid':uid(v),'position_mm':xy(v.GetPosition())} for v in b.vias if v.GetNetname()==net],'nominal_fab_new_copper_projections':rows,'same_mounted_face_projections':[r for r in rows if r['same_face']],'fab_geometry_limits':unsupported,'new_or_reassigned_transition_reviews':[r for r in step['reference_transitions'] if r['uuid'] not in old or r['uuid'] in {s['uuid'] for s in plan.get('reassign_vias',[])}],'limits':'Native nominal Fab outlines and copper geometry only. Unsupported Fab geometry stays explicitly listed; no physical, parasitic, thermal, EMC, quiet-ground or surge qualification.'}
Path(sys.argv[5]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['fab_geometry_limits','nominal_fab_new_copper_projections']},indent=2))
