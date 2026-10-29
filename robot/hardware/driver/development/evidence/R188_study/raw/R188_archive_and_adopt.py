"""Freeze all three local trials; receive C for development after source-bound gates.

No publication, manufacture, mechanical/software adoption or physical qualification.
"""
import collections,csv,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
dev=Path('robot/hardware/driver/development')
source=dev/'native';candidate=b/'R188C';board='MORI_Interface_C3.kicad_pcb'
study=dev/'evidence/R188_study';ev=dev/'evidence/R188C'
backup=Path('robot/.state/c3-completion/baseline_R187F_before_R188C')
old='6dbcf638a4292c080a05c01f46f9317d69bd655f37d57f0da46d6e3d3bfcb876'
new='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write('\n')
assert not study.exists() and not ev.exists() and not backup.exists()
assert sha(source/board)==old and sha(candidate/board)==new
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert commit=='5144d9ad7e35d61e2f39ef6e671cba659ffcacdf'
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
assert remote=='aa94dddebcc8ca40cc4b63616147f81448ef087f'
r=read(b/'R188C-checks/result.json');reg=read(b/'R188C-checks/regression.json')
delta=read(b/'R188C-planned-delta.json');geo=read(b/'R188C-geometry-review.json')
visual=read(b/'R188C-visual-review.json');coupling=read(b/'R188C-coupling-review.json')
survey=read(b/'R188C-reference-survey.json');comparison=read(b/'R188C-reference-comparison.json')
ground=read(b/'R188C-ground-contact-review.json');reservations=read(b/'R188-supply-reservations/result.json')
assert tuple(r[k] for k in ['board_sha256','unconnected_items','violations','schematic_parity','erc_violations','new_reference_gaps','historical_transition_flags'])==(new,19,0,0,0,0,6)
assert r['ina300_rlimit_return_screen']=='PASS'
assert delta['status']=='PASS' and not delta['errors'] and len(delta['checks'])==2524 and all(delta['checks'].values())
assert delta['source_sha256']==old and delta['candidate_sha256']==new
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width'])==50 and all(x['status']=='PASS' for x in reg['power_width'])
assert len(reg['critical_placement'])==63 and all(x['status']=='PASS' for x in reg['critical_placement'])
assert [len(x) for x in reg['GND_groups']]==[155]
assert geo['source_sha256']==old and geo['candidate_sha256']==new
assert geo['track_counts']==dict(before=1415,after=1418) and geo['via_counts']==dict(before=324,after=324)
assert geo['new_holes']==0 and geo['retained_vias_unchanged']==322
assert (geo['moved_GND_vias'],geo['moved_non_GND_vias'],geo['original_ground_via_identities_preserved'],geo['original_ground_vias_unchanged'])==(1,1,114,113)
assert not geo['same_face_nominal_body_hits'] and all(x['unshielded_added_mm2']<1e-8 for x in geo['body_projections'])
assert ground['status']=='PASS' and ground['candidate_sha256']==new and len(ground['contacts'])==114
assert all(all(a>1e-8 for a in x['fill_contact_mm2'].values()) for x in ground['contacts'])
assert coupling['candidate_sha256']==new and coupling['local_development_layout_decision']=='PASS'
assert not coupling['intervening_ground_between_In2_and_In3']
assert visual['local_status']=='PASS' and len(visual['images_actually_viewed'])==10
assert survey['source_sha256']==new and (survey['flagged_tracks'],survey['flagged_nets'])==(75,36)
assert comparison['status']=='PASS' and len(comparison['removed_flags'])==1
assert not comparison['new_flags'] and not comparison['worsened_retained_tracks']
assert reservations['source_sha256']==new
for key in ['checks','roundtrip_checks']:
    assert len(reservations[key])==50 and all(x['status']=='PASS' for x in reservations[key])
