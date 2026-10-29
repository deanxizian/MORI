from pathlib import Path
import sys,json,hashlib,copy
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from review_planned_delta import review
root=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');out=root/'R134N-tool-validation';out.mkdir(exist_ok=False);src=dev/'native/MORI_Interface_C3.kicad_pcb';dst=root/'R134N/MORI_Interface_C3.kicad_pcb';source_hash=hashlib.sha256(src.read_bytes()).hexdigest();candidate_hash=hashlib.sha256(dst.read_bytes()).hexdigest();base=json.loads((root/'R134N-plan.json').read_text());rows=[]
for label in ['positive_native_R134N','undeclared_via_change','wrong_source_snapshot','undeclared_target_position','non_via_uuid','duplicate_via_change']:
 p=copy.deepcopy(base)
 if label=='undeclared_via_change':p.pop('reassign_vias')
 elif label=='wrong_source_snapshot':p['reassign_vias'][0]['source_expected']['drill_mm']=.4
 elif label=='undeclared_target_position':p['reassign_vias'][0].pop('position_mm')
 elif label=='non_via_uuid':p['reassign_vias'][0]['uuid']=p['delete_copper'][0]
 elif label=='duplicate_via_change':p['reassign_vias'].append(copy.deepcopy(p['reassign_vias'][0]))
 pp=out/(label+'-plan.json');pp.write_text(json.dumps(p,indent=2)+'\n');r=review(src,dst,pp,root/'R134N-step.json',dev/'evidence/R131G/step-regression.json');expected='PASS' if label.startswith('positive') else 'FAIL';assert r['status']==expected,(label,r['errors']);(out/(label+'-review.json')).write_text(json.dumps(r,indent=2)+'\n');rows.append({'case':label,'expected':expected,'actual':r['status'],'errors':r['errors'],'checks':len(r['checks'])});print(label,r['status'],flush=True)
for label,a,b,p,r,old in [('R131G_replay',root/'R129D/MORI_Interface_C3.kicad_pcb',src,dev/'evidence/R131G/edit_plan.json',dev/'evidence/R131G/step-regression.json',dev/'evidence/R129D/step-regression.json'),('native_PTH_probe_replay',src,root/'R133PTH2/MORI_Interface_C3.kicad_pcb',root/'R133PTH2-declared-plan.json',root/'R133PTH2-step-regression.json',dev/'evidence/R131G/step-regression.json')]:
 v=review(a,b,p,r,old);assert v['status']=='PASS',v['errors'];(out/(label+'-review.json')).write_text(json.dumps(v,indent=2)+'\n');rows.append({'case':label,'expected':'PASS','actual':v['status'],'checks':len(v['checks'])});print(label,v['status'],flush=True)
assert hashlib.sha256(src.read_bytes()).hexdigest()==source_hash and hashlib.sha256(dst.read_bytes()).hexdigest()==candidate_hash
result={'status':'PASS','source_sha256':source_hash,'candidate_sha256':candidate_hash,'source_and_candidate_unchanged':True,'cases':rows,'scope':'Native candidate positive, exact-plan rejection controls, and prior placement/PTH replay; no physical qualification or adoption.'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
