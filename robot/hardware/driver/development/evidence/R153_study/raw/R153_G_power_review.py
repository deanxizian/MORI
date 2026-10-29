"""Read-only check of actual added supply corridor and inherited terminal limits."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R153G-power-review.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(b/'R153G/MORI_Interface_C3.kicad_pcb')
ps={c.pad_name(p):p for p in c.pads};newvia=next(v for v in c.vias if uid(v) not in a.by_id)
assert a.sha=='7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9'
assert c.sha=='a9121d98d1c6c5d86acbdb473a0873b76fe07ae8e85f26212c999d552f844ca0'
source_pads={a.pad_name(p):p for p in a.pads};rows=[]
for w in [0,.2,.28,.3,.4,.48,.5,.6]:
 pairs=c.connected_pairs('/HEAD_6V_RAW',w);oldpairs=a.connected_pairs('/HEAD_6V_RAW',w)
 targets=[('C911.1',uid(ps['C911.1'])),('C904.1',uid(ps['C904.1'])),('L901.2',uid(ps['L901.2']))]+[(str(xy(v.GetPosition())),uid(v)) for v in a.vias if v.GetNetname()=='/HEAD_6V_RAW' and 21<v.GetPosition().y/1e6<24]
 rows.append({'width_mm':w,'new_C909_paths':{name:tuple(sorted([uid(ps['C909.1']),u])) in pairs for name,u in targets},'new_via_paths':{name:tuple(sorted([uid(newvia),u])) in pairs for name,u in targets},'source_L901_to_U1201':tuple(sorted([uid(source_pads['L901.2']),uid(source_pads['U1201.5'])])) in oldpairs,'candidate_L901_to_U1201':tuple(sorted([uid(ps['L901.2']),uid(ps['U1201.5'])])) in pairs})
assert all(next(r for r in rows if r['width_mm']==.48)['new_C909_paths'].values())
assert all(next(r for r in rows if r['width_mm']==.48)['new_via_paths'].values())
assert all(r['source_L901_to_U1201']==r['candidate_L901_to_U1201'] for r in rows)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
added=c.copper['/HEAD_6V_RAW','In2.Cu'].difference(a.copper['/HEAD_6V_RAW','In2.Cu'])
projections=[]
for f in c.footprints:
 area=added.intersection(fab(f)).area
 if area>1e-6: projections.append({'reference':f.GetReference(),'value':f.GetValue(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),'new_In2_power_copper_nominal_body_projection_mm2':area,'position_mm':xy(f.GetPosition())})
def track_signature(board,t):
 return (t.GetNetname(),board.GetLayerName(t.GetLayer()),t.GetWidth(),xy(t.GetStart()),xy(t.GetEnd()))
source_feed=[]
for t in a.segments:
 if t.GetNetname()=='/HEAD_6V_RAW' and LineString([xy(t.GetStart()),xy(t.GetEnd())]).intersects(box(7,22,13,27)):
  source_feed.append({'uuid':uid(t),'layer':a.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'retained_exactly':uid(t) in c.by_id and track_signature(a.board,t)==track_signature(c.board,c.by_id[uid(t)])})
d={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'new_supply_width_checks':rows,'added_In2_copper_nominal_projections':projections,'source_U1201_region_tracks':source_feed,'preliminary_report_note':'The earlier preliminary report used UUID presence for the field named retained_exactly. This corrected report compares net, layer, width and exact endpoints; the preliminary bytes are retained separately.', 'new_via':via_snapshot(c.board,newvia),'new_via_native_contact_layers':via_contact_layers(c.board,newvia),'unchanged_original_power_via_drill_mm':.4,'new_path_screen_status':'PASS','inherited_U1201_input_width_limit':'The unchanged 0.30 mm L901-to-U1201 input branch has separate source/candidate corridor results below; equal-width erosion can collapse this branch. It is not a 0.48 mm path. This is retained open for full power-path review, not claimed 0.48 mm throughout the downstream input.','limits':['Widths are eroded geometric corridor screens using native lands, not current/ripple/plating/thermal qualification.','0.50 mm traces can collapse under equal-width erosion; 0.48 mm is a screening allowance, not an IPC current rating.','New In2 allocation is reviewed with original reference planes and adjacent nets; no blanket all-layer body prohibition is invented.'], 'physical':'NOT_TESTED','manufacturing_release':False}
out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'width_checks':rows,'projections':projections,'source_U1201_region_tracks':source_feed}))
