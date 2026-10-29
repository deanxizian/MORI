"""Read-only exact native metrics and nominal projections for local review; no physical qualification."""
import ast,json,sys,math
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R152N/MORI_Interface_C3.kicad_pcb');out=b/'R152N-local-metrics.json';assert not out.exists()
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
old={uid(t) for t in a.segments};new=[t for t in c.segments if uid(t) not in old];rows=[]
for t in new:
 ly=c.board.GetLayerName(t.GetLayer());net=t.GetNetname();stroke=c.shapes[uid(t),ly];own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);outside=stroke.difference(own);hits=[]
 for f in c.footprints:
  area=outside.intersection(fab(f)).area
  if area>1e-6:hits.append({'reference':f.GetReference(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),'projected_intersection_mm2':area,'same_face':c.board.GetLayerName(f.GetLayer())==ly})
 rows.append({'uuid':uid(t),'net':net,'layer':ly,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'length_mm':math.dist(xy(t.GetStart()),xy(t.GetEnd())),'nominal_body_projections':hits})
p=json.loads((b/'R152N-plan.json').read_text());r=json.loads((b/'R152N-audit.json').read_text());report={'source_sha256':a.sha,'candidate_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':len(new),'removed_segments':len(p['delete_copper']),'new_vias':len(p['vias']),'removed_obsolete_vias':len(p.get('remove_obsolete_vias',[]))},'new_tracks':rows,'same_face_body_hits':sum(x['same_face'] for row in rows for x in row['nominal_body_projections']),'new_transitions':[x for x in r['reference_transitions'] if x['uuid'] not in a.by_id or x['uuid'] in {v['uuid'] for v in p.get('reassign_vias',[])}],'method_limits':['Nominal Fab geometry and fallback outlines, not measured or manufacturer maximum body envelopes.','Individual opposite/internal reference, coupling and thermal review required.','No physical or manufacturing qualification.']}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'counts':report['counts'],'same_face_hits':report['same_face_body_hits'],'projection_groups':sorted({(h['reference'],row['net'],row['layer']) for row in rows for h in row['nominal_body_projections']}),'new_transitions':report['new_transitions']}));assert all(h['reference']=='J101' and row['layer']=='F.Cu' and row['start_mm'][0]==row['end_mm'][0]==12.45 for row in rows for h in row['nominal_body_projections'] if h['same_face']), 'Any other same-face overlap remains unresolved'
