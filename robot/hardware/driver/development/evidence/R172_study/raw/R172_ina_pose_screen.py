"""Read-only quarter-turn/translation comparison for the INA300 functional group.

Five named parts may be relocated; three exact non-ground supply transfers and
enumerated local leads are prospective replacements. All other pads, source GND
vias, native guards and retained copper/reference remain obstacles. This is a
bounded placement/straight-FAULT-port screen, not a routed or accepted board.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
from shapely.affinity import translate,rotate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R172-ina-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
refs={'U1701','R1701','C1701','R1706','R1707'};fps={f.GetReference():f for f in c.footprints};padids={uid(p) for ref in refs for p in fps[ref].Pads()}
movepos={(46.3,11.85),(45.29,10.05),(44.575,10.125)};movable={uid(v):v for v in c.vias if xy(v.GetPosition()) in movepos};assert len(movable)==3 and all(v.GetNetname()!='GND' for v in movable.values())
private={'Net-(U1701-IN+)','Net-(U1701-IN-)','Net-(U1701-LIMIT)'}
retired={uid(t) for t in c.segments if t.GetNetname() in private}
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer());g=c.shapes[uid(t),ly]
 if any(t.GetNetname()==c.by_id[u].GetNetname() and (u,ly) in c.shapes and g.intersects(c.shapes[u,ly]) for u in padids|set(movable)):retired.add(uid(t))
# Include the complete local explicit GND track component seeded by these parts;
# no fills/via barrels or other layers are used to expand the component.
window=box(41,6,54,16)
for ly in ['F.Cu','B.Cu']:
 seeds=[s for (u,l),s in c.shapes.items() if l==ly and u in padids and c.by_id[u].GetNetname()=='GND']
 tracks=[t for t in c.segments if c.board.GetLayerName(t.GetLayer())==ly and t.GetNetname()=='GND' and window.covers(c.shapes[uid(t),ly])]
 region=unary_union([g for g in parts(unary_union(seeds+[c.shapes[uid(t),ly] for t in tracks])) if any(g.intersects(s) for s in seeds)])
 retired.update(uid(t) for t in tracks if c.shapes[uid(t),ly].intersects(region))
face='B.Cu';owned={ref:[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')] for ref in refs}
old=fps['U1701'];origin=xy(old.GetPosition());angle0=old.GetOrientationDegrees();uowned=owned['U1701'];body_guard=unary_union([k['shape'] for k in uowned if k['tracks']]);via_guard=unary_union([k['shape'] for k in uowned if k['vias']]);assert via_guard.difference(body_guard).area<1e-8
fixed_holes=body_guard.difference(via_guard)
fb=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in refs]);fy=unary_union([outline(f,pcb.B_CrtYd) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in refs])
vl=unary_union([s for (u,l),s in c.shapes.items() if l==face and isinstance(c.by_id[u],pcb.PCB_VIA) and u not in movable])
ts=unary_union([c.shapes[uid(t),face] for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in retired])
unets={p.GetNetname() for p in old.Pads()};foreign={n:unary_union([s for (u,l),s in c.shapes.items() if l==face and u not in padids|retired|set(movable) and not isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=n]) for n in unets}
ground=c.copper['GND','In4.Cu'];keep=[k for k in c.keepouts if not any(k['name'].startswith('BODY_'+r+'_') for r in refs)]
ref_strokes=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(c.copper.get(('GND',REFERENCE[c.board.GetLayerName(t.GetLayer())]),GeometryCollection())) for t in c.segments if uid(t) not in retired and t.GetNetname()!='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
physical=[s.buffer(.457) for (u,ly),s in c.shapes.items() if u not in padids|retired|set(movable) and c.by_id[u].GetNetname()!='/FAULT_N']
physical += [s.buffer(.457) for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD) and u not in padids]
physical += [k['shape'].buffer(.257) for k in keep if k['vias']]
physical += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v) not in movable]
physical += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
port_block=unary_union(physical+[unary_union(ref_strokes).buffer(.657)])
track_block=unary_union([foreign['/FAULT_N'].buffer(.305),vl.buffer(.305),fb.buffer(.102)]+[k['shape'].buffer(.102) for k in keep if k['tracks'] and face in k['layers']])
rows=[];reject=collections.Counter();start=time.monotonic()
points=[(x/4,y/4) for x in range(176,205) for y in range(38,65)]+[origin]
for x,y in points:
 for angle in [0,90,180,270]:
  f=pcb.FOOTPRINT(old);f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));body=fab(f);yard=outline(f,pcb.B_CrtYd)
  if body.intersection(fb).area>1e-8 or yard.intersection(fy).area>1e-8:reject['body_or_courtyard']+=1;continue
  pp=[(p.GetNumber(),p.GetNetname(),shape(p,pcb.B_Cu),xy(p.GetPosition())) for p in f.Pads()]
  if any(s.distance(vl)<.2-1e-6 for _,_,s,_ in pp):reject['fixed_via_pad']+=1;continue
  if any(s.distance(foreign[n])<.2-1e-6 for _,n,s,_ in pp):reject['retained_copper']+=1;continue
  moved=translate(rotate(body_guard,-(angle-angle0),origin=origin),xoff=x-origin[0],yoff=y-origin[1]);vg=moved.difference(fixed_holes)
  if vg.intersection(vl).area>1e-8:reject['native_fixed_via_guard']+=1;continue
  if moved.intersection(ts).area>1e-8:reject['native_retained_track_guard']+=1;continue
  if body.difference(unary_union([p[2] for p in pp])).intersection(ts).area>1e-8:reject['retained_track_under_body']+=1;continue
  fault=next(p for p in pp if p[0]=='5');direction=[(-1,0),(0,1),(1,0),(0,-1)][angle//90]
  own_block=unary_union([p[2].buffer(.457) for p in pp]+[vg.buffer(.257)])
  route_block=unary_union([track_block,moved.buffer(.102),body.buffer(.102).difference(fault[2].buffer(-.001)),unary_union([p[2].buffer(.305) for p in pp if p[1]!='/FAULT_N'])])
  ports=[]
  for d in [1.2+i*.05 for i in range(27)]:
   pos=(fault[3][0]+d*direction[0],fault[3][1]+d*direction[1]);point=Point(pos)
   if port_block.intersects(point) or own_block.intersects(point):continue
   line=LineString([fault[3],pos])
   if line.intersects(route_block):continue
   # Conservative source GND plus actual new terminal/own transfer allowances.
   allowed=unary_union([ground,fault[2],point.buffer(.655)]).buffer(-.102)
   if not allowed.covers(line):continue
   conflicts=[u for u,v in movable.items() if any(p[2].distance(c.shapes[u,face])<.2-1e-6 for p in pp) or vg.intersects(c.shapes[u,face]) or point.distance(Point(xy(v.GetPosition())))<.71]
   ports.append(dict(position_mm=[round(v,6) for v in pos],straight_length_mm=d,requires_supply_via_relocation=conflicts))
  row=dict(position_mm=[x,y],rotation_deg=angle,pads={p[0]:list(p[3]) for p in pp},ports=ports,score=math.dist([x,y],origin)+.3*(angle!=angle0)+.5*min((len(p['requires_supply_via_relocation']) for p in ports),default=9));rows.append(row)
rows.sort(key=lambda r:(not bool(r['ports']),r['score']))
result=dict(scope=__doc__,source_sha256=c.sha,grid_mm=.25,bounds_mm=[44,9.5,51,16],prospectively_moved_parts=sorted(refs),prospectively_retired_tracks=sorted(retired),prospectively_movable_vias=[dict(uuid=u,net=v.GetNetname(),position_mm=list(xy(v.GetPosition()))) for u,v in movable.items()],rejections=dict(reject),poses=rows,elapsed_seconds=time.monotonic()-start,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),with_ports=sum(bool(x['ports']) for x in rows),by_rotation=dict(collections.Counter(x['rotation_deg'] for x in rows if x['ports'])),retired_tracks=len(retired),rejections=dict(reject),elapsed_seconds=result['elapsed_seconds'])),flush=True)
for angle in [0,90,180,270]:
 for row in [x for x in rows if x['rotation_deg']==angle and x['ports']][:3]:print(json.dumps(row),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
