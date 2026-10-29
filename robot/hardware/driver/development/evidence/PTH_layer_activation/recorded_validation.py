import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
from review_planned_delta import review
root=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');src=dev/'native/MORI_Interface_C3.kicad_pcb';dst=root/'R133PTH2/MORI_Interface_C3.kicad_pcb'
result=review(src,dst,root/'R133PTH2-declared-plan.json',root/'R133PTH2-step-regression.json',dev/'evidence/R131G/step-regression.json')
(root/'R133PTH2-planned-delta.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['status']=='PASS',result['errors']
print('positive',result['status'],len(result['checks']),flush=True)
rows=[]
base=json.loads((root/'R133PTH2-declared-plan.json').read_text());c=Copper(src)
for label in ['undeclared','smd','npth','wrong_layer']:
 p=json.loads(json.dumps(base))
 if label=='undeclared':p.pop('activate_pth_layers')
 elif label=='wrong_layer':p['activate_pth_layers'][0]['layer']='In1.Cu'
 else:
  q=next(q for q in c.pads if c.pad_name(q)==('U502.3' if label=='smd' else 'H1.'))
  p['activate_pth_layers'][0].update(pad_uuid=uid(q),pad=c.pad_name(q),position_mm=list(xy(q.GetPosition())))
 file=root/('R133-negative-'+label+'-plan.json');file.write_text(json.dumps(p,indent=2)+'\n')
 v=review(src,dst,file,root/'R133PTH2-step-regression.json',dev/'evidence/R131G/step-regression.json');assert v['status']=='FAIL',label
 rows.append({'case':label,'expected':'FAIL','actual':v['status'],'errors':v['errors']});print(label,v['status'],flush=True)
# Existing placement-only plans remain accepted, while their frozen raw audits
# and original check counts remain untouched.
v=review(root/'R129D/MORI_Interface_C3.kicad_pcb',src,dev/'evidence/R131G/edit_plan.json',dev/'evidence/R131G/step-regression.json',dev/'evidence/R129D/step-regression.json');assert v['status']=='PASS',v['errors']
rows.append({'case':'R131G_replay','expected':'PASS','actual':v['status'],'checks':len(v['checks'])});print('replay',v['status'],flush=True)
p=Planner(src,.1,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);gs=p.routing_groups('/01 {slash} Core/LINK_RX');declared=[x for g in gs for x in g.get('prospective_pth_terminals',[])]
assert any(x['pad']=='J102.22' and x['layer']=='In3.Cu' for x in declared)
assert not any(x['layer']=='In2.Cu' or x['pad']=='U502.3' for x in declared)
assert not next(q for q in p.c.pads if p.c.pad_name(q)=='J102.22').FlashLayer(p.c.ids['In3.Cu'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==p.c.sha=='6f9d92ebf5a36598421f064cf29523081d8004d28d2e60ef7a0c36ff8b9bd099'
rows.append({'case':'prospective_terminal_policy','status':'PASS','declared':declared,'source_copper_mutated':False,'In2_rule_relaxed':False})
report={'status':'PASS','positive_native_probe_status':result['status'],'positive_checks':len(result['checks']),'checks':rows,'scope':'Native behavior/model guard validation; probe unadopted and board still has 32 opens','manufacturing_release':False}
(root/'R133-model-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
