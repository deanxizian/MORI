"""Read-only nominal-body and actual declared filter-path inspection of R161R.
This incomplete working layout is not accepted. Native checks and local views
do not qualify actual thermal, coupling, protection or physical performance.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161R-inspection.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(str(b/'R161R/MORI_Interface_C3.kicad_pcb'))
p=json.loads((b/'R161R-plan.json').read_text());assert p['board_sha256']==a.sha
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={f.GetReference():fab(f) for f in c.footprints};faces={f.GetReference():c.board.GetLayerName(f.GetLayer()) for f in c.footprints}
same=[];opposite=[]
for t in c.segments:
 if uid(t) in a.by_id:continue
 ly=c.board.GetLayerName(t.GetLayer());net=t.GetNetname();stroke=c.shapes[(uid(t),ly)]
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 outside=stroke.difference(lands)
 for ref,body in bodies.items():
  area=outside.intersection(body).area
  if area<=1e-6:continue
  row={'uuid':uid(t),'net':net,'layer':ly,'component':ref,'component_face':faces[ref],'area_mm2':area}
  (same if ly==faces[ref] else opposite).append(row)
ground=[v for v in a.vias if v.GetNetname()=='GND']
assert all(uid(v) in c.by_id and via_snapshot(a.board,v)==via_snapshot(c.board,c.by_id[uid(v)]) for v in ground)
fs={f.GetReference():f for f in c.footprints};source_fs={f.GetReference():f for f in a.footprints}
clamps=[]
for ref in ['D1802','D1803']:
 f=fs[ref];s=source_fs[ref]
 assert xy(f.GetPosition())==xy(s.GetPosition()) and f.GetOrientationDegrees()==s.GetOrientationDegrees() and f.GetFPIDAsString()==s.GetFPIDAsString()
 clamps.append({'reference':ref,'value':f.GetValue(),'footprint':f.GetFPIDAsString(),'position_mm':xy(f.GetPosition()),'rotation_deg':f.GetOrientationDegrees(),'unchanged_from_source':True})
path=list(reversed(p['routes'][21]['points_mm']))+p['routes'][20]['points_mm'][1:]+p['routes'][6]['points_mm'][-2:]
assert path[0]==[65.65,28.275] and path[-1]==[64.0625,26.95]
images=sorted(x.name for x in (b/'R161R-views').glob('*.png'));assert len(images)==13
result={'scope':__doc__,'source_sha256':a.sha,'board_sha256':c.sha,'source_ground_vias_preserved':len(ground),
 'clamps':clamps,'same_face_nominal_body_hits':same,'opposite_or_internal_body_hits':opposite,
 'C1301_to_actual_U1301_3':{'path_mm':path,'nominal_centerline_length_mm':sum(math.dist(x,y) for x,y in zip(path,path[1:])),'layers':['F.Cu','B.Cu'],'transfer_mm':[64.2,26.1],'actual_input_pin':'U1301.3','complete_divider_connection':False,'physical_filter_performance':'NOT_TESTED'},
 'images_actually_viewed':images,
 'findings':['C1301 and R1503 share a joint F-face placement; C1301 has an explicit local transfer to the actual U1301 UV input. R1302 upstream is still disconnected.',
 'OV is connected through the F corridor west of J401, the lower In2 exit and a B escape. The small F jog and overall detour remain candidates for final route-style optimization; the native thermal and power tests pass.',
 'ACT_UV_N replaces three F tails with one direct outward escape. The U402-1Y non-ground transfer moves down 0.1 mm; both source branches are explicitly replaced.',
 'U1501 OV transfer at (64.45,31.275) now meets the existing nearby-ground screen. Its small nominal margin to the H4 native guard is not manufacturing tolerance qualification.',
 'The four still-unrestored circuit links and four dangling DRC items prevent acceptance. All exact-delta checks except preservation of prior pad connections pass; source canonical remains R159H.'],
 'local_visual_status':'INCOMPLETE','whole_board_visual':'NOT_TESTED','thermal_coupling_and_manufacturer_layout':'NOT_TESTED','adopted':False,'manufacturing_release':False}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'same_face_hits':len(same),'opposite_or_internal_hits':len(opposite),'filter_centerline_mm':result['C1301_to_actual_U1301_3']['nominal_centerline_length_mm'],'preserved_ground_vias':len(ground)}))
