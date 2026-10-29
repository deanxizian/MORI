"""End-to-end guard regression: valid symmetric rotation and two rejected mutations."""
import contextlib,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import pcb,uid
from audit_candidate import audit
from review_planned_delta import review
b=Path('robot/.state/c3-completion/trials');out=b/'R156-guard-checker-tests-v2';out.mkdir(exist_ok=False)
source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');candidate=b/'R156G';name=source.name
p=b/'R156G-plan.json';sr=Path('robot/hardware/driver/development/evidence/R154B/regression.json')
source_hash=hashlib.sha256(source.read_bytes()).hexdigest();candidate_hash=hashlib.sha256((candidate/name).read_bytes()).hexdigest();rows=[]
valid=json.loads((b/'R156G-verify/planned-delta.json').read_text());assert valid['status']=='PASS' and valid['transformed_invariant_guard_ids']==['d8903c86-31f1-4900-ae0e-deac387ca989']
rows.append({'case':'unmodified_R156G_symmetric_half_turn','status':'PASS','expected_result':'PASS','observed_result':valid['status'],'checks':len(valid['checks'])})
for tag,ref in [('unexpected_symmetric_guard_shift','R1702'),('unplanned_unrelated_guard_shift','R1701')]:
 folder=out/tag;shutil.copytree(candidate,folder)
 board=pcb.LoadBoard(str(folder/name));z=next(z for z in board.Zones() if z.GetZoneName().startswith('BODY_'+ref+'_'));guard_id=uid(z);z.Move(pcb.VECTOR2I(10000,0));pcb.SaveBoard(str(folder/name),board)
 reg=audit(source,folder/name,Path('robot/hardware/driver/evidence/R108P'));(folder/'regression.json').write_text(json.dumps(reg,indent=2)+'\n')
 result=review(source,folder/name,p,folder/'regression.json',sr);(folder/'review.json').write_text(json.dumps(result,indent=2)+'\n')
 assert result['status']=='FAIL' and not result['checks']['exact_moved_guard_set']
 if ref=='R1702':assert not result['checks']['moved_guard_'+guard_id]
 else:assert not result['checks']['zone_constraints_'+guard_id]
 rows.append({'case':tag,'status':'PASS','expected_result':'FAIL','observed_result':result['status'],'guard_uuid':guard_id,'errors':result['errors']})
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash and hashlib.sha256((candidate/name).read_bytes()).hexdigest()==candidate_hash
result={'scope':__doc__,'status':'PASS','source_sha256':source_hash,'candidate_sha256':candidate_hash,'cases':rows,'original_boards_unchanged':True,'limits':'Tests validate planned guard-delta checking, not electrical or physical qualification.'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