members={x['member']:x['sha256'] for x in read(dev/'evidence/R187F/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==sha(candidate/n)==h for n,h in members.items())
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
status=read(dev/'STATUS.json');assert status['revision']=='C3 R187F'
now=datetime.now(timezone.utc).isoformat()
study.mkdir();ev.mkdir()
for p in (b/'R188C-checks').iterdir():shutil.copy2(p,ev/p.name)
for suffix,name in [('plan','plan'),('planned-delta','planned-delta'),('geometry-review','geometry_review'),
                    ('visual-review','visual_review'),('coupling-review','coupling-review'),
                    ('ground-contact-review','ground-contact-review'),('reference-survey','reference-survey'),
                    ('reference-comparison','reference-comparison'),('reference-review-queue','reference-review-queue'),
                    ('commands','build_commands')]:
    shutil.copy2(b/('R188C-'+suffix+'.json'),ev/(name+'.json'))
for name in ['R188C-views','R188-source-views']:shutil.copytree(b/name,ev/name)
(ev/'source_R187F.kicad_pcb.gz').write_bytes(gzip.compress((source/board).read_bytes(),mtime=0))
with (ev/'remaining_connections.csv').open('x',newline='') as f:
    w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
    for i,q in enumerate(read(ev/'drc.json')['unconnected_items'],1):
        w.writerow([i,q['description'],' | '.join(x['description'] for x in q['items'])])
rows=[]
for letter in 'ABC':
    rev='R188'+letter;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert a['board_sha256']==sha(b/rev/board) and a['baseline_sha256']==old
    assert read(b/(rev+'-plan.json'))['board_sha256']==old
    check=b/(rev+'-checks/result.json')
    rows.append(dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),
        other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),
        DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
        enabled_ERC=read(check)['erc_violations'] if check.exists() else 'NOT_RERUN',
        power_checks_pass=sum(x['status']=='PASS' for x in a['power_width']),GND_group_sizes=[len(x) for x in a['GND_groups']],
        old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
        old_reference_losses=len(a['retained_trace_reference_loss']),
        new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),
        adopted=letter=='C'))
payloads=[];omitted=[]
def preserve(path,relative):
    data=path.read_bytes();compress=path.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and path.suffix not in ['.png','.pdf'])
    target=study/relative
    if compress:target=target.with_name(target.name+'.gz')
    target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
    target.write_bytes(gzip.compress(data,mtime=0) if compress else data)
    payloads.append(dict(path=target.relative_to(study).as_posix(),sha256=sha(target),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compress))
roots=[b/q['revision'] for q in rows]
for top in sorted(b.glob('R188*')):
    if top.name in ['R188C-views','R188-source-views']:continue
    files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
    for p in files:
        owner=next((root for root in roots if p.is_relative_to(root)),None)
        rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:
            omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R182_supply_reservations.py']:
    preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('STATUS.before_R188.json'))
prerequisites=[]
for name in ['reference-survey.json','reference-review-queue.json','adoption.json']:
    p=dev/'evidence/R187F'/name
    prerequisites.append(dict(path='../R187F/'+name,sha256=sha(p)))
write(study/'summary.json',dict(recorded_at_utc=now,source_commit=commit,remote_main=remote,
    source_revision='R187F',source_sha256=old,adopted_revision='R188C',adopted_board_sha256=new,
    candidates=rows,completed_native_trials=3,remaining_unconnected_items=19,newly_completed_connections_in_accepted_board=0,
    baseline_unconnected_items=40,remaining_connectivity_fraction=.475,connectivity_fraction_is_not_engineering_progress=True,
    full_verification=r,planned_checks=2524,reference_review_before=76,reference_review_after=75,
    removed_reference_flags=1,U1702_INA_input_remaining_reference_flags=0,unchanged_non_PCB_members=77,
    moved_non_GND_vias=1,moved_GND_vias=1,new_holes=0,source_ground_via_identities_preserved=114,
    source_ground_via_positions_preserved=113,direct_ground_return=delta['ground_direct_return_review'],
    power_reservations='raw/R188-supply-reservations/result.json',
    space_finding='Coordinated C1002 ground and sampling transfer moves repair one comparator reference defect within unchanged 70x35. TVS-adjacent upward via moves violate spacing. This local repair neither closes the nineteen opens nor proves total board area sufficient or insufficient. The R182 enlargement direction remains unapproved.',
    next_step='Use R188C and its newly computed supply reservations. Continue the nineteen open connections and remaining sampling/reference items with complete endpoints, actual all-layer via access, supply and return preservation. Do not reuse rejected R188A/B geometry or unchanged R186 fixed-topology searches.',
    whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,
    unchanged_native_members_omitted=omitted,accepted_images='../R188C/',source_board='../R188C/source_R187F.kicad_pcb.gz',
    external_frozen_prerequisites=prerequisites,
    reconstruction='Restore source commit native members and source R187F PCB before source-bound scripts. Restore raw/R188X PCB plus any archived nonidentical project file for each trial. C retains all 77 original non-PCB members. R188 reservations were newly computed for C; older reservations remain historical.',
    original_local_sources_preserved=True))
