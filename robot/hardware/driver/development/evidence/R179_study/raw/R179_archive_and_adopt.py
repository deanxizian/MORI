"""Freeze the R179 comparisons and receive only the checked CLR preparation I.

This does not complete another connection, adopt U301 relocation, publish the
board, or qualify manufacture/physical performance. All local originals remain.
"""
import collections,csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');board='MORI_Interface_C3.kicad_pcb'
source=dev/'native';candidate=b/'R179I';study=dev/'evidence/R179_study';evidence=dev/'evidence/R179I';backup=Path('robot/.state/c3-completion/baseline_R178L_before_R179I')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
old='aceda44f2f65d235200d4542525ebe3e6d7a3779572369c181851b2af6760f32';new='0314affe1179898dbb679292c8c4ecb8f59838d5753302436854bf4ea5e76af9'
assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source/board)==old and sha(candidate/board)==new
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert commit.startswith('03f2eb5')
r=read(b/'R179I-final-checks/result.json');reg=read(b/'R179I-final-checks/regression.json');plan=read(b/'R179I-planned-delta.json');inspection=read(b/'R179I-inspection.json');metrics=read(b/'R179I-metrics-v2.json');coupling=read(b/'R179I-coupling-review.json')
assert tuple(r[k] for k in ['board_sha256','unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps','historical_transition_flags'])==(new,19,0,0,0,0,6)
assert r['ina300_rlimit_return_screen']=='PASS' and plan['status']=='PASS' and not plan['errors'] and len(plan['checks'])==2507
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(q['status']=='PASS' for q in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(q['status']=='PASS' for q in reg['critical_placement'])
assert [len(q) for q in reg['GND_groups']]==[155] and not inspection['same_face_nominal_body_hits']
assert coupling['original_vias_preserved']==325 and coupling['source_ground_vias_preserved']==114
assert coupling['track_counts']==dict(before=1400,after=1409) and coupling['new_vias']==0
assert len(coupling['sampling_crossings'])==1 and abs(coupling['sampling_crossings'][0]['angle_deg']-90)<1e-6
assert all(q['unshielded_body_overlap_mm2']<1e-8 for q in coupling['body_projection_reviews'])
assert all(q['unshielded_by_intervening_plane_mm2']<1e-8 for q in metrics['projection_rows'] if q['layer'] in ['F.Cu','B.Cu'])
assert metrics['old_connection_changes']==[]
members={q['member']:q['sha256'] for q in read(dev/'evidence/R178L/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==sha(candidate/n)==h for n,h in members.items())
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
status=read(dev/'STATUS.json');assert status['revision']=='C3 R178L' and status['unconnected_items']==19
now=datetime.now(timezone.utc).isoformat()
for ly in ['F.Cu','In2.Cu']:
 for ext in ['svg','png']:
  shutil.copy2(b/'R179D-views'/('source-'+ly+'.'+ext),b/'R179I-views'/('source-'+ly+'.'+ext))
images=[dict(path='images/'+p.name,sha256=sha(p)) for p in sorted((b/'R179I-views').glob('*.png'))]
assert len(images)==8
visual=dict(source_sha256=old,board_sha256=new,local_status='PASS',scope='Six actual native layer views plus two immutable source comparisons were viewed. Local prototype routing preparation only.',images_actually_viewed=images,decision='Accept the CLR layer reassignment to clear the front ARMED corridor. No U301 movement or its trial routes are accepted.',routing_reason='The extra bends preserve the power island and fixed ground via while making the adjacent sampling crossing perpendicular. The initial 0.10 mm vertical termination lies within the old via land.',body_review=coupling['body_projection_reviews'],coupling_review='coupling_review.json',whole_board_visual='NOT_TESTED',whole_board_route_style='NOT_TESTED',full_EMC_timing_thermal='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False)
write(b/'R179I-visual-review.json',visual)
write(b/'R179-diagnostic-corrections.json',dict(read_only_metric_v1='The inline diagnostic repeatedly enumerated pad groups and was interrupted with SIGINT (exit 130); no PCB save occurred. The preserved metrics scripts cache groups once.',network_name='An initial image-only ACT_GATE inference was wrong. Native geometry identifies Net-(U1001-S2_{slash}_WHEEL_sense); user-facing correction and original F description are preserved.',F_plan_description_only_corrected=True,adopted_U301_relocation=False))
study.mkdir();evidence.mkdir()
for p in (b/'R179I-final-checks').iterdir():shutil.copy2(p,evidence/p.name)
for src,dst in [('R179I-plan.json','plan.json'),('R179I-planned-delta.json','planned-delta.json'),('R179I-inspection.json','inspection.json'),('R179I-metrics-v2.json','metrics.json'),('R179I-coupling-review.json','coupling_review.json'),('R179I-visual-review.json','visual_review.json'),('R179I-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dst)
shutil.copytree(b/'R179I-views',evidence/'images')
(evidence/'source_R178L.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for i,q in enumerate(read(evidence/'drc.json')['unconnected_items'],1):w.writerow([i,q['description'],' | '.join(x['description'] for x in q['items'])])
rows=[]
for letter in 'ABCDEFGHI':
 rev='R179'+letter;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'));assert sha(b/rev/board)==a['board_sha256'] and read(b/(rev+'-plan.json'))['board_sha256']==old
 row=dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),GND_group_sizes=[len(x) for x in a['GND_groups']],power_failures=[dict(net=x['net'],width_mm=x['width_mm']) for x in a['power_width'] if x['status']=='FAIL'],old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),adopted=letter=='I')
 check=b/(rev+'-final-checks/result.json');row['enabled_ERC']=read(check)['erc_violations'] if check.exists() else 'NOT_RERUN';rows.append(row)
payloads=[];omitted=[]
def preserve(p,rel):
 data=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf'])
 dest=study/rel
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/q['revision'] for q in rows]
for top in sorted(b.glob('R179*')):
 if top.name=='R179I-views':continue
 for p in ([top] if top.is_file() else sorted(x for x in top.rglob('*') if x.is_file())):
  owner=next((root for root in roots if p.is_relative_to(root)),None);rel=p.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
  preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R179.json'))
write(study/'summary.json',dict(recorded_at_utc=now,source_commit=commit,remote_main='aa94dddebcc8ca40cc4b63616147f81448ef087f',source_revision='R178L',source_sha256=old,adopted_revision='R179I',adopted_board_sha256=new,candidates=rows,remaining_unconnected_items=19,newly_completed_connections=0,baseline_unconnected_items=40,remaining_connectivity_fraction=.475,connectivity_fraction_is_not_engineering_progress=True,full_verification=r,planned_checks=2507,source_ground_vias_preserved=114,all_original_vias_preserved=325,unchanged_non_PCB_members=77,whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,accepted_images='../R179I/images',source_board='../R179I/source_R178L.kicad_pcb.gz',original_local_sources_preserved=True))
for q in payloads:
 p=study/q['path'];assert sha(p)==q['sha256'];data=gzip.decompress(p.read_bytes()) if q['gzip'] else p.read_bytes();assert len(data)==q['source_bytes'] and hashlib.sha256(data).hexdigest()==q['source_sha256']
for q in images:assert sha(evidence/q['path'])==q['sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=9,all_original_byte_hashes_match=True,source_local_trials_untouched=True,accepted_images_hash_verified=8))
shutil.copytree(source,backup,copy_function=shutil.copy2);assert source_all=={p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for n,h in source_all.items():
 if n!=board:assert sha(source/n)==h
write(evidence/'adoption.json',dict(adopted_at_utc=now,source_commit=commit,source_sha256=old,adopted_board_sha256=new,source_full_local_backup=str(backup.absolute()),other_native_members_unchanged=77,member_checks=[dict(member=n,sha256=sha(source/n)) for n in members],development_only=True,published_revision='C3 R108P',adopted_in_main_model=False,adopted_in_software=False,engineering_status='FAIL',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
status.update(r);status.update(revision='C3 R179I',previous_candidate='C3 R178L',previous_candidate_sha256=old,strict_regression_explanation='Raw geometry FAIL records one replaced F CLR segment and ten planned In2 segments. All 2507 exact-delta and electrical/reference checks pass; no rule, footprint or via change.',planned_delta_review_status='PASS',planned_delta_check_count=2507,electrical_regression_status='PASS',local_visual_review='PASS',local_visual_review_explanation='Eight native local/source views reviewed. The cleared front CLR bridge is replaced by a ground-referenced In2 route, with one perpendicular WHEEL_sense crossing and fully shielded foreign outer-copper/body projections. Full field coupling, EMC, timing and thermal qualification remain open.',new_same_face_nominal_body_projection_groups=0,segment_count=1409,via_count=325,footprint_count=215,remaining_connectivity_fraction=.475,ina300_rlimit_return_evidence='evidence/R179I/ina300-return.json',last_followup_study='R179',latest_study_evidence='evidence/R179_study/summary.json',latest_study_adopted=True,latest_study_note='I clears the front routing barrier without moving components or vias. No additional open is closed: 19 opens / 47.5 percent by original count remain. U301 comparison relocations are not adopted.',goal_complete=False)
status['open_manufacturer_layout_items'].append(dict(id='CLR_IN2_ADJACENT_SAMPLING_CROSSING',status='NOT_TESTED',reason='Prototype geometry uses one perpendicular crossing of retained In3 WHEEL_sense and shields outer copper/body projections. Full noise/EMC/timing/thermal qualification is still open.',evidence='evidence/R179I/coupling_review.json'))
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(adopted='R179I',board_sha256=new,remaining_unconnected_items=19,newly_completed_connections=0,planned_checks=2507,archive_payloads=len(payloads),unchanged_non_PCB_members=77,goal_complete=False)),flush=True)
