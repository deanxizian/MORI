"""Freeze R189 source-wide review and unadopted native studies without source edits."""
import collections, gzip, hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R189_study'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R188C' and status['unconnected_items']==19
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert commit=='13856e0be4c1d6b978ca7a73ce38f6d1cdd8ce69'
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
members={r['member']:r['sha256'] for r in read(dev/'evidence/R188C/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
roots=sorted(p for p in b.glob('R189[A-Z]') if p.is_dir());rows=[]
for root in roots:
    rev=root.name;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert a['baseline_sha256']==expected and a['board_sha256']==sha(root/board)
    rows.append(dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),
        other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),enabled_ERC='NOT_RERUN',
        DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
        power_checks_pass=sum(r['status']=='PASS' for r in a['power_width']),
        GND_group_sizes=[len(g) for g in a['GND_groups']],critical_adjacency_pass=sum(r['status']=='PASS' for r in a['critical_placement']),
        old_connection_loss_nets=[r['net'] for r in a['lost_pad_connections']],old_reference_losses=a['retained_trace_reference_loss'],
        new_reference_gap_count=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),
        transition_flags=sum(r['status']=='FAIL' for r in a['reference_transitions']),adopted=False))
viewed=read(b/'R189-visual-review.json')
assert all(sha(b/r['local_path'])==r['sha256'] for r in viewed['images_actually_viewed'])
decision=read(b/'R189-decision.json')
assert decision['adopted'] is False
study.mkdir();payloads=[];omitted=[]
def write(name,obj):
    with (study/name).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
def preserve(p,rel):
    raw=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(raw)>524288 and p.suffix not in ['.png','.pdf','.npz'])
    dst=study/rel
    if compressed:dst=dst.with_name(dst.name+'.gz')
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('xb') as f:f.write(gzip.compress(raw,mtime=0) if compressed else raw)
    payloads.append(dict(path=dst.relative_to(study).as_posix(),sha256=sha(dst),source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),gzip=compressed))
for top in sorted(b.glob('R189*')):
    for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):
        owner=next((root for root in roots+[b/'R189B-initial-build'] if p.is_relative_to(root)),None)
        rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:
            omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for name in ['R138_joint_search.py','R167_joint_pose_screen.py','R153_run_trial.py','R152_render_highlight.py']:
    preserve(b/name,Path('raw/helpers')/name)
preserve(source/board,Path('source_R188C.kicad_pcb'))
preserve(dev/'STATUS.json',Path('STATUS.before_R189.json'))
write('summary.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,remote_main=remote,
    source_revision='R188C',source_sha256=expected,adopted_revision=None,candidates=rows,
    decision=decision,accepted_revision_unchanged='R188C',
    remaining_unconnected_items=19,accepted_transition_flags=6,newly_completed_connections_in_accepted_board=0,
    whole_board_visual='NOT_TESTED',manufacturer_layout_qualification='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('visual_review.json',viewed)
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,
    dependencies=[dict(path='../R188_study/raw/R188-supply-reservations/result.json',sha256=sha(b/'R188-supply-reservations/result.json'),source_sha256=expected)],
    reconstruction='Restore the frozen source PCB and source_commit native members in an independent checkout, then the raw scripts/plans with their frozen dependencies. No source adoption or manufacturing export.',original_local_sources_preserved=True))
for r in payloads:
    data=(study/r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256']
    raw=gzip.decompress(data) if r['gzip'] else data
    assert len(raw)==r['source_bytes'] and hashlib.sha256(raw).hexdigest()==r['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_DRC_checked_trials=len(rows),
    all_original_byte_hashes_match=True,protected_non_PCB_members_unchanged=77,accepted_source_unchanged=True,
    actual_viewed_image_count=len(viewed['images_actually_viewed']),local_originals_preserved=True))
status.update(last_followup_study='R189',latest_study_evidence='evidence/R189_study/summary.json',latest_study_adopted=False,
    latest_study_note=decision['status_note'])
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(status='PASS',payloads=len(payloads),native_trials=len(rows),accepted_revision='R188C',opens=19,adopted=False)))
