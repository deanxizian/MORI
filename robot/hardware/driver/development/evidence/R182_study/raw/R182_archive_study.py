"""Freeze source-bound routing trials and an unadopted space comparison.

The accepted R181C board and all original local experiments remain unchanged.
This archive is not a design release, PCB manufacturing package or fit approval.
"""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';study=dev/'evidence/R182_study';board='MORI_Interface_C3.kicad_pcb'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R181C' and status['unconnected_items']==19
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert commit=='c7b8fbee745a83715d9c0a268af8f7f27a993a99'
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
members={x['member']:x['sha256'] for x in read(dev/'evidence/R181C/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
rows=[]
for letter in 'ABCDEFGH':
    rev='R182'+letter;plan=read(b/(rev+'-plan.json'));d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert plan['board_sha256']==expected and a['baseline_sha256']==expected
    assert a['board_sha256']==sha(b/rev/board)
    rows.append(dict(revision=rev,role='routing_trial' if letter!='H' else 'released_terminal_access_preparation',
      board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),
      DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),schematic_parity=len(d['schematic_parity']),
      enabled_ERC='NOT_RERUN',power_checks_pass=sum(r['status']=='PASS' for r in a['power_width']),
      power_check_count=len(a['power_width']),GND_group_sizes=[len(g) for g in a['GND_groups']],
      old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
      old_reference_losses=len(a['retained_trace_reference_loss']),
      new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),adopted=False))
space=read(b/'R182I-space-check.json')
assert space['source_sha256']==expected and space['proposal_sha256']==sha(b/'R182I'/board)
assert space['fixed_core_pin_count']==68 and space['fixed_footprints_checked']==213
assert (space['unconnected_items'],space['other_DRC'],space['schematic_parity'])==(28,3,0)
back=read(b/'R182-global-exact-pose-access/result.json')
front=read(b/'R182-front-exact-pose-access/result.json')
mount=read(b/'R182-front-mount-filter.json')
key=lambda p:(tuple(p['position_mm']),p['rotation_deg'])
valid={key(p) for p in mount['accepted']}
valid_front=[p for p in front['poses'] if key(p) in valid]
signals=lambda p:sum(p['access'][k]['accessible'] for k in ['1','3','5','6'])
supplies=lambda p:sum(p['access'][k]['accessible'] for k in ['2','7','8'])
assert len(back['poses'])==51 and max(map(signals,back['poses']))==3
assert len(valid_front)==2 and len(mount['rejected'])==23
assert max(map(signals,valid_front))==1 and max(map(supplies,valid_front))==0
reservations=read(b/'R182-supply-reservations/result.json')
assert reservations['source_sha256']==expected and len(reservations['roundtrip_checks'])==50
assert all(x['status']=='PASS' for x in reservations['roundtrip_checks'])
viewed=['R182A-power-In3.png','R182E-clr-B.png','R182-space-comparison/comparison.png']
assert all((b/n).is_file() for n in viewed)
study.mkdir();payloads=[];omitted=[]
def write(name,obj):
    with (study/name).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
