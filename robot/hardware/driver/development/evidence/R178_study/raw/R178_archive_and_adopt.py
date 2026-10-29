"""Freeze R178 evidence and receive L into the independent development entry.

The published R108P and mechanical/software adoption states remain unchanged.
Only the candidate PCB and development status are updated after all gates pass.
"""
import collections,csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';candidate=b/'R178L';board='MORI_Interface_C3.kicad_pcb'
study=dev/'evidence/R178_study';evidence=dev/'evidence/R178L'
backup=Path('robot/.state/c3-completion/baseline_R168G_before_R178L')
old='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source/board)==old
new=sha(candidate/board);r=read(b/'R178L-final-checks/result.json')
reg=read(b/'R178L-final-checks/regression.json');planned=read(b/'R178L-planned-delta.json')
ins=read(b/'R178L-inspection.json');visual=read(b/'R178L-visual-review.json')
metrics=read(b/'R178L-metrics.json');local=read(b/'R178L-local-reference-review.json')
assert tuple(r[k] for k in ['board_sha256','unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps'])==(new,19,0,0,0,0)
assert r['ina300_rlimit_return_screen']=='PASS' and r['historical_transition_flags']==6
assert planned['status']=='PASS' and not planned['errors'] and len(planned['checks'])==2515
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(x) for x in reg['GND_groups']]==[155]
assert ins['source_ground_vias_preserved']==114 and not ins['same_face_nominal_body_hits']
assert local['opposite_DVDT_copper_overlap_mm2']==0 and local['overlap_unshielded_by_both_mm2']==0
assert all(v==0 for v in local['inductor_projections'].values())
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==9
assert all(x['unshielded_by_both_mm2']<1e-6 for x in metrics['opposite_foreign_copper_projections'])
assert metrics['counts']==dict(segments=1400,vias=325,footprints=215,new_segments=7,removed_segments=5)
assert metrics['group_count_changes']==[dict(net='/FAULT_N',before=3,after=2)]
tests=read(b/'R178-side-change-tests-v2/result.json');assert tests['status']=='PASS' and tests['test_count']==13
members={q['member']:q['sha256'] for q in read(dev/'evidence/R168G/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==sha(candidate/n)==h for n,h in members.items())
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
now=datetime.now(timezone.utc).isoformat();commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
study.mkdir();evidence.mkdir()
for p in (b/'R178L-final-checks').iterdir():shutil.copy2(p,evidence/p.name)
for src,dst in [('R178L-plan.json','plan.json'),('R178L-planned-delta.json','planned-delta.json'),('R178L-inspection.json','inspection.json'),('R178L-visual-review.json','visual_review.json'),('R178L-metrics.json','metrics.json'),('R178L-local-reference-review.json','local_reference_review.json'),('R178L-commands.json','build_commands.json')]:shutil.copy2(b/src,evidence/dst)
shutil.copytree(b/'R178L-views',evidence/'images')
(evidence/'source_R168G.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
with (evidence/'remaining_connections.csv').open('x',newline='') as f:
    w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
    for i,x in enumerate(read(evidence/'drc.json')['unconnected_items'],1):w.writerow([i,x['description'],' | '.join(z['description'] for z in x['items'])])
rows=[]
for s in 'ABCDEFGHJKL':
    rev='R178'+s;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert read(b/(rev+'-plan.json'))['board_sha256']==old and sha(b/rev/board)==a['board_sha256']
    row=dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),GND_group_sizes=[len(x) for x in a['GND_groups']],power_failures=[dict(net=x['net'],width_mm=x['width_mm']) for x in a['power_width'] if x['status']=='FAIL'],old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],old_reference_losses=len(a['retained_trace_reference_loss']),new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),adopted=s=='L')
    v=b/(rev+'-final-checks/result.json')
    row['enabled_ERC']=read(v)['erc_violations'] if v.exists() else 'NOT_RERUN'
    rows.append(row)
payloads=[];omitted=[]
def preserve(p,rel):
    data=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf'])
    dest=study/rel
    if compressed:dest=dest.with_name(dest.name+'.gz')
    dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compressed else data)
    payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/x['revision'] for x in rows]
