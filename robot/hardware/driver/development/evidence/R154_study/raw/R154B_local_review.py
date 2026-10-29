"""Read-only local power-trunk and mandatory native input-land escape review."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R154B-local-review.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R154B/MORI_Interface_C3.kicad_pcb');assert a.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
pa={a.pad_name(p):p for p in a.pads};pc={c.pad_name(p):p for p in c.pads};rows=[]
for w in [0,.2,.28,.3,.4,.48]:
 row={'width_mm':w}
 for key,obj,pads in [('source',a,pa),('candidate',c,pc)]:
  pairs=obj.connected_pairs('/HEAD_6V_RAW',w)
  row[key]={target:tuple(sorted([uid(pads['L901.2']),uid(pads[target])])) in pairs for target in ['C1201.1','C1202.1','C909.1','C911.1','U1201.5']}
 rows.append(row)
assert all(next(x for x in rows if x['width_mm']==.48)['candidate'][k] for k in ['C1201.1','C1202.1','C909.1','C911.1'])
new=[]
for t in c.segments:
 if uid(t) in a.by_id:continue
 ly=c.board.GetLayerName(t.GetLayer());lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==t.GetNetname()]);outside=c.shapes[uid(t),ly].difference(lands);projections=[]
 for f in c.footprints:
  area=outside.intersection(fab(f)).area
  if area>1e-6:projections.append({'reference':f.GetReference(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),'same_face':f.GetLayer()==t.GetLayer(),'area_mm2':area})
 new.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'length_mm':LineString([xy(t.GetStart()),xy(t.GetEnd())]).length,'nominal_body_projections':projections})
u='1b3035a7-c9ba-44db-9674-ec974420a31b';gv='06d811e4-9241-4812-beaf-c1a19399b4a6'
d={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints)},'power_width':rows,'new_tracks':new,'same_face_body_hits':sum(x['same_face'] for t in new for x in t['nominal_body_projections']),'moved_via':{'source':via_snapshot(a.board,a.by_id[u]),'candidate':via_snapshot(c.board,c.by_id[u]),'candidate_contacts':via_contact_layers(c.board,c.by_id[u])},'unchanged_ground_via':{'snapshot':via_snapshot(c.board,c.by_id[gv]),'source_identical':via_snapshot(a.board,a.by_id[gv])==via_snapshot(c.board,c.by_id[gv]),'new_cap_raw_pad_copper_clearance_mm':c.shapes[uid(pc['C1201.1']),'F.Cu'].distance(c.shapes[gv,'F.Cu'])},'terminal_escape':{'net':'/HEAD_6V_RAW','layer':'F.Cu','width_mm':.3,'start_mm':[8.95,24.75],'end_mm':[9.35,24.75],'nominal_length_mm':.4,'native_pad_bounds_mm':list(c.shapes[uid(pc['U1201.5']),'F.Cu'].bounds),'why':'The unchanged 0.30 mm-high native input land and adjacent output land limit the final pin escape. The 0.50 mm trunk reaches both bypass capacitors; no full-terminal 0.48 mm claim is made.','footprint_manufacturer_land_pattern_qualification':'Separate from native geometry review.'},'physical':'NOT_TESTED','manufacturing_release':False}
out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'candidate_sha256':c.sha,'counts':d['counts'],'power_width':rows,'same_face_body_hits':d['same_face_body_hits'],'projections':{t['uuid']:t['nominal_body_projections'] for t in new if t['nominal_body_projections']},'ground_via_clearance':d['unchanged_ground_via']['new_cap_raw_pad_copper_clearance_mm']}),flush=True)
