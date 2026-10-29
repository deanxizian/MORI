"""Native pad/courtyard comparison for a larger Q1701/U1702 adjustment.

The R167 source ACT_UV_N output via is explicitly movable; all other vias,
especially the 114 source GND transfers, remain fixed. Original Q/U leads are
the nine declared replacement tracks. This is not a complete routing check.
"""
import ast,json,sys,math,collections
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.affinity import rotate,translate
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168-pose-compare.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
base=json.loads((b/'R167B-plan.json').read_text());retired=set(base['delete_copper']);mv='74c0d925-81e9-4f8b-8224-202391f21e26'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
def yard(f):
 ly=pcb.F_CrtYd if f.GetLayer()==pcb.F_Cu else pcb.B_CrtYd
 lines=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=ly:continue
  a,z=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,z]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],z[0]),min(a[1],z[1]),max(a[0],z[0]),max(a[1],z[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(lines))))
fps={f.GetReference():f for f in c.footprints};rows=[]
for ref in ['Q1701','U1702']:
 f0=fps[ref];ly=c.board.GetLayerName(f0.GetLayer());other=[f for f in c.footprints if f.GetLayer()==f0.GetLayer() and f.GetReference()!=ref]
 foreign_yards=[(f.GetReference(),yard(f)) for f in other]
 owned={uid(q) for q in f0.Pads()}
 otherpads=[q for q in c.pads if uid(q) not in owned and (uid(q),ly) in c.shapes]
 fixedvias=[v for v in c.vias if uid(v)!=mv and (uid(v),ly) in c.shapes]
 tracks=[t for t in c.segments if uid(t) not in retired and c.board.GetLayerName(t.GetLayer())==ly]
 guards=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
 assert not any('_VIA_' in k['name'] for k in guards)
 poses=([(x,y,270) for x in [57,57.125,57.25,57.375] for y in [13.875,14,14.125]] if ref=='Q1701' else [(x,y,a) for x in [57.75,58,58.25] for y in [15,15.25,15.5] for a in [90,180,270]])
 for x,y,angle in poses:
  f=pcb.FOOTPRINT(f0);f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));pp=[(q,shape(q,f.GetLayer())) for q in f.Pads()]
  dx=x-xy(f0.GetPosition())[0];dy=y-xy(f0.GetPosition())[1];da=angle-f0.GetOrientationDegrees()
  moved_guards=[dict(k,shape=translate(rotate(k['shape'],-da,origin=xy(f0.GetPosition())),xoff=dx,yoff=dy)) for k in guards]
  hits=[]
  for name,g in foreign_yards:
   if yard(f).intersection(g).area>1e-8:hits.append(dict(kind='courtyard',reference=name))
  for q,s in pp:
   for oq in otherpads:
    if oq.GetNetname()!=q.GetNetname() and s.distance(c.shapes[uid(oq),ly])<.199999:
     hits.append(dict(kind='pad',pad=q.GetNumber(),other=c.pad_name(oq)))
   for v in fixedvias:
    if s.distance(c.shapes[uid(v),ly])<.199999:hits.append(dict(kind='via_to_pad',pad=q.GetNumber(),via_uuid=uid(v),position_mm=list(xy(v.GetPosition()))))
   for t in tracks:
    if t.GetNetname()!=q.GetNetname() and s.distance(c.shapes[uid(t),ly])<.199999:hits.append(dict(kind='track_to_pad',pad=q.GetNumber(),uuid=uid(t),net=t.GetNetname()))
  for k in moved_guards:
   for v in fixedvias:
    if k['vias'] and k['shape'].intersects(c.shapes[uid(v),ly]):hits.append(dict(kind='native_via_guard',guard=k['name'],via_uuid=uid(v)))
   for t in tracks:
    if k['tracks'] and ly in k['layers'] and k['shape'].intersects(c.shapes[uid(t),ly]):hits.append(dict(kind='native_track_guard',guard=k['name'],uuid=uid(t)))
  row=dict(reference=ref,position_mm=[x,y],rotation_deg=angle,hits=hits,status='CANDIDATE' if not hits else 'REJECTED')
  if ref=='U1702':
   cap=next(q for q in c.pads if c.pad_name(q)=='C1702.1');vdd=next(q for q,s in pp if q.GetNumber()=='5');row['nominal_VDD_cap_distance_mm']=math.dist(xy(cap.GetPosition()),xy(vdd.GetPosition()))
  rows.append(row)
 print(ref,'candidates',[(r['position_mm'],r['rotation_deg']) for r in rows if r['reference']==ref and not r['hits']],flush=True)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,movable_non_ground_via=mv,rows=rows,adopted=False),indent=2)+'\n')
