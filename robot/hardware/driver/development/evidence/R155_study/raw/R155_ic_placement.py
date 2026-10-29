"""Bounded U1301 pose/OV escape study before any local block re-layout.

Other component courtyards, pads, all existing vias and native keepouts are
preserved. Old tracks may require explicit re-routing and are enumerated.
No saved model, routed block, or physical qualification is implied.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R155-ic-placement.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
f=next(f for f in c.footprints if f.GetReference()=='U1301');origin=xy(f.GetPosition());a0=f.GetOrientationDegrees();pads=list(f.Pads());own={uid(p) for p in pads};lid=pcb.B_Cu;net='Net-(U1301-INB-_{slash}_OV)'
court=polyset(f.GetCourtyard(pcb.B_CrtYd));body=fab(f)
other_courts=prep(unary_union([polyset(q.GetCourtyard(pcb.B_CrtYd)) for q in c.footprints if q.GetReference()!='U1301']))
pad_obs={p.GetNetname():prep(unary_union([s.buffer(.205) for (u,l),s in c.shapes.items() if l=='B.Cu' and u not in own and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=p.GetNetname()])) for p in pads}
via_for_pads=prep(unary_union([shape(v,lid).buffer(.205) for v in c.vias]))
via_obs=[s.buffer(.457) for (u,l),s in c.shapes.items() if u not in own and isinstance(c.by_id[u],pcb.PAD)]
via_obs += [shape(v,lid).buffer(.457) for v in c.vias]
other_guards=[k for k in c.keepouts if not k['name'].startswith('BODY_U1301_')]
via_obs += [k['shape'].buffer(.257) for k in other_guards if k['vias']]
via_obs += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.557) for p in c.pads if max(xy(p.GetDrillSize()))>0]
vo=prep(unary_union(via_obs))
other_body=unary_union([fab(q) for q in c.footprints if q.GetReference()!='U1301' and q.GetLayer()==lid])
other_track_guards=unary_union([k['shape'] for k in other_guards if k['tracks'] and 'B.Cu' in k['layers']])
other_pad=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and u not in own and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()!=net])
leg_ob=prep(unary_union([other_body.buffer(.102),other_track_guards.buffer(.102),other_pad.buffer(.305),unary_union([shape(v,lid) for v in c.vias if v.GetNetname()!=net]).buffer(.305)]))
ground=c.copper[('GND','In4.Cu')]
ground_anchors=[p for p in c.pads+c.vias if p.GetNetname()=='GND' and all((uid(p),ly) in c.shapes and c.shapes[uid(p),ly].intersects(c.copper[('GND',ly)]) for ly in ['In1.Cu','In4.Cu'])]
own_via_guard=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_U1301_') and k['vias']])
own_track_guard=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_U1301_') and k['tracks']])
fixed_via_cutouts=own_track_guard.difference(own_via_guard)
rows=[];stats=[]
for angle in [0,90,180,270]:
 passing=0
 for x in np.arange(40.0,45.001,.1):
  for y in np.arange(24.5,29.001,.1):
   pos=(round(float(x),6),round(float(y),6));tr=lambda g:translate(rotate(g,-(angle-a0),origin=origin),xoff=pos[0]-origin[0],yoff=pos[1]-origin[1])
   if other_courts.intersects(tr(court).buffer(-.002)):continue
   pp=[(p,tr(c.shapes[uid(p),'B.Cu'])) for p in pads]
   if any(pad_obs[p.GetNetname()].intersects(g) or via_for_pads.intersects(g) for p,g in pp):continue
   # Preserve the received 4 mm VDD-to-bypass adjacency screen explicitly.
   pg={p.GetNumber():g for p,g in pp};vdd=(pg['5'].centroid.x,pg['5'].centroid.y)
   if math.dist(vdd,(42.9,24.275))>4:continue
   passing+=1;signal=pg['4'];pin=(signal.centroid.x,signal.centroid.y)
   moved_body=tr(body);guards=tr(own_via_guard).difference(fixed_via_cutouts)
   local_via=unary_union([g.buffer(.457) for p,g in pp]).union(guards.buffer(.257))
   impact=[]
   for t in c.segments:
    if t.GetLayer()!=lid:continue
    tg=c.shapes[uid(t),'B.Cu'];land=unary_union([g for p,g in pp if p.GetNetname()==t.GetNetname()])
    hit=tg.intersection(moved_body).difference(land).area>1e-6 or any(t.GetNetname()!=p.GetNetname() and tg.intersects(g.buffer(.205)) for p,g in pp)
    if hit:impact.append({'uuid':uid(t),'net':t.GetNetname(),'layer':'B.Cu','start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'width_mm':t.GetWidth()/1e6})
   candidates=[]
   for vx in np.arange(pin[0]-1.8,pin[0]+1.801,.1):
    for vy in np.arange(pin[1]-1.8,pin[1]+1.801,.1):
     vp=(round(float(vx),6),round(float(vy),6));pt=Point(vp)
     if math.dist(vp,pin)>1.8 or vo.intersects(pt) or local_via.intersects(pt):continue
     line=LineString([pin,vp]);stroke=line.buffer(.1)
     if leg_ob.intersects(line) or stroke.intersection(moved_body).difference(signal).area>1e-6:continue
     if any(p.GetNumber()!='4' and stroke.intersects(g.buffer(.2)) for p,g in pp):continue
     if stroke.difference(ground.union(signal)).area>1e-6:continue
     near=min(math.dist(vp,xy(q.GetPosition())) for q in ground_anchors)
     if near>2:continue
     hits=[]
     hole=pt.buffer(.655)
     for t in c.segments:
      ly=c.board.GetLayerName(t.GetLayer())
      if t.GetNetname()=='GND' or ly not in REFERENCE:continue
      ar=c.shapes[uid(t),ly].intersection(c.copper[('GND',REFERENCE[ly])]).intersection(hole).area
      if ar>1e-6:hits.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'reference_area_mm2':ar})
     candidates.append({'position_mm':vp,'length_mm':line.length,'nearest_ground_mm':near,'required_old_reference_repairs':hits})
   if candidates:
    candidates.sort(key=lambda z:(len(z['required_old_reference_repairs']),z['length_mm']))
    rows.append({'position_mm':pos,'angle_deg':angle,'pads_mm':{k:(g.centroid.x,g.centroid.y) for k,g in pg.items()},'VDD_bypass_distance_mm':math.dist(vdd,(42.9,24.275)),'old_back_tracks_requiring_review':impact,'via_proposals':candidates[:8],'score':len(impact)*3+len(candidates[0]['required_old_reference_repairs'])*3+math.dist(pos,origin)})
 stats.append({'angle':angle,'placement_poses':passing,'with_short_OV_escape':sum(r['angle_deg']==angle for r in rows)});print(json.dumps(stats[-1]),flush=True)
 rows.sort(key=lambda z:z['score'])
 out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'stats':stats,'poses':rows,'adopted':False,'physical':'NOT_TESTED'},indent=2)+'\n')
print(json.dumps({'count':len(rows),'best':rows[:2]}),flush=True)
