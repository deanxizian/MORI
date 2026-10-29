"""Archive the unadopted five-part/power-bridge study and rejected build states."""
import collections,gzip,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R184_study'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R181C' and status['unconnected_items']==19
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert commit.startswith('5f6d8a9')
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
members=read(dev/'evidence/R183_study/archive_manifest.json')['source_non_PCB_members'];assert len(members)==77
assert all(sha(source/n)==h for n,h in members.items())
a=read(b/'R184D-audit.json');d=read(b/'R184D-drc.json');assert a['baseline_sha256']==expected and a['board_sha256']==sha(b/'R184D'/board)
native=dict(revision='R184D',board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),
            DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),schematic_parity=len(d['schematic_parity']),enabled_ERC='NOT_RERUN',
            power_checks_pass=sum(x['status']=='PASS' for x in a['power_width']),power_check_count=len(a['power_width']),
            power_failures=[dict(net=x['net'],width_mm=x['width_mm']) for x in a['power_width'] if x['status']!='PASS'],
            GND_group_sizes=[len(x) for x in a['GND_groups']],critical_adjacency_pass=sum(x['status']=='PASS' for x in a['critical_placement']),
            old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],old_reference_losses=len(a['retained_trace_reference_loss']),
            new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-7 for x in a['new_copper_review']),
            adopted=False)
assert (native['unconnected_items'],native['other_DRC'],native['power_checks_pass'])==(26,3,46)
route_rows=[]
for p in sorted(b.glob('R184D-R184-route-*/result.json')):
    r=read(p);q=r['result'];route_rows.append(dict(name=p.parent.name,net=r['net'],status=q['status'],length_mm=q.get('length_mm'),built_into_PCB=False))
assert len(route_rows)==7 and sum(r['status']=='PROPOSAL' for r in route_rows)==1
poses={phase:{ref:len(read(b/(phase+'-'+ref+'-poses.json'))['candidates']) for ref in ['D1602','C1602','R1601','C1603']} for phase in ['R184-group','R184-power-group']}
pairs={name:{k:v for k,v in read(b/(name+'.json')).items() if k not in ['scope','solutions']} for name in ['R184-group-pairs','R184-power-group-pairs','R184-power-group-cardinal-pairs']}
viewed=['R184-source-control-F.png','R184D-group-B.png'];assert all((b/n).exists() for n in viewed)
study.mkdir();payloads=[];omitted=[]
def write(name,obj):
    with (study/name).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