for top in sorted(b.glob('R178*')):
    if top.name=='R178L-views':continue
    for p in ([top] if top.is_file() else sorted(x for x in top.rglob('*') if x.is_file())):
        owner=next((root for root in roots if p.is_relative_to(root)),None);rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for name in ['build_trial.py','review_planned_delta.py','verify_trial.py','audit_ina300_return.py','copper_geometry.py','zone_expansion.py','footprint_side_change.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
    preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R162_inspection.py','R167_joint_pose_screen.py','R177_guarded_route.py','R177_quiet_guarded_route.py','R177_D302_pose_access.py']:
    preserve(b/name,Path('raw/helpers')/name)
for p in sorted((b/'R177-supply-reservations-v3').iterdir()):
    if p.is_file():preserve(p,Path('raw/helpers/R177-supply-reservations-v3')/p.name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R178.json'))
summary=dict(recorded_at_utc=now,source_commit=commit,remote_main='aa94dddebcc8ca40cc4b63616147f81448ef087f',source_revision='R168G',source_sha256=old,adopted_revision='R178L',adopted_board_sha256=new,candidates=rows,preflight_only_failure='R178I: unshielded overlap persisted; no plan or native board was produced. The following build rejected the absent plan.',remaining_unconnected_items=19,baseline_unconnected_items=40,remaining_connectivity_fraction=.475,connectivity_fraction_is_not_engineering_progress=True,full_verification=r,planned_checks=len(planned['checks']),side_change_tests=13,source_ground_vias_preserved=114,unchanged_non_PCB_members=77,whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary)
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,accepted_images='../R178L/images',source_board='../R178L/source_R168G.kicad_pcb.gz',original_local_sources_preserved=True))
for q in payloads:
    p=study/q['path'];assert sha(p)==q['sha256'];data=gzip.decompress(p.read_bytes()) if q['gzip'] else p.read_bytes();assert len(data)==q['source_bytes'] and hashlib.sha256(data).hexdigest()==q['source_sha256']
for q in visual['images_actually_viewed']:assert sha(evidence/q['path'])==q['sha256']
assert gzip.decompress((evidence/'source_R168G.kicad_pcb.gz').read_bytes())==(source/board).read_bytes()
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=11,preflight_only_rejections=1,all_original_byte_hashes_match=True,source_local_trials_untouched=True,accepted_images_hash_verified=9))
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert source_all=={p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
for n,h in source_all.items():
    if n!=board:assert sha(source/n)==h
write(evidence/'adoption.json',dict(adopted_at_utc=now,source_commit=commit,source_sha256=old,adopted_board_sha256=new,source_full_local_backup=str(backup.absolute()),other_native_members_unchanged=77,member_checks=[dict(member=n,sha256=sha(source/n)) for n in members],development_only=True,published_revision='C3 R108P',adopted_in_main_model=False,adopted_in_software=False,engineering_status='FAIL',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
status.update(r);status.update(revision='C3 R178L',previous_candidate='C3 R168G',previous_candidate_sha256=old,strict_regression_explanation='Raw geometry FAIL retains the declared D302 face/pose transform and five replaced CLR tracks. All 2515 exact-delta and electrical/reference checks pass; no rule or threshold changes.',planned_delta_review_status='PASS',planned_delta_check_count=2515,electrical_regression_status='PASS',local_visual_review='PASS',local_visual_review_explanation='Nine native local geometry views. Outward D302 escapes, no new same-face body crossing; opposite C1207/HEAD_VM overlap retains intervening ground. No new FAULT projection onto DVDT copper or L701/L901. Full physical coupling, thermal and assembly qualification remains open.',new_same_face_nominal_body_projection_groups=0,segment_count=1400,via_count=325,footprint_count=215,remaining_connectivity_fraction=.475,remaining_FAULT_N_groups=2,ina300_rlimit_return_evidence='evidence/R178L/ina300-return.json',last_followup_study='R178',latest_study_evidence='evidence/R178_study/summary.json',latest_study_adopted=True,latest_study_note='L joins D302 FAULT with a native vertical F-face pose and short routes to old transfers; all prior electrical checks retained. 19 opens / 47.5 percent by original connection count, not overall engineering progress.',goal_complete=False)
status['open_manufacturer_layout_items'].append(dict(id='D302_F_FACE_PROTOTYPE_LAYOUT',status='NOT_TESTED',reason='Local digital/source checks pass, but full fault/clear timing, EMC, thermal and complete installed front-face assembly remain unqualified.',evidence='evidence/R178L/visual_review.json'))
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(adopted='R178L',board_sha256=new,remaining_unconnected_items=19,planned_checks=2515,archive_payloads=len(payloads),unchanged_non_PCB_members=77,goal_complete=False)))
