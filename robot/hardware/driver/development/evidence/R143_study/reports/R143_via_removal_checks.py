"""Safety checks for explicit obsolete signal-via removal, using actual boards.
No failure may be accepted merely because some unrelated exception occurred.
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import build
b=Path('robot/.state/c3-completion/trials');out=b/'R143-via-removal-checks';out.mkdir(exist_ok=False)
base=json.loads((b/'R143J-plan.json').read_text());cases=[]
p=copy.deepcopy(base);del p['board_sha256'];cases.append(('missing_hash','R143G',p,'exact source board hash'))
p=copy.deepcopy(base);p['remove_obsolete_vias'][0]['source_expected']['drill_mm']=.4;cases.append(('stale_snapshot','R143G',p,'snapshot mismatch'))
p=copy.deepcopy(base);p['remove_obsolete_vias']*=2;cases.append(('duplicate','R143G',p,'Duplicate or conflicting'))
p=copy.deepcopy(base);p['reassign_vias']=[{'uuid':p['remove_obsolete_vias'][0]['uuid']}];cases.append(('conflicting_mutations','R143G',p,'Duplicate or conflicting'))
for name,rev,net,match in [('active_transfer','R142','/CLR_N','still transfers between layers'),('ground_stitch','R143G','GND','snapshot mismatch')]:
 c=Copper(str(b/rev/'MORI_Interface_C3.kicad_pcb'))
 v=c.by_id['819eb181-4e28-4093-bf9b-3792433636d0'] if name=='active_transfer' else next(v for v in c.vias if v.GetNetname()=='GND')
 p={'revision':name,'board_sha256':c.sha,'remove_obsolete_vias':[{'uuid':uid(v),'source_expected':via_snapshot(c.board,v),'remaining_contact_layers':via_contact_layers(c.board,v),'reason':'negative safety test'}]}
 cases.append((name,rev,p,match))
results=[]
for name,rev,p,expected in cases:
 src=b/rev;before=hashlib.sha256((src/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()
 pp=out/(name+'.json');pp.write_text(json.dumps(p,indent=2)+'\n')
 try:build(src,out/(name+'-rejected-copy'),pp)
 except ValueError as e:
  result={'case':name,'expected_error_fragment':expected,'actual_error':str(e),'status':'PASS' if expected in str(e) else 'FAIL'}
 else:result={'case':name,'status':'FAIL','reason':'Invalid operation was accepted'}
 result['source_unchanged']=hashlib.sha256((src/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()==before
 results.append(result)
(out/'results.json').write_text(json.dumps({'scope':__doc__,'results':results,'positive_native_trial':'R143J'},indent=2)+'\n')
print(json.dumps(results,indent=2));assert all(r['status']=='PASS' and r['source_unchanged'] for r in results)
