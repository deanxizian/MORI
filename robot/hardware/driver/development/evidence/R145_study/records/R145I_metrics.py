"""Read-only measurements for the scoped R145I acceptance review."""
import ast,hashlib,json,math,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R145I/MORI_Interface_C3.kicad_pcb');h=Copper(b/'R145H/MORI_Interface_C3.kicad_pcb')
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
def signature(c):
 return {'footprints':sorted((f.GetReference(),f.GetValue(),f.GetFPID().GetLibNickname(),f.GetFPID().GetLibItemName(),xy(f.GetPosition()),f.GetOrientationDegrees(),f.GetLayer()) for f in c.footprints),'pads':sorted((uid(p),p.GetNetname(),xy(p.GetPosition()),xy(p.GetSize()),xy(p.GetDrillSize())) for p in c.pads),'tracks':sorted((t.GetNetname(),c.board.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),t.GetWidth()) for t in c.segments),'vias':sorted(json.dumps(via_snapshot(c.board,v),sort_keys=True) for v in c.vias),'zones':sorted((uid(z),z.GetNetname(),z.GetZoneName(),polyset(z.Outline()).wkt) for z in c.zones)}
s1,s2=signature(h),signature(c);comparison={key:s1[key]==s2[key] for key in s1}
fills_equal=all(h.copper.get(k,GeometryCollection()).symmetric_difference(c.copper.get(k,GeometryCollection())).area<1e-7 for k in set(h.copper)|set(c.copper))
rebuild={'source_h_sha256':h.sha,'consolidated_i_sha256':c.sha,'geometry_comparisons':comparison,'filled_copper_equality':fills_equal,'expected_uuid_and_title_differences':True,'status':'PASS' if all(comparison.values()) and fills_equal else 'FAIL','supersedes':'The first diagnostic accidentally compared str(LIB_ID) SWIG object addresses. This compares library nickname/item strings; the original diagnostic is preserved.'}
q=b/'R145I-independent-rebuild-v2.json';assert not q.exists();q.write_text(json.dumps(rebuild,indent=2)+'\n')
new=[t for t in c.segments if uid(t) not in a.by_id];rows=[]
for t in new:
 ly=c.board.GetLayerName(t.GetLayer());net=t.GetNetname();stroke=c.shapes[uid(t),ly]
 own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);outside=stroke.difference(own)
 hits=[]
 for f in c.footprints:
  g=fab(f);area=outside.intersection(g).area
  if area>1e-6:hits.append({'reference':f.GetReference(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),'projected_intersection_mm2':area,'same_face':c.board.GetLayerName(f.GetLayer())==ly})
 rows.append({'uuid':uid(t),'net':net,'layer':ly,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'length_mm':math.dist(xy(t.GetStart()),xy(t.GetEnd())),'nominal_body_projections':hits})
plan=json.loads((b/'R145I-plan.json').read_text());arm='/01 {slash} Core/ARMED';en='Net-(D1601-K)'
r=json.loads((b/'R145I-verify/regression.json').read_text())
report={'source_sha256':a.sha,'candidate_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':len(new),'removed_segments':len(plan['delete_copper']),'new_vias':len(plan['vias']),'removed_obsolete_vias':len(plan['remove_obsolete_vias']),'moved_vias':len(plan['move_vias'])},'net_groups':{n:[g['pads'] for g in groups(c,n)] for n in [arm,en]},'new_tracks':rows,'same_face_body_hits':sum(x['same_face'] for row in rows for x in row['nominal_body_projections']),'ARMED_new_length_mm':sum(row['length_mm'] for row in rows if row['net']==arm),'ARMED_new_back_length_mm':sum(row['length_mm'] for row in rows if row['net']==arm and row['layer']=='B.Cu'),'ARMED_back_route_segments':sum(row['net']==arm and row['layer']=='B.Cu' for row in rows),'new_ARMED_transition':[x for x in r['reference_transitions'] if x['net']==arm and x['uuid'] not in a.by_id],'moved_source_transition':[x for x in r['reference_transitions'] if x['uuid']==plan['move_vias'][0]['uuid']],'method_limits':['Nominal Fab bodies are not measured body envelopes.','Opposite/internal projections require separate local review; no blanket waiver.','No electromagnetic, thermal, current-capacity or physical qualification.']}
q=b/'R145I-local-metrics.json';assert not q.exists();q.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'rebuild':rebuild['status'],'counts':report['counts'],'same_face_body_hits':report['same_face_body_hits'],'ARMED_new_length_mm':report['ARMED_new_length_mm'],'ARMED_new_back_length_mm':report['ARMED_new_back_length_mm'],'projection_refs':sorted({x['reference'] for row in rows for x in row['nominal_body_projections']}),'new_ARMED_transition':report['new_ARMED_transition']}))
assert rebuild['status']=='PASS' and report['same_face_body_hits']==0
