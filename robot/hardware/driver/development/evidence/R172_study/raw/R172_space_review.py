"""Native footprint/copper space inventory; not a routability or fit certificate.

Courtyard area is mounted-face 2D geometry only. Its complement is NOT free
routing/placement capacity: existing copper, fixed vias, reference planes,
native keepouts and unqualified 3D assembly requirements still apply.
"""
import ast,html,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R172-space-review';out.mkdir(exist_ok=False)
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
edge_lines=[LineString([xy(d.GetStart()),xy(d.GetEnd())]) for d in c.board.GetDrawings() if c.board.GetLayerName(d.GetLayer())=='Edge.Cuts' and d.GetShape()==pcb.SHAPE_T_SEGMENT]
board=unary_union(list(polygonize(unary_union(edge_lines))));assert abs(board.area-2450)<1e-5 and list(board.bounds)==[0,0,70,35]
focus=box(40,6,54,18);group={'U1701','R1701','R1706','R1707','C1701'};extended=group|{'U1302'}
rows=[];part_rows=[]
for f in c.footprints:
 face=c.board.GetLayerName(f.GetLayer());yard=outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd);body=fab(f)
 part_rows.append(dict(reference=f.GetReference(),face=face,position_mm=list(xy(f.GetPosition())),courtyard_present=not yard.is_empty,courtyard_area_mm2=yard.intersection(board).area))
for face in ['F.Cu','B.Cu']:
 yards=[outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==face]
 yard=unary_union(yards);pads=unary_union([s for (u,ly),s in c.shapes.items() if ly==face and isinstance(c.by_id[u],pcb.PAD)]);tracks=unary_union([s for (u,ly),s in c.shapes.items() if ly==face and isinstance(c.by_id[u],pcb.PCB_TRACK)])
 keep=unary_union([k['shape'] for k in c.keepouts if face in k['layers'] and k['tracks']])
 for name,region in [('whole_board',board),('INA300_region',focus)]:
  rows.append(dict(face=face,region=name,bounds_mm=list(region.bounds),area_mm2=region.area,courtyard_union_mm2=yard.intersection(region).area,courtyard_fraction=yard.intersection(region).area/region.area,pad_copper_union_mm2=pads.intersection(region).area,track_via_union_mm2=tracks.intersection(region).area,native_track_keepout_union_mm2=keep.intersection(region).area,ground_via_centres=sum(v.GetNetname()=='GND' and region.covers(Point(xy(v.GetPosition()))) for v in c.vias),non_ground_via_centres=sum(v.GetNetname()!='GND' and region.covers(Point(xy(v.GetPosition()))) for v in c.vias)))
dep=json.loads((b/'R172-ina-dependency-screen.json').read_text());strict=json.loads((b/'R172-ina-pose-screen.json').read_text())
report=dict(scope=__doc__,board_sha256=c.sha,board_outline_mm=[70,35],layers=6,footprints=len(c.footprints),segments=len(c.segments),vias=len(c.vias),ground_vias=sum(v.GetNetname()=='GND' for v in c.vias),areas=rows,missing_mounted_courtyards=[p['reference'] for p in part_rows if not p['courtyard_present']],parts=part_rows,local_pose_evidence=dict(strict_remaining_poses=len(strict['poses']),strict_straight_ports=sum(bool(p['ports']) for p in strict['poses']),dependency_candidates=dep['candidate_poses'],dependency_by_rotation=dep['by_rotation'],scope='Bounded 0.25 mm position grid and four rotations; no global infeasibility or completed-routing proof.'),conclusion='Local constraint congestion is demonstrated. Whole-board area insufficiency is not established; wider grouped placement has explicit candidates requiring restoration and native verification.',global_routability='NOT_PROVEN',physical_fit='NOT_TESTED',adopted=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1520" height="1080" viewBox="0 0 1520 1080">','<rect width="1520" height="1080" fill="#f5f7fa"/>','<text x="35" y="30" font-family="sans-serif" font-size="23" fill="#152438">R168G SPACE REVIEW - native board unchanged</text>','<text x="35" y="55" font-family="sans-serif" font-size="15" fill="#48586b">70 x 35 mm | 215 footprints | 325 vias (114 GND) | fills hidden; courtyards shown | 2D diagnostic, not routing capacity</text>']
def path(g,color,opacity=1,stroke=None,sw=.015):
 for p in parts(g):
  rings=[p.exterior]+list(p.interiors);d=' '.join('M'+' L'.join(f'{x:.6f},{y:.6f}' for x,y in ring.coords)+' Z' for ring in rings)
  svg.append(f'<path d="{d}" fill="{color}" fill-opacity="{opacity}" stroke="{stroke or color}" stroke-width="{sw}" fill-rule="evenodd"/>')
for col,face in enumerate(['F.Cu','B.Cu']):
 for zoom in [False,True]:
  x0=40+750*col;y0=100 if not zoom else 500;scale=9.5 if not zoom else 45;bounds=(0,0,70,35) if not zoom else (40,6,54,18);region=box(*bounds)
  svg.append(f'<text x="{x0}" y="{y0-12}" font-family="sans-serif" font-size="20" fill="#152438">{face} - {"whole board" if not zoom else "INA300 and U1302 region"}</text>')
  svg.append(f'<g transform="translate({x0},{y0}) scale({scale}) translate({-bounds[0]},{-bounds[1]})">')
  path(board.intersection(region),'#ffffff',1,'#26364a',.055)
  for t in c.segments:
   if c.board.GetLayerName(t.GetLayer())==face:path(c.shapes[uid(t),face].intersection(region),'#8794a7',.38)
  for f in c.footprints:
   if c.board.GetLayerName(f.GetLayer())!=face:continue
   ref=f.GetReference();yard=outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd)
   color='#df633f' if ref=='U1701' else ('#e6a539' if ref in extended else ('#546579' if ref.startswith(('J','H')) else '#4d89b8'))
   path(yard.intersection(region),color,.24,color,.022);path(fab(f).intersection(region),color,.52)
   x,y=xy(f.GetPosition())
   if region.contains(Point(x,y)) and (zoom or ref in extended or ref.startswith('J')):
    svg.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="{.37 if zoom else .52}" fill="#102239">{html.escape(ref)}</text>')
  for v in c.vias:
   x,y=xy(v.GetPosition())
   if not region.contains(Point(x,y)):continue
   color='#138663' if v.GetNetname()=='GND' else '#5d6980';svg.append(f'<circle cx="{x}" cy="{y}" r=".25" fill="{color}" fill-opacity=".78"/><circle cx="{x}" cy="{y}" r=".15" fill="#ffffff"/>')
  if not zoom:svg.append('<rect x="40" y="6" width="14" height="12" fill="none" stroke="#c84e2b" stroke-width=".16" stroke-dasharray=".8 .4"/>')
  svg.append('</g>')
svg.append('<text x="40" y="1062" font-family="sans-serif" font-size="15" fill="#48586b">Green: fixed GND vias. Orange/red: functional group under review. Pale footprints: mounted-face courtyards, not free-space certification.</text></svg>')
(out/'overview.svg').write_text('\n'.join(svg))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
print(json.dumps(dict(counts={k:report[k] for k in ['footprints','segments','vias','ground_vias']},areas=rows,missing_courtyards=report['missing_mounted_courtyards'])),flush=True)