def preserve(p,rel):
    data=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf','.npz'])
    target=study/rel
    if compressed:target=target.with_name(target.name+'.gz')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(gzip.compress(data,mtime=0) if compressed else data)
    payloads.append(dict(path=target.relative_to(study).as_posix(),sha256=sha(target),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R184'+s) for s in 'ABCD']
for top in sorted(b.glob('R184*')):
    for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):
        owner=next((root for root in roots if p.is_relative_to(root)),None);rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for name in ['R138_joint_search.py','R167_joint_pose_screen.py','R153_run_trial.py','R183-clamp-cap-D1602-pose-screen.json']:
    preserve(b/name,Path('raw/helpers')/name)
preserve(source/board,Path('source_R181C.kicad_pcb'));preserve(dev/'STATUS.json',Path('STATUS.before_R184.json'))
write('summary.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,remote_main=remote,source_revision='R181C',source_sha256=expected,
    adopted_revision=None,native_trial=native,independent_pose_counts=poses,mutual_geometry_screens=pairs,routing_screens=route_rows,
    rejected_builds=[
      dict(revision='R184A',state='Rejected before PCB save: generic builder cannot reconstruct mixed track/via guards. Destination PCB is the unchanged source copy.'),
      dict(revision='R184B',state='Rejected before PCB save: a moved D1602 pad becomes the retiring source via only remaining B-side contact. Source-copy PCB retained.'),
      dict(revision='R184C',state='Saved draft rejected by exact via readback: proposed (35,14.5) overlaps Net-(D1001-K), and KiCad reads that via on the wrong net. Never adopted; no native DRC acceptance claimed.')],
    mixed_guard_check=read(b/'R184D-mixed-guard-readback.json'),
    component_pose=dict(D1602=dict(face='B.Cu',position_mm=[37,15.375],rotation_deg=225),C1602=dict(face='B.Cu',position_mm=[39.875,15.625],rotation_deg=45),R1601=dict(face='B.Cu',position_mm=[41.125,18],rotation_deg=270),D301='unchanged',C1603='unchanged with original GND return'),
    next_step='Compare complete transfer and power restoration before another placement acceptance attempt. Restore the unchanged C1601-to-UPS_BAT source branch first; retain/reuse the original VCAP transfer and its F traces where feasible. A future clamp pose must leave the source transfer usable or explicitly prove a replacement hole with all-layer copper, power and reference checks. Treat the UPS 5 V bridge and gate-RC access as simultaneous constraints. The D gate-only proposal is not a completed circuit.',
    space_finding='The five-part screen still lacks a displaced mutual pair with the current UPS 5 V bridge. Releasing only that bridge creates geometric candidates, but native D loses required power and signal paths. This demonstrates local placement/routing coupling, not global unroutability or sufficiency of a 5 mm expansion.',
    outline_direction='70x40 R182 proposal remains unadopted; no user direction reply received. Current 70x35 outline and fixed interfaces remain.',
    accepted_revision_unchanged='R181C',remaining_unconnected_items=19,newly_completed_connections_in_accepted_board=0,
    whole_board_visual='NOT_TESTED',manufacturer_layout_qualification='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('corrections.json',dict(items=[
    'The preliminary pair reporter omitted the fixed C1603 displacement field; failed script/log preserved, corrected script reran the same geometry with displacement 0.',
    'Plan creation initially used exact Python float equality for 18.825; corrected to an explicit 1e-7 coordinate check and six-decimal native grid. No PCB was written in that attempt.',
    'The first NRST call used an abbreviated net name and failed before solving. The exact /01 {slash} Core/NRST call is separately retained.',
    'The R184 gate/RC inventory used the deprecated unlayered via GetWidth accessor and emitted warnings. The actual via plans use via_snapshot with per-layer dimensions; no via size was changed.',
    'R184C disproves the guessed source-hole position (35,14.5); it must not be reused. Exact native readback caught the wrong net.',
    'R184D restores the RC branch only. Removing the six UPS_BAT B-side leads also disconnected unchanged C1601; the two original C1601-to-(39.15,13) segments should be retained in a subsequent plan.',
    'R184-only mixed-guard builder is a source-specific study helper; production builder and planned-delta validator are unchanged. Readback proof is not full candidate acceptance.']))
write('visual_review.json',dict(images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],scope='Two local native-geometry plots only.',
    observations=['The source F-side view shows the LM74502/FET paths and adjacent R1101 power-sense structure.','The D B-side view shows the diagonal clamp/cap and moved RC resistor; empty former power/transfer routes are not usable completed copper. The new RC segment has a small opposite-face R805 projection in the audit; coupling/thermal qualification remains open.'],
    unbuilt_routes_not_shown_as_copper=True,whole_board='NOT_TESTED',physical='NOT_TESTED'))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,
    shared_reservation_dependency=dict(path='../R182_study/raw/R182-supply-reservations/result.json',sha256=sha(b/'R182-supply-reservations/result.json'),source_sha256=expected),
    reconstruction='Use source_commit native members with byte hashes. Restore raw files into an isolated trials directory and the recorded earlier supply reservations/helpers; retain rejected A/B/C labels. Never export manufacturing data from these boards.',original_local_sources_preserved=True))
for r in payloads:
    data=(study/r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256'];raw=gzip.decompress(data) if r['gzip'] else data
    assert hashlib.sha256(raw).hexdigest()==r['source_sha256'] and len(raw)==r['source_bytes']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_DRC_checked_trials=1,rejected_build_states_preserved=3,
    all_original_byte_hashes_match=True,protected_non_PCB_members_unchanged=77,accepted_source_unchanged=True,actual_viewed_image_count=2,local_originals_preserved=True))
status.update(last_followup_study='R184',latest_study_evidence='evidence/R184_study/summary.json',latest_study_adopted=False,
    latest_study_note='Five-part re-placement is constrained by the original UPS 5 V bridge. A separate bridge-release study enables geometric poses but native D has 26 opens/3 dangling vias and only 46/50 power checks. No adoption; R181C remains at 19 opens.')
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(status='PASS',payloads=len(payloads),accepted_revision='R181C',opens=19,adopted=False)))
