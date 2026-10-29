"""Validate the dedicated-return screen against real boards and a cut-path control."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess,sys
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from audit_ina300_return import audit
from copper_geometry import pcb,uid
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';name='MORI_Interface_C3.kicad_pcb'
out=b/'R157-return-checker-tests';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
assert hashes[name]=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
rows=[]
for rev,path in [('R156G',source/name),('R157B',b/'R157B'/name)]:
 r=audit(path);(out/(rev+'.json')).write_text(json.dumps(r,indent=2)+'\n')
 assert r['direct_return_screen']=='FAIL' and r['rlimit_return']['full_native_copper_connected']
 assert not r['rlimit_return']['explicit_track_pad_via_path_without_fills']
 assert r['bypass_return_positive_control']['explicit_track_pad_via_path_without_fills']
 rows.append({'case':rev+' plane-only RLIMIT and real bypass control','status':'PASS','board_sha256':r['board_sha256']})
board=pcb.LoadBoard(str(source/name));cut='4e3cff17-d7fe-4cb4-87f2-0dfef758262e';tracks=[t for t in board.GetTracks() if uid(t)==cut];assert len(tracks)==1
assert tracks[0].GetNetname()=='GND';board.Remove(tracks[0]);control=out/'bypass_return_cut.kicad_pcb';pcb.SaveBoard(str(control),board)
r=audit(control);(out/'cut-control.json').write_text(json.dumps(r,indent=2)+'\n');assert not r['bypass_return_positive_control']['explicit_track_pad_via_path_without_fills']
rows.append({'case':'Remove actual U1701.8 ground trace only; reject bypass direct-path control','status':'PASS','removed_track_uuid':cut,'board_sha256':r['board_sha256'],'native_DRC_and_refill':'NOT_TESTED; algorithm-control copy only; never a design candidate'})
assert hashes=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
result={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS','cases':rows,'all_source_native_members_unchanged':len(hashes),'source_native_hashes':hashes,'board_design_adopted':False,'scope':__doc__}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
project=b/'R157B/MORI_Interface_C3.kicad_pro';saved=b/'R157B-project-before-verify.kicad_pro';assert not saved.exists();saved.write_bytes(project.read_bytes())
command=[str(Path(sys.executable).absolute()),str((dev/'scripts/verify_trial.py').absolute()),str(source.absolute()),str((b/'R157B').absolute()),str((b/'R157B-verify').absolute())]
r=subprocess.run(command,text=True,capture_output=True)
(b/'R157-return-integration-command.json').write_text(json.dumps({'argv':command,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2)+'\n')
assert r.returncode==0,(r.stdout,r.stderr)
v=json.loads((b/'R157B-verify/result.json').read_text());assert v['unconnected_items']==22 and v['ina300_rlimit_return_screen']=='FAIL' and v['engineering_status']=='FAIL'
assert hashes=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
print(json.dumps({'checker_tests':'PASS','cases':len(rows),'integration':'PASS','candidate_unconnected':v['unconnected_items'],'candidate_ina300_return':v['ina300_rlimit_return_screen'],'candidate_engineering':v['engineering_status'],'adopted':False,'native_source_members_unchanged':len(hashes)}))
