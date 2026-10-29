import json,sys,math
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from shapely.geometry import box
root=Path('robot/.state/c3-completion/trials');c=Copper(root/'R125B/MORI_Interface_C3.kicad_pcb')
f=next(f for f in c.footprints if f.GetReference()=='C1208');f.BuildCourtyardCaches();court=polyset(f.GetCourtyard(pcb.B_Cu))
pads={p.GetNumber():p for p in f.Pads()};out={'board_sha256':c.sha,'reference':'C1208','position_mm':xy(f.GetPosition()),'orientation_deg':f.GetOrientationDegrees(),'face':c.board.GetLayerName(f.GetLayer()),'pad_positions':{k:xy(v.GetPosition()) for k,v in pads.items()}}
net='/HEAD_VM';hp=uid(pads['1']);gp=uid(pads['2']);names={uid(p):c.pad_name(p) for p in c.pads};out['HEAD_VM_groups']=c.pad_groups()[net];out['new_anchor_width_corridors']=[]
for w in [0,.2,.3,.4,.48]:
 pairs=c.connected_pairs(net,w);neighbors={b if a==hp else a for a,b in pairs if hp in (a,b)}
 out['new_anchor_width_corridors'].append({'width_mm':w,'connected_pad_names':sorted(names[v] for v in neighbors if v in names)})
near=[];opposite=[]
for q in c.footprints:
 if q==f:continue
 q.BuildCourtyardCaches();ly=q.GetLayer();s=polyset(q.GetCourtyard(ly))
 if not s.is_empty:
  if ly==pcb.B_Cu:near.append({'reference':q.GetReference(),'courtyard_gap_mm':court.distance(s)})
  elif s.intersects(court):opposite.append({'reference':q.GetReference(),'projected_courtyard_overlap_mm2':s.intersection(court).area})
out['nearest_same_face_courtyards']=sorted(near,key=lambda r:r['courtyard_gap_mm'])[:6];out['opposite_face_courtyards']=opposite
ownpads=unary_union([c.shapes[uid(p),'B.Cu'] for p in pads.values()]);body=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_C1208_') and k['tracks']])
out['native_body_bounds_mm']=body.bounds;out['reference_ground_beneath_moved_lands']={layer:{'uncovered_body_mm2':body.difference(c.copper['GND',layer]).area,'uncovered_pad_mm2':ownpads.difference(c.copper['GND',layer]).area} for layer in ['In1.Cu','In4.Cu']}
out['other_layers_under_native_body']=[]
for (id_,layer),s in c.shapes.items():
 if layer=='B.Cu' or not s.intersects(body):continue
 o=c.by_id[id_];out['other_layers_under_native_body'].append({'layer':layer,'net':o.GetNetname(),'item':c.pad_name(o),'type':type(o).__name__,'overlap_mm2':body.intersection(s).area})
out['nearest_ground_stitches']=sorted([{'uuid':uid(v),'position_mm':xy(v.GetPosition()),'distance_from_ground_pad_mm':Point(xy(v.GetPosition())).distance(Point(xy(pads['2'].GetPosition())))} for v in c.vias if v.GetNetname()=='GND' and all((uid(v),n) in c.shapes and c.shapes[uid(v),n].intersects(c.copper['GND',n]) for n in ['B.Cu','In1.Cu','In4.Cu'])],key=lambda r:r['distance_from_ground_pad_mm'])[:3]
out['ground_pad_other_net_clearance_mm']=min(c.shapes[gp,'B.Cu'].distance(s) for (id_,ly),s in c.shapes.items() if ly=='B.Cu' and c.by_id[id_].GetNetname()!='GND')
out['head_pad_existing_trace_contact']=[{'uuid':uid(t),'width_mm':t.GetWidth()/1e6,'contact_area_mm2':c.shapes[hp,'B.Cu'].intersection(c.shapes[uid(t),'B.Cu']).area} for t in c.segments if t.GetNetname()==net and c.board.GetLayerName(t.GetLayer())=='B.Cu' and c.shapes[hp,'B.Cu'].intersects(c.shapes[uid(t),'B.Cu'])]
out['qualification']='Geometric/electrical connectivity screen only; no current, thermal, EMC or physical validation'
(root/'R125B-placement-review.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
