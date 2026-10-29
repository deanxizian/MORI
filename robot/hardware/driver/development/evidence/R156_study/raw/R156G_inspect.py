"""Read-only exact local supply, divider, body and clearance inspection of R156G."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R156G-inspection.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R156G/MORI_Interface_C3.kicad_pcb')
assert a.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
pa={a.pad_name(p):p for p in a.pads};pc={c.pad_name(p):p for p in c.pads};supply=[]
vias=['9fc6be27-25b2-4bce-8f44-98f39ccd1aa1','aa3ea505-081f-4d12-a9a9-b7d9b2cf4e57','c89d9b75-62b7-4bdc-8fe8-09516366b58c']
for w in [0,.18,.28,.33,.48]:
 row={'width_mm':w}
 for name,obj,pads in [('source',a,pa),('candidate',c,pc)]:
  pairs=obj.connected_pairs('MOTION_3V3',w)
  row[name]={via:{pad:tuple(sorted([via,uid(pads[pad])])) in pairs for pad in ['C1701.1','U1701.4','U1701.9','R1310.2']} for via in vias}
 supply.append(row)
assert all((not row['source'][v][p]) or row['candidate'][v][p] for row in supply for v in vias for p in ['C1701.1','U1701.4','U1701.9','R1310.2'])
new=[]
for t in c.segments:
 if uid(t) in a.by_id:continue
 ly=c.board.GetLayerName(t.GetLayer());lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==t.GetNetname()]);outside=c.shapes[uid(t),ly].difference(lands);projections=[]
 for f in c.footprints:
  area=outside.intersection(fab(f)).area
  if area>1e-6:projections.append({'reference':f.GetReference(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),'same_face':f.GetLayer()==t.GetLayer(),'area_mm2':area})
 new.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'length_mm':LineString([xy(t.GetStart()),xy(t.GetEnd())]).length,'nominal_body_projections':projections})
wheel=[]
for w in [0,.18]:
 pairs=c.connected_pairs('/WHEEL_VM',w);wheel.append({'width_mm':w,'R1702_to_R1101':tuple(sorted([uid(pc['R1702.1']),uid(pc['R1101.2'])])) in pairs,'R1702_to_R1002':tuple(sorted([uid(pc['R1702.1']),uid(pc['R1002.1'])])) in pairs})
assert all(x['R1702_to_R1101'] and not x['R1702_to_R1002'] for x in wheel)
fps={f.GetReference():f for f in c.footprints};gvia='01448c59-3902-4b17-8362-1f1ec1c425ab'
d={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':len(new)},'MOTION_3V3_local_source_preserved':True,'local_supply_width_pairs':supply,'supply_vias':[{'uuid':v,'snapshot_unchanged':via_snapshot(a.board,a.by_id[v])==via_snapshot(c.board,c.by_id[v]),'native_contact_layers':via_contact_layers(c.board,c.by_id[v])} for v in vias],'wheel_tap_width_screen':wheel,'wheel_groups':c.pad_groups()['/WHEEL_VM'],'new_tracks':new,'same_face_nominal_body_hit_count':sum(p['same_face'] for t in new for p in t['nominal_body_projections']),'R1702_R1703_courtyard_gap_mm':polyset(fps['R1702'].GetCourtyard(c.ids['F.Cu'])).distance(polyset(fps['R1703'].GetCourtyard(c.ids['F.Cu']))),'R1703_pad2_to_fixed_ground_via_copper_gap_mm':c.shapes[uid(pc['R1703.2']),'F.Cu'].distance(c.shapes[gvia,'F.Cu']),'source_middle_node_length_mm':sum(LineString([xy(a.by_id[u].GetStart()),xy(a.by_id[u].GetEnd())]).length for u in ['a9295a25-0725-4f1f-ae2c-8822b258bcec','673dca86-7975-4381-ac89-1e83cd82b8e5']),'candidate_middle_node_length_mm':sum(t['length_mm'] for t in new if t['net']=='Net-(R1702-~-Pad2)'),'new_wheel_tap_length_mm':sum(t['length_mm'] for t in new if t['net']=='/WHEEL_VM'),'limits':['Width erosion is corridor continuity, not current rating or via ampacity.','Fab bodies are nominal library geometry, not measured full component envelopes.','The 0.20 mm new branch serves only the existing 100k/100k sense divider; main actuator feed stays unchanged.','Opposite-face INA300 projection needs individual return/coupling/thermal review.'],'physical':'NOT_TESTED','manufacturing_release':False}
assert d['same_face_nominal_body_hit_count']==0
out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:d[k] for k in ['candidate_sha256','counts','wheel_groups','same_face_nominal_body_hit_count','R1702_R1703_courtyard_gap_mm','R1703_pad2_to_fixed_ground_via_copper_gap_mm','candidate_middle_node_length_mm','source_middle_node_length_mm','new_wheel_tap_length_mm']}));print(json.dumps({'opposite_projections':sorted({p['reference'] for t in new for p in t['nominal_body_projections']})}))
