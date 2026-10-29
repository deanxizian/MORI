"""Freeze R168 trials and receive G into the independent development entry only."""
import collections,csv,gzip,hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';candidate=b/'R168G';board='MORI_Interface_C3.kicad_pcb'
study=dev/'evidence/R168_study';evidence=dev/'evidence/R168G';backup=Path('robot/.state/c3-completion/baseline_R165M_before_R168G')
old='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70';new='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n')
assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source/board)==old and sha(candidate/board)==new
r=read(b/'R168G-final-checks/result.json');reg=read(b/'R168G-final-checks/regression.json');planned=read(b/'R168G-planned-delta.json');ins=read(b/'R168G-inspection.json');visual=read(b/'R168G-visual-review.json');metrics=read(b/'R168G-metrics.json')
assert tuple(r[k] for k in ['board_sha256','unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps'])==(new,20,0,0,0,0)
assert r['ina300_rlimit_return_screen']=='PASS' and r['historical_transition_flags']==6
assert planned['status']=='PASS' and len(planned['checks'])==2566 and not planned['errors']
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(q['status']=='PASS' for q in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(q['status']=='PASS' for q in reg['critical_placement'])
assert [len(g) for g in reg['GND_groups']]==[155] and all(q['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for q in reg['new_copper_review'])
assert ins['source_ground_vias_preserved']==114 and not ins['same_face_nominal_body_hits']
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==12 and len(visual['opposite_or_internal_projections'])==10
assert metrics['counts']==dict(segments=1398,vias=325,footprints=215,new_segments=45) and metrics['source_In2_0_48_spine_uncovered_mm2']<1e-6
assert [(x['net'],x['before'],x['after']) for x in metrics['group_count_changes']]==[('/FAULT_N',4,3)]
members={q['member']:q['sha256'] for q in read(dev/'evidence/R165M/adoption.json')['member_checks']};assert len(members)==77
for n,d in members.items():assert sha(source/n)==sha(candidate/n)==d,n
source_all={q.relative_to(source).as_posix():sha(q) for q in source.rglob('*') if q.is_file()}
status=read(dev/'STATUS.json');assert status['board_sha256']==old and status['unconnected_items']==21
now=datetime.now(timezone.utc).isoformat();commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
study.mkdir();evidence.mkdir()
for q in (b/'R168G-final-checks').iterdir():shutil.copy2(q,evidence/q.name)
for src,dst in [('R168G-plan.json','plan.json'),('R168G-planned-delta.json','planned-delta.json'),('R168G-inspection.json','inspection.json'),('R168G-visual-review.json','visual_review.json'),('R168G-metrics.json','metrics.json'),('R168G-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dst)
shutil.copytree(b/'R168G-views',evidence/'images')
(evidence/'source_R165M.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
assert gzip.decompress((evidence/'source_R165M.kicad_pcb.gz').read_bytes())==(source/board).read_bytes()
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for n,q in enumerate(read(evidence/'drc.json')['unconnected_items'],1):w.writerow([n,q['description'],' | '.join(z['description'] for z in q['items'])])
payloads=[];omitted=[];trials=[]
def preserve(q,rel):
 data=q.read_bytes();compressed=q.suffix in ['.kicad_pcb','.kicad_prl'] or len(data)>524288;dest=study/rel
 if compressed:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R168'+s) for s in 'ABCDEFG']
for top in sorted(b.glob('R168*')):
 if top.name=='R168G-views':continue
 for q in ([top] if top.is_file() else sorted(z for z in top.rglob('*') if z.is_file())):
  owner=next((root for root in roots if q.is_relative_to(root)),None);rel=q.relative_to(owner).as_posix() if owner else None
  if rel in members and sha(q)==members[rel]:omitted.append(dict(local_path=q.relative_to(b).as_posix(),member=rel,sha256=sha(q)));continue
  preserve(q,Path('raw')/q.relative_to(b))
for name in ['build_trial.py','footprint_side_change.py','zone_expansion.py','copper_geometry.py','audit_candidate.py','verify_trial.py','audit_ina300_return.py','review_planned_delta.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R161_power_aware_search.py','R166-power-spine.json','R167B-plan.json','R167_fault_without_in2.py','R167_fault_reserved_search.py']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R168.json'))
for s in 'ABCDEFG':
 rev='R168'+s;dr=b/(rev+'-drc.json');entry=dict(revision=rev,board_sha256=sha(b/rev/board),native_completed=dr.exists(),adopted=s=='G')
 if dr.exists():
  d=read(dr);a=read(b/(rev+'-audit.json'));ix=read(b/(rev+'-inspection.json'))
  entry.update({**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'DRC_types':dict(collections.Counter(q['type'] for q in d['violations'])),'power_width_failures':sum(q['status']!='PASS' for q in a['power_width']),'old_connection_losses':a['lost_pad_connections'],'ground_group_sizes':[len(q) for q in a['GND_groups']],'old_reference_losses':a['retained_trace_reference_loss'],'new_reference_gaps':[q for q in a['new_copper_review'] if q['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6],'source_ground_vias_preserved':ix['source_ground_vias_preserved'],'same_face_nominal_body_hits':ix['same_face_nominal_body_hits'],'erc':'0 enabled in G full verification' if s=='G' else 'NOT_RERUN'})
 else:entry['failure_phase']='Saved A preparation changed the orphan moved ACT via to GND; strict saved-board readback rejected it. No native DRC/audit completed; preserved wrong-net file is not a starting source.'
 trials.append(entry)
summary=dict(recorded_at_utc=now,source_commit=commit,remote_main='aa94dddebcc8ca40cc4b63616147f81448ef087f',source_revision='R165M',source_sha256=old,adopted_revision='R168G',adopted_board_sha256=new,candidates=trials,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,progress=[
 'B restores all old pads, source widths and ground pads by explicit complete leads, relocating only non-ground transfers and retaining all 114 source GND vias. C fixes the local body and reference failures but the FAULT trunk remains open.',
 'C fixed-placement F/B/In3 searches fail; the In2 weighted path cuts the old 3V3 corridor, and reserving that corridor yields a 90.76 mm detour. Neither is adopted.',
 'D separates right ACT/power vias but creates old supply-reference loss and an INA reference/body issue. E restores the original right 3V3 via but collides with the new left FAULT port. F jointly adjusts U1702 and three signal ports; one tiny INA reference gap and one body hit remain.',
 'G uses the screened outward INA input route and an exact-centre 21.090180 mm In2 FAULT trunk. The proposal before endpoint correction was 20.582338 mm. No extra trunk via is added; the one new port via is included in the total +1 via delta.',
 'Q1701 FAULT joins the main group. U1701.5 and D302.1 remain separate FAULT groups. Native 20 opens/0 other/0 parity/0 enabled ERC and 2566 exact planned checks pass; all source power/ground/reference tests and the explicit 0.48 mm In2 spine remain intact.'
 ],full_verification=r,source_ground_vias_preserved=114,unchanged_non_PCB_members=77,images='../R168G/images: twelve actually reviewed native local geometry views',projection_review='../R168G/visual_review.json: 33 overlaps in 10 component groups plus four In2/In3 crossings; complete coupling/thermal qualification remains open',whole_board_visual='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,accepted_images='../R168G/images',source_board='../R168G/source_R165M.kicad_pcb.gz',original_local_sources_preserved=True))
for q in payloads:
 dest=study/q['path'];assert sha(dest)==q['sha256'];data=gzip.decompress(dest.read_bytes()) if q['gzip'] else dest.read_bytes();assert len(data)==q['source_bytes'] and hashlib.sha256(data).hexdigest()==q['source_sha256']
for q in visual['images_actually_viewed']:assert sha(evidence/q['path'])==q['sha256']
assert source_all=={q.relative_to(source).as_posix():sha(q) for q in source.rglob('*') if q.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=6,saved_readback_failures=1,all_original_byte_hashes_match=True,source_local_trials_untouched=True,accepted_images_hash_verified=12))
shutil.copytree(source,backup,copy_function=shutil.copy2);assert source_all=={q.relative_to(backup).as_posix():sha(q) for q in backup.rglob('*') if q.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for name,digest in source_all.items():
 if name!=board:assert sha(source/name)==digest,name
write(evidence/'adoption.json',dict(adopted_at_utc=now,source_commit=commit,source_sha256=old,adopted_board_sha256=new,source_full_local_backup=str(backup.absolute()),other_native_members_unchanged=77,member_checks=[dict(member=n,sha256=sha(source/n)) for n in members],development_only=True,published_revision='C3 R108P',adopted_in_main_model=False,adopted_in_software=False,engineering_status='FAIL',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
status.update(r);status.update(revision='C3 R168G',previous_candidate='C3 R165M',previous_candidate_sha256=old,strict_regression_explanation='Raw geometry FAIL is retained for 3 planned footprint transforms, 13 replaced tracks and 3 relocated non-ground vias. All 2566 explicit delta and electrical/reference checks pass without changing rules or thresholds.',planned_delta_review_status='PASS',planned_delta_check_count=2566,electrical_regression_status='PASS',local_visual_review='PASS',local_visual_review_explanation='Twelve actual native local geometry views; no new mounted-face body hits. Ten opposite/internal component groups and four interlayer crossings reviewed with explicit unqualified coupling/thermal boundaries.',new_same_face_nominal_body_projection_groups=0,segment_count=1398,via_count=325,footprint_count=215,remaining_connectivity_fraction=.5,remaining_FAULT_N_groups=3,ina300_rlimit_return_evidence='evidence/R168G/ina300-return.json',last_followup_study='R168',latest_study_evidence='evidence/R168_study/summary.json',latest_study_adopted=True,latest_study_note='G joins Q1701 FAULT to the main group while preserving original power, ground and reference checks. 20 opens / 50 percent by original connection count; not overall engineering or manufacturing readiness.',goal_complete=False)
status['open_manufacturer_layout_items'].append(dict(id='TPS3700_U1702_BYPASS_INPUT_AND_FAULT_COUPLING',status='NOT_TESTED',reason='Complete bypass loop, analog input noise, protection dynamics and new FAULT interlayer coupling require full-board/manufacturer/physical qualification; local geometry and reference checks alone do not close these.',evidence='evidence/R168G/visual_review.json'))
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(adopted='R168G',remaining_unconnected_items=20,remaining_connectivity_fraction=.5,planned_checks=2566,archive_payloads=len(payloads),unchanged_non_PCB_members=77,goal_complete=False)))
