"""Native integration refusals and unchanged accepted-board review for R171 tools.

The positive candidate is not accepted. Source boards and frozen evidence remain
unchanged. Deliberately invalid builds may leave copied source projects only.
"""
import copy,hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import Copper,uid,via_snapshot
from review_planned_delta import review
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
out=b/'R171-tool-validation';out.mkdir(exist_ok=False)
source=dev/'native';pcbname='MORI_Interface_C3.kicad_pcb'
c=Copper(str(source/pcbname));source_hash=c.sha
plan=json.loads((b/'R171D-plan.json').read_text());py=str(Path(sys.executable).absolute())
ground=next(v for v in c.vias if v.GetNetname()=='GND')
cases=[]
p=copy.deepcopy(plan);p['remove_obsolete_vias'][0].pop('isolated_zone_layers');cases.append(('legacy_dual_layer_refusal',p,'Via still transfers between layers'))
p=copy.deepcopy(plan);p['remove_obsolete_vias'][0]['isolated_zone_layers']=['In3.Cu'];cases.append(('real_distribution_refusal',p,'Via still transfers between layers'))
p=copy.deepcopy(plan);p['remove_obsolete_vias'][0].update(uuid=uid(ground),source_expected=via_snapshot(c.board,ground));cases.append(('ground_via_refusal',p,'Obsolete non-ground via snapshot mismatch'))
p=copy.deepcopy(plan);p['remove_obsolete_vias'][0]['source_expected']['position_mm'][0]+=.01;cases.append(('wrong_snapshot_refusal',p,'Obsolete non-ground via snapshot mismatch'))
records=[]
for name,p,error in cases:
 p['revision']='R171-validation-'+name;pp=out/(name+'-plan.json');pp.write_text(json.dumps(p,indent=2)+'\n')
 dest=out/name;start=time.monotonic()
 r=subprocess.run([py,str(dev/'scripts/build_trial.py'),str(source),str(dest),str(pp)],capture_output=True,text=True)
 (out/(name+'.log')).write_text(r.stdout+'\n'+r.stderr)
 saved_hash=hashlib.sha256((dest/pcbname).read_bytes()).hexdigest()
 assert r.returncode!=0 and error in r.stderr,(name,r.returncode,r.stderr)
 assert saved_hash==source_hash and not (dest/'trial_changes.json').exists()
 records.append(dict(name=name,returncode=r.returncode,expected_error=error,source_copy_saved_hash=saved_hash,elapsed_seconds=time.monotonic()-start,status='PASS'))
 print(name,'PASS',flush=True)
old_source=Path('robot/.state/c3-completion/baseline_R165M_before_R168G')/pcbname
accepted=dev/'evidence/R168G'
r=review(str(old_source),str(source/pcbname),str(accepted/'plan.json'),str(accepted/'regression.json'),str(dev/'evidence/R165M/regression.json'))
assert r['status']=='PASS' and len(r['checks'])==2566,r['errors']
assert all(x['status']=='PASS' and not x['removed_anchor_pairs'] for x in r['power_width_review'])
(out/'accepted_R168G-review.json').write_text(json.dumps(r,indent=2)+'\n')
records.append(dict(name='unchanged_accepted_R168G',status='PASS',checks=len(r['checks']),power_width_rows=len(r['power_width_review'])))
assert hashlib.sha256((source/pcbname).read_bytes()).hexdigest()==source_hash
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=source_hash,checks=records,status='PASS'),indent=2)+'\n')
print('PASS',len(records),flush=True)