for q in payloads:
    p=study/q['path'];assert sha(p)==q['sha256']
    raw=gzip.decompress(p.read_bytes()) if q['gzip'] else p.read_bytes()
    assert len(raw)==q['source_bytes'] and hashlib.sha256(raw).hexdigest()==q['source_sha256']
for q in visual['images_actually_viewed']:assert sha(ev/q['path'])==q['sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),completed_native_trials=3,
    all_original_byte_hashes_match=True,original_local_trials_preserved=True,
    source_native_members_unchanged_before_adoption=True,accepted_images_hash_verified=10))
shutil.copytree(source,backup,copy_function=shutil.copy2)
assert source_all=={p.relative_to(backup).as_posix():sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate/board,source/board);assert sha(source/board)==new
assert all(sha(source/n)==h for n,h in source_all.items() if n!=board)
write(ev/'adoption.json',dict(adopted_at_utc=now,source_commit=commit,source_sha256=old,adopted_board_sha256=new,
    source_full_local_backup=str(backup.absolute()),other_native_members_unchanged=77,
    member_checks=[dict(member=n,sha256=sha(source/n)) for n in members],development_only=True,
    published_revision='C3 R108P',adopted_in_main_model=False,adopted_in_software=False,
    engineering_status='FAIL',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
status.update(r)
status.update(revision='C3 R188C',previous_candidate='C3 R187F',previous_candidate_sha256=old,
    strict_regression_explanation='Raw geometry FAIL records ten retired segments, one planned GND-via move and one planned sampling-via move. All 2524 exact-delta checks pass, including the non-lengthened direct GND return. All original connections, power/ground and reference requirements preserved. No footprint, rule or keepout change.',
    planned_delta_review_status='PASS',planned_delta_check_count=2524,electrical_regression_status='PASS',
    local_visual_review='PASS',local_visual_review_explanation='Ten source/final layer images viewed. One U1702 input reference flag removed. Small added In3 sampling projection onto In2 receiver supply is explicitly unshielded; nearer continuous In4 GND and shorter C1002 direct return support local development acceptance. Complete noise/transient/thermal qualification remains open.',
    new_same_face_nominal_body_projection_groups=0,segment_count=1418,via_count=324,footprint_count=215,
    remaining_connectivity_fraction=.475,ina300_rlimit_return_evidence='evidence/R188C/ina300-return.json',
    last_followup_study='R188',latest_study_evidence='evidence/R188_study/summary.json',latest_study_adopted=True,
    latest_study_note='Only C adopted for development; nineteen opens and six historical transition flags remain. Reference survey improves from 76/37 to 75/36 tracks/nets without new or worsened retained deficits. A/B violate native spacing and introduce CT reference gaps. No outline or fixed-interface change.',
    reference_ground_contact_review='evidence/R188C/ground-contact-review.json',goal_complete=False)
status['whole_board_reference_review']=dict(source_sha256=new,reviewed_tracks=1305,flagged_tracks=75,flagged_nets=36,
    status='REVIEW_REQUIRED',evidence='evidence/R188C/reference-review-queue.json',confirmed_electrical_fault_count='NOT_DETERMINED')
status['current_power_reservations']=dict(source_sha256=new,evidence='evidence/R188_study/raw/R188-supply-reservations/result.json',
    source_width_checks=50,serialization_checks=50,status='PASS',scope='Conservative planning only; native fill and full source regression remain mandatory.')
for item in status['open_manufacturer_layout_items']:
    if item['id']=='TPS3700_U1702_BYPASS_INPUT_AND_FAULT_COUPLING':
        item['current_geometry_evidence']='evidence/R188C/coupling-review.json'
status['open_manufacturer_layout_items'].append(dict(id='C1002_WHEEL_SAMPLING_REFERENCE_REPAIR',status='NOT_TESTED',
    reason='One ground and one sampling via moved with original padstacks; the direct C1002 return shortens to 2.568503 mm. Added In3/In2 receiver-supply projection reviewed locally; full accuracy/noise/transient/thermal and supplier stack qualification remain open.',evidence='evidence/R188C/coupling-review.json'))
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(adopted='R188C',board_sha256=new,opens=19,reference_flags=75,planned_checks=2524,
    archive_payloads=len(payloads),unchanged_non_PCB_members=77,goal_complete=False)))
