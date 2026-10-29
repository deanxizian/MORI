"""Native positive/negative checks for explicit allocation changes; never modifies source or accepted PCB."""
import sys,json,copy,hashlib,shutil
from pathlib import Path
from shapely.geometry import Polygon
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import expanded_zone_geometry,zone_snapshot,zone_settings
from review_planned_delta import review
b=Path('robot/.state/c3-completion/trials');out=b/'R152-zone-validation';out.mkdir(exist_ok=False)
source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');candidate=b/'R152N/MORI_Interface_C3.kicad_pcb';a=Copper(source);c=Copper(candidate)
plan_path=b/'R152N-plan.json';plan=json.loads(plan_path.read_text());spec=plan['power_zone_expansions'][0];z=next(z for z in a.zones if uid(z)==spec['uuid']);q=next(z for z in c.zones if uid(z)==spec['uuid']);rows=[]
def check(name,passed,details=None):
 rows.append({'name':name,'status':'PASS' if passed else 'FAIL','details':details});assert passed,name
check('native_expansion_matches_declared_union',expanded_zone_geometry(a.board,z,spec).symmetric_difference(polyset(q.Outline())).area<1e-9)
check('native_fill_spacing_and_thermal_settings_preserved',zone_settings(a.board,z)==zone_settings(c.board,q))
for name in ['wrong_source_clearance','wrong_source_outline','wrong_area','blank_reason','nonfinite_vertex','self_crossing_patch','disjoint_patch','patch_inside_original','outside_board']:
 s=copy.deepcopy(spec)
 if name=='wrong_source_clearance':s['source_expected']['settings']['GetLocalClearance']-=1
 elif name=='wrong_source_outline':s['source_expected']['outline_wkt']='POLYGON EMPTY'
 elif name=='wrong_area':s['expected_added_area_mm2']+=.001
 elif name=='blank_reason':s['reason']=' '
 elif name=='nonfinite_vertex':s['union_patch_mm'][0][0]=float('nan')
 elif name=='self_crossing_patch':s['union_patch_mm']=[[39,25],[40,26],[39,26],[40,25]]
 elif name=='disjoint_patch':s['union_patch_mm']=[[1,1],[2,1],[2,2],[1,2]]
 elif name=='patch_inside_original':s['union_patch_mm']=[[25,25],[26,25],[26,26],[25,26]]
 elif name=='outside_board':s['union_patch_mm']=[[45,26],[71,26],[71,27],[45,27]]
 try:expanded_zone_geometry(a.board,z,s)
 except ValueError as e:check(name,True,str(e))
 else:check(name,False)
for name,z0 in [('native_keepout',next(x for x in a.zones if x.GetIsRuleArea())),('ground_reference_plane',next(x for x in a.zones if not x.GetIsRuleArea() and x.GetNetname()=='GND' and x.IsOnLayer(a.ids['In1.Cu']))),('other_copper_layer',next(x for x in a.zones if not x.GetIsRuleArea() and x.GetNetname() not in ['','GND'] and x.GetAssignedPriority()>0 and x.IsOnLayer(a.ids['In3.Cu'])))]:
 s=copy.deepcopy(spec);s['source_expected']=zone_snapshot(a.board,z0)
 try:expanded_zone_geometry(a.board,z0,s)
 except ValueError as e:check(name,True,str(e))
 else:check(name,False)
reg=b/'R152N-verify/regression.json';old=Path('robot/hardware/driver/development/evidence/R148E/regression.json')
r=review(source,candidate,plan_path,reg,old);(out/'positive-review.json').write_text(json.dumps(r,indent=2)+'\n');check('complete_native_planned_delta',r['status']=='PASS',len(r['checks']))
omitted=copy.deepcopy(plan);omitted.pop('power_zone_expansions');p=out/'omitted-plan.json';p.write_text(json.dumps(omitted,indent=2)+'\n');r=review(source,candidate,p,reg,old);(out/'omitted-review.json').write_text(json.dumps(r,indent=2)+'\n');check('undeclared_allocation_change_rejected','exact_power_zone_expansion_set' in r['errors'] and 'zone_constraints_'+spec['uuid'] in r['errors'])
fixture=out/'altered-clearance';shutil.copytree(candidate.parent,fixture);fb=pcb.LoadBoard(str(fixture/candidate.name));fz=next(x for x in fb.Zones() if uid(x)==spec['uuid']);fz.SetLocalClearance(300000);pcb.SaveBoard(str(fixture/candidate.name),fb)
r=review(source,fixture/candidate.name,plan_path,reg,old);(out/'altered-clearance-review.json').write_text(json.dumps(r,indent=2)+'\n');check('native_clearance_change_rejected','zone_constraints_'+spec['uuid'] in r['errors'],{'expected_additional_hash_failure':'regression_hashes' in r['errors'],'fixture_is_not_an_engineering_trial':True})
check('source_and_candidate_bytes_unchanged',hashlib.sha256(source.read_bytes()).hexdigest()==a.sha and hashlib.sha256(candidate.read_bytes()).hexdigest()==c.sha)
result={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,'checks':rows,'status':'PASS','manufacturing_release':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'PASS','checks':len(rows)}))
