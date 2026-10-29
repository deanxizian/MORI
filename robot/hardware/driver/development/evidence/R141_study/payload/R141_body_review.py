"""Read-only new-copper body projections and local routing measurements.

Closed native Fab outlines are nominal. L701/L901 use the 9.2 x 8.5 maximum
projection recorded in bom_candidate.csv (not a new physical measurement).
Unsupported shapes stay explicit. Opposite/internal projections require separate
coupling/thermal review; this report is not physical or manufacturing acceptance.
"""
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

source, candidate, output = sys.argv[1:4]
a,b = Copper(source),Copper(candidate)
template=Path('robot/hardware/driver/development/evidence/R134N/review_local.py')
node=next(x for x in ast.parse(template.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
af={f.GetReference():f for f in a.footprints};bf={f.GetReference():f for f in b.footprints}
bodies={};limits={};sources={}
for ref,f in bf.items():
 g,other=fab(f)
 if other or g.is_empty:limits[ref]={'unsupported_shape_types':other,'closed_outline_available':not g.is_empty}
 if ref in ['L701','L901']:
  x,y=xy(f.GetPosition());g=translate(rotate(box(-4.6,-4.25,4.6,4.25),-f.GetOrientationDegrees(),origin=(0,0)),xoff=x,yoff=y)
  sources[ref]='bom_candidate.csv recorded maximum body, 9.2 x 8.5 mm; no solder/thermal/measured assembly claim'
 else:sources[ref]='native nominal Fab outline'
 if not g.is_empty:bodies[ref]=g
strokes=defaultdict(list);new_segments=[]
for t in b.segments:
 if uid(t) in a.by_id:continue
 layer=b.board.GetLayerName(t.GetLayer());net=t.GetNetname();strokes[net,layer].append(b.shapes[uid(t),layer]);new_segments.append(t)
rows=[]
for (net,layer),geometries in strokes.items():
 lands=unary_union([g for (u,l),g in b.shapes.items() if l==layer and isinstance(b.by_id[u],pcb.PAD) and b.by_id[u].GetNetname()==net])
 new=unary_union(geometries).difference(lands)
 old=unary_union([a.shapes[uid(t),layer] for t in a.segments if t.GetNetname()==net and a.board.GetLayerName(t.GetLayer())==layer]).difference(lands)
 for ref,body in bodies.items():
  overlap=new.intersection(body)
  if overlap.area<=1e-7:continue
  face=b.board.GetLayerName(bf[ref].GetLayer())
  rows.append({'net':net,'layer':layer,'component':ref,'mounted_face':face,'same_face':layer==face,
               'projection_mm2':overlap.area,'new_projection_beyond_source_mm2':overlap.difference(old).area,
               'body_source':sources[ref],'body_bounds_mm':body.bounds})
moves=[]
for ref,f in bf.items():
 old=af[ref]
 if xy(old.GetPosition())!=xy(f.GetPosition()) or old.GetOrientationDegrees()!=f.GetOrientationDegrees():
  moves.append({'reference':ref,'value':f.GetValue(),'face':b.board.GetLayerName(f.GetLayer()),
                'source_position_mm':xy(old.GetPosition()),'source_rotation_deg':old.GetOrientationDegrees(),
                'candidate_position_mm':xy(f.GetPosition()),'candidate_rotation_deg':f.GetOrientationDegrees()})
lengths=[]
for net in sorted({t.GetNetname() for t in new_segments}):
 lengths.append({'net':net,'source_mm':sum(t.GetLength()/1e6 for t in a.segments if t.GetNetname()==net),
                 'candidate_mm':sum(t.GetLength()/1e6 for t in b.segments if t.GetNetname()==net)})
report={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':b.sha,'moves':moves,
        'segment_count':len(b.segments),'via_count':len(b.vias),'footprint_count':len(b.footprints),
        'new_segment_count':len(new_segments),'removed_source_segments':len([t for t in a.segments if uid(t) not in b.by_id]),
        'new_via_count':len([v for v in b.vias if uid(v) not in a.by_id]),
        'net_track_lengths':lengths,'same_face_projections':[r for r in rows if r['same_face']],
        'opposite_or_internal_projections':[r for r in rows if not r['same_face']],
        'outline_limits':limits,'physical':'NOT_TESTED','manufacturing_release':False}
with Path(output).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['opposite_or_internal_projections','outline_limits','net_track_lengths']},indent=2))
