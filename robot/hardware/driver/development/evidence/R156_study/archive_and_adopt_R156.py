"""Archive all R156 studies and receive G into the independent development entry."""
import csv,gzip,hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';candidate=b/'R156G';board='MORI_Interface_C3.kicad_pcb'
evidence=dev/'evidence/R156G';study=dev/'evidence/R156_study';backup=Path('robot/.state/c3-completion/baseline_R154B_before_R156G')
old='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede';new='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(source/board)==old and sha(candidate/board)==new
assert not evidence.exists() and not study.exists() and not backup.exists()
r=read(b/'R156G-verify/result.json');reg=read(b/'R156G-verify/regression.json');planned=read(b/'R156G-verify/planned-delta.json');inspect=read(b/'R156G-inspection.json');supply=read(b/'R156G-supply-review.json');visual=read(b/'R156G-visual-review.json');tests=read(b/'R156-guard-checker-tests-v3/result.json')
assert (r['board_sha256'],r['unconnected_items'],r['violations'],r['schematic_parity'],r['erc_violations'])==(new,23,0,0,0)
assert planned['status']=='PASS' and len(planned['checks'])==2520 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155]
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
assert sum(x['status']=='FAIL' for x in reg['reference_transitions'])==6
assert inspect['same_face_nominal_body_hit_count']==0 and inspect['counts']=={'segments':1303,'vias':325,'footprints':215,'new_segments':11}
assert len(inspect['wheel_groups'])==2 and ['R1002.1'] in inspect['wheel_groups']
assert supply['source_local_pair_widths_preserved'] and all(x['changed_area_mm2']<1e-7 for x in supply['internal_supply_and_reference_fills'])
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==9 and tests['status']=='PASS' and len(tests['cases'])==3
source_hashes={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
members=[p for p in source_hashes if p!=board and not p.endswith(('.kicad_prl','.lck'))];assert len(members)==77
for p in members:assert sha(candidate/p)==source_hashes[p],p
old_status=read(dev/'STATUS.json');assert old_status['board_sha256']==old
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();now=datetime.now(timezone.utc).isoformat()
before=b/'R156-review-planned-delta-before.py';assert not before.exists();before.write_bytes(subprocess.check_output(['git','show','HEAD:robot/hardware/driver/development/scripts/review_planned_delta.py']))
evidence.mkdir();study.mkdir()
for p in (b/'R156G-verify').iterdir():shutil.copy2(p,evidence/p.name)
for src,dest in [('R156G-plan.json','plan.json'),('R156G-inspection.json','inspection.json'),('R156G-supply-review.json','supply-review.json'),('R156G-visual-review.json','visual_review.json'),('R156G-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dest)
shutil.copy2(b/'R156-guard-checker-tests-v3/result.json',evidence/'guard-checker-tests.json');shutil.copytree(b/'R156G-views',evidence/'images')
(evidence/'source_R154B.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 writer=csv.writer(f);writer.writerow(['item','description','endpoint_descriptions'])
 for i,x in enumerate(read(evidence/'drc.json')['unconnected_items'],1):writer.writerow([i,x['description'],' | '.join(y['description'] for y in x['items'])])
payloads=[];trials=[];skipped=[]
def preserve(src,rel):
 data=src.read_bytes();compress=src.suffix=='.kicad_pcb' or len(data)>524288;dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R156*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch(r'R156[A-Z]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for name in ['edit_plan.json','edit_manifest.json']:
   if (p/name).is_file():preserve(p/name,Path('raw')/p.name/name)
  changed=[]
  for name in members:
   q=p/name;assert q.is_file()
   if sha(q)!=source_hashes[name]:changed.append(name);preserve(q,Path('raw')/p.name/name)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':p.name=='R156G',**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'old_power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'lost_connection_nets':len(a['lost_pad_connections']),'retained_reference_loss_count':len(a['retained_trace_reference_loss']),'new_reference_gap_count':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),'changed_other_native_members':changed,'erc':'0 in final G; otherwise not rerun','physical':'NOT_TESTED'})
 elif p.name!='R156G-views':
  copies=[q.parent for q in p.rglob(board)]
  for q in sorted(p.rglob('*')):
   if not q.is_file():continue
   matching=next((root for root in copies if root in q.parents),None)
   rel=q.relative_to(matching).as_posix() if matching else None
   if rel in source_hashes and rel!=board and sha(q)==source_hashes[rel]:
    skipped.append({'local_path':q.relative_to(b).as_posix(),'identical_source_member':rel,'sha256':sha(q)});continue
   preserve(q,Path('raw')/q.relative_to(b))
assert len(trials)==7
preserve(Path(__file__),Path('archive_and_adopt_R156.py'))
for name in ['build_trial.py','review_planned_delta.py','audit_candidate.py','copper_geometry.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
preserve(b/'R152_render_highlight.py',Path('raw/helpers/R152_render_highlight.py'))
write(study/'summary.json',{'recorded_at_utc':now,'source_commit':commit,'source_revision':'R154B','source_sha256':old,'adopted_revision':'R156G','adopted_sha256':new,'candidates':trials,'remaining_unconnected_items':23,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.575,'not_engineering_progress':True,'OV_study':'A/B retain the old MOTION_3V3 split; C crosses the existing UPS 5V tree. Joint supply searches produce excessive 35-79 mm detours and are not adopted.','wheel_study':'D in-place rotation alone retains 24 opens. E connects R1702 but conflicts with a fixed ground hole and has reference gaps. F fixes those but has a courtyard overlap. G passes the recorded reception and preserves R1002.1 as the sole remaining WHEEL_VM island.','checker_tests':'Initial v1 harness used the wrong audit API argument and did not finish; v2 had extra project normalization differences. V3 isolates one guard per negative case and rejects exactly the expected geometry/change-set checks. The original pre-fix false rejection and all cases remain preserved.','manufacturing_release':False,'goal_complete':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'unchanged_native_members_omitted_from_mutant_test_copies':skipped,'accepted_images':visual['images_actually_viewed'],'local_only':'All complete source/native candidate folders and experiment files remain on Sol; nothing deleted.'})
for row in payloads:
 q=study/row['path'];assert sha(q)==row['sha256'];data=gzip.decompress(q.read_bytes()) if row['gzip'] else q.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'native_trial_count':7,'all_stored_and_original_byte_hashes_match':True,'source_local_trials_untouched':True})
assert {p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}==source_hashes
shutil.copytree(source,backup,copy_function=shutil.copy2);assert {p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}==source_hashes
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for rel,digest in source_hashes.items():
 if rel!=board:assert sha(source/rel)==digest
write(evidence/'adoption.json',{'adopted_at_utc':now,'source_commit':commit,'source_sha256':old,'adopted_board_sha256':new,'source_full_local_backup':str(backup.absolute()),'other_native_members_unchanged':77,'member_checks':[{'member':p,'sha256':sha(source/p)} for p in members],'development_only':True,'published_revision':'C3 R108P','adopted_in_main_model':False,'adopted_in_software':False,'engineering_status':'FAIL','physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
status={**old_status,**r};status.update({'revision':'C3 R156G','previous_candidate':'C3 R154B','previous_candidate_sha256':old,'strict_regression_explanation':'Raw audit retains FAIL for ten replaced/removed front traces and two planned resistor transforms. All 2520 exact planned checks and electrical/reference regressions pass. The R1702 guard is geometrically invariant under its half-turn; negative mutation tests still reject changed or unrelated guards.','step_regression_status':'FAIL','planned_delta_review_status':'PASS','planned_delta_check_count':2520,'electrical_regression_status':'PASS','local_visual_review':'PASS','local_visual_review_explanation':'Six candidate layers and three source views actually inspected. No new mounted-face nominal-body hits; opposite C505/U1701 projections individually reviewed with thermal/coupling limits.','new_same_face_nominal_body_projection_groups':0,'segment_count':1303,'via_count':325,'footprint_count':215,'remaining_connectivity_fraction':.575,'remaining_WHEEL_VM_groups':2,'R1702_wheel_tap_connected':True,'R1002_wheel_tap_connected':False,'goal_complete':False})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':'R156G','unconnected':23,'remaining_fraction':.575,'exact_checks':2520,'archive_payloads':len(payloads),'other_native_members_unchanged':77,'goal_complete':False}))