def preserve(p,rel):
    data=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(data)>524288 and p.suffix not in ['.png','.pdf','.npz'])
    target=study/rel
    if compressed:target=target.with_name(target.name+'.gz')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(gzip.compress(data,mtime=0) if compressed else data)
    payloads.append(dict(path=target.relative_to(study).as_posix(),sha256=sha(target),
       source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/('R182'+x) for x in 'ABCDEFGHI']
for top in sorted(b.glob('R182*')):
    files=[top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
    for p in files:
        owner=next((root for root in roots if p.is_relative_to(root)),None)
        rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:
            omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for n in ['R138_joint_search.py','R167_joint_pose_screen.py','R153_run_trial.py']:
    preserve(b/n,Path('raw/helpers')/n)
preserve(source/board,Path('source_R181C.kicad_pcb'))
preserve(dev/'STATUS.json',Path('STATUS.before_R182.json'))
write('summary.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,remote_main=remote,
 source_revision='R181C',source_sha256=expected,adopted_revision=None,
 routing_and_access_preparation_trials=rows,space_proposal=space,
 source_bound_supply_reservations_recomputed=True,
 rear_pose_screen=dict(candidate_count=51,independent_signal_access_counts=dict(collections.Counter(map(signals,back['poses'])))),
 front_pose_screen=dict(preliminary_count=25,mount_hole_rejected=23,remaining_count=2,
   valid_poses=[dict(position_mm=p['position_mm'],rotation_deg=p['rotation_deg'],signal_access_count=signals(p),supply_access_count=supplies(p)) for p in valid_front]),
 screen_limitations='Bounded coarse placement and raster single-net access screens with C301 omitted for planning; not a proof of simultaneous routing or global infeasibility. Other functional groups remain fixed.',
 accepted_revision_unchanged='R181C',remaining_unconnected_items=19,newly_completed_connections_in_accepted_board=0,
 baseline_unconnected_items=40,remaining_connectivity_fraction=.475,connectivity_fraction_is_not_engineering_progress=True,
 space_finding='Current local topology is constrained by simultaneous signals, retained 3V3/CAM supply paths, body rules and reference ground. Wider grouped redesign or an independently checked extra board area must be compared. No proof that 70x35 is globally unroutable; 70x40 is not proven sufficient.',
 outline_direction_question='Presented 70x40 space model and static comparison; user direction pending. Neither mechanical fit nor adoption has been authorized.',
 next_step='Resolve board-envelope direction while continuing independent work on the other open nets. If the envelope stays fixed, compare a wider functional-group placement instead of repeating fixed-U301 micro-routes. Preserve all source connectivity and electrical rules.',
 manufacturer_layout_qualification='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('corrections.json',dict(notes=[
 'R182E plan calls both OUT anchors transfer centres. (24.775,15.575) is an In3 corner, not a via; the retained track continues to the actual via at (27.825,15.575). Original plan is preserved; no changed routing geometry follows from this wording correction.',
 'Front pose preliminary screen omitted NPTH drills because flashed-copper geometry excludes NPTH. The explicit native drill/body follow-up rejects 23 of 25; only the two remaining poses may be discussed as placement-screen candidates, still not qualified.',
 'R182I first checker stopped on KiCad project normalization. Saved normalized project is preserved, original project bytes restored in independent I, and DRC rerun without save. Native source remained unchanged.',
 'Initial space report core count 60 included J101/J102 only. Explicit J105 eight-pad verification restores the complete count 68; initial report is preserved. No PCB edit.',
 'The first comparison renderer stopped on a missing polygonize import; its log is retained. The corrected renderer completed and the resulting image was viewed.'
 ]))
write('visual_review.json',dict(source_sha256=expected,
 images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],
 scope='Two local native copper views plus equal-scale whole-board footprint/outline comparison. This is not a full routing, 3D assembly or thermal review.',
 observations=[
 'A In3 shows separated 3V3 regions around existing OUT and CAM supply corridor; native regression independently reports 39/17 pad grouping.',
 'E B view shows CLR trapped between U301 pads/body, U303 supply/body and the fixed UPS_5V via at (22.5,14.7).',
 'Space image shows only U301/C301 moved into the orange +Y strip, all connector and mounting datums fixed. Strip has no extended power or reference planes; it is not a usable routed board.',
 'Increasing y35 to y40 grows area by 350 mm2 (14.2857%) and lower hole-centre-to-edge distance from 2.5 to 7.5 mm. Board strength, robot direction and installation clearance remain unverified.'
 ],adopted=False,physical='NOT_TESTED',manufacturing_release=False))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,
 unchanged_native_members_omitted=omitted,original_local_sources_preserved=True,
 reconstruction='Use source commit native members matched by SHA, then restore raw/R182X board and any nonidentical member. I is a space-only proposal; its project normalization was restored. H is access-screen preparation, not a proposed design.'))
for r in payloads:
    p=study/r['path'];assert sha(p)==r['sha256']
    data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes()
    assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_routing_trials=7,
 access_preparation_boards=1,space_proposal_boards=1,all_original_byte_hashes_match=True,
 source_native_members_unchanged=True,protected_non_PCB_members_unchanged=77,local_originals_preserved=True,actual_viewed_image_count=3))
status.update(last_followup_study='R182',latest_study_evidence='evidence/R182_study/summary.json',latest_study_adopted=False,
 latest_study_note='Joint U301 routes conflict with retained 3V3/CAM supply and CLR; broader mounted-face screens find no complete independent access within bounded search. Unadopted 70x40 space model and comparison presented; mechanical direction pending. R181C remains unchanged with 19 opens.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(archived=str(study),payload_count=len(payloads),canonical_unchanged='R181C',opens=19,adopted=False)))
