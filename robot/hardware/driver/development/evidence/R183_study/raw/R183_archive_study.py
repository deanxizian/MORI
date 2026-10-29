"""Freeze R183 source-wide and reset/clamp studies without adopting a PCB.

All local originals remain. No manufacturing, physical or global routing
qualification follows from a bounded screen or a locally clean native DRC.
"""
import collections,gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';study=dev/'evidence/R183_study';board='MORI_Interface_C3.kicad_pcb'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R181C' and status['unconnected_items']==19
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert commit=='bb03d31ff19d69ef05e7bf9fff6431245def6466'
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
members={x['member']:x['sha256'] for x in read(dev/'evidence/R181C/adoption.json')['member_checks']}
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
rows=[]
for rev in ['R183A','R183B']:
    plan=read(b/(rev+'-plan.json'));d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert plan['board_sha256']==expected and a['baseline_sha256']==expected
    assert a['board_sha256']==sha(b/rev/board)
    rows.append(dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),
      other_DRC=len(d['violations']),DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
      schematic_parity=len(d['schematic_parity']),enabled_ERC='NOT_RERUN',
      power_checks_pass=sum(x['status']=='PASS' for x in a['power_width']),power_check_count=len(a['power_width']),
      GND_group_sizes=[len(g) for g in a['GND_groups']],
      critical_adjacency_pass=sum(x['status']=='PASS' for x in a['critical_placement']),
      old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
      old_reference_losses=len(a['retained_trace_reference_loss']),
      new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),
      adopted=False))
assert [(r['unconnected_items'],r['other_DRC']) for r in rows]==[(20,6),(20,0)]
assert all(r['power_checks_pass']==50 and r['GND_group_sizes']==[155] for r in rows)
normal=read(b/'R183-source-screen/summary.json');diagnostic=read(b/'R183-diagnostic-source-screen/summary.json')
assert len(normal['results'])==len(diagnostic['results'])==17
assert all(r['result']['status']=='NO_RASTER_CONNECTION' for r in normal['results']+diagnostic['results'])
poses=read(b/'R183-D301-two-face-screen.json')
access=[read(b/('R183-D301-two-face-access-'+face+'/result.json')) for face in ['B','F']]
assert [len(d['poses']) for d in access]==[246,42]
assert all(r['signal_access_count']<2 for d in access for r in d['poses'])
clamp=read(b/'R183-clamp-group-pose-screen.json')
cp={r:read(b/('R183-clamp-cap-'+r+'-pose-screen.json')) for r in ['D1602','C1602']}
pairs=read(b/'R183-clamp-cap-pairs.json')
assert len(clamp['candidates'])==2 and [len(cp[r]['candidates']) for r in ['D1602','C1602']]==[68,407]
assert pairs['novel_clamp_pair_count']==0
nrst=read(b/'R183B-R183-route-nrst/result.json')
assert nrst['result']['status']=='PROPOSAL' and abs(nrst['result']['length_mm']-25.4033008588991)<1e-8
viewed=['R183-source-reset-clamp-B.png','R183A-placement-B.png','R183B-placement-B.png']
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
    payloads.append(dict(path=target.relative_to(study).as_posix(),sha256=sha(target),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compressed))
roots=[b/'R183A',b/'R183B']
for top in sorted(b.glob('R183*')):
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
preserve(dev/'STATUS.json',Path('STATUS.before_R183.json'))
write('summary.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,remote_main=remote,
 source_revision='R181C',source_sha256=expected,adopted_revision=None,native_trials=rows,
 fixed_layout_screen=dict(connection_pairs=17,distinct_nets=len({r['net'] for r in normal['results']}),proposals=0,
   omitted_fixed_terminals=normal['skipped'],planning_only_no_power_reservation_comparison=dict(connection_pairs=17,proposals=0,native_acceptance_criteria_unchanged=True)),
 D301_two_face_screen=dict(coarse_pose_count=len(poses['candidates']),rear_exact_access_poses=246,front_exact_access_poses=42,
   both_nets_accessible_poses=0,scope='Single-net raster access with actual proposed pads/body/via guards restored; not simultaneous routing or a global impossibility proof.'),
 D301_local_PTH_correction=dict(preliminary_poses=6,corrected_poses=2,
   reason='Drill/body clearance alone missed PTH copper inside courtyard. Native A rejects the four displaced near-header poses; corrected screen keeps only original-location orientations.'),
 B_NRST_proposal=dict(length_mm=nrst['result']['length_mm'],layers=['B.Cu'],new_vias=0,built_into_PCB=False,
   reason_not_adopted='Long perimeter detour; original CLR connection remains missing. A separate proposal is not a completed design.'),
 clamp_pair_screen=dict(released_refs=['D301','D1602'],candidate_count=2,max_displacement_mm=max(x['displacement_mm'] for x in clamp['candidates']),clamp_target_mm=5),
 clamp_cap_screen=dict(released_refs=['D301','D1602','C1602'],D1602_independent_poses=68,C1602_independent_poses=407,
   mutual_pairs_with_D301_retained=len(pairs['pairs']),novel_clamp_pairs=0,clamp_limit_mm=5,cap_limit_mm=3,
   scope='Eight rotations and 0.125 mm grid. Explicit terminal branches and three non-ground transfers prospectively released, all ground vias retained. No full electrical restoration claimed.'),
 next_step='A larger coordinated disconnect-control layout is needed for the next comparison; include charge-pump/gate-slew placement, actual transfer holes, restored source power paths and reset escape together. Do not repeat the same fixed layouts or accept a moved diode that loses CLR. Keep the 70x35 outline while the separate enlargement-direction question is pending.',
 generated_but_not_executed_helpers=['raw/R183_d301_exact_access.py','raw/R183_regions.py'],
 accepted_revision_unchanged='R181C',remaining_unconnected_items=19,newly_completed_connections_in_accepted_board=0,
 baseline_unconnected_items=40,remaining_connectivity_fraction=.475,connectivity_fraction_is_not_engineering_progress=True,
 space_finding='Actual local placement and routing congestion is demonstrated. Searches do not establish global unroutability or prove an expanded outline sufficient.',
 outline_direction='70x40 independent proposal from R182 remains unadopted; user direction not received. Current board unchanged.',
 whole_board_visual='NOT_TESTED',manufacturer_layout_qualification='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('visual_review.json',dict(source_sha256=expected,
 images_actually_viewed=[dict(path='raw/'+n,sha256=sha(b/n)) for n in viewed],
 scope='Three native B-face local plots; not a full-board or mechanical-assembly review.',
 observations=[
 'A physically places D301 between J101 pads 18 and 20; native PTH-inside-courtyard errors and silk overlaps are retained, not waived.',
 'B clears those placement errors at (42,26), but D301 CLR is unconnected and the NRST pins remain separate. The 25.403 mm route is only a search proposal and is not shown as real copper.',
 'The original reset/clamp view shows the D1602 body/branch under the D301 escape, adjacent C1602 charge-pump path and fixed ground vias. Individual capacitor/diode positions cannot be combined without mutual checking.'
 ],adopted=False,physical='NOT_TESTED',manufacturing_release=False))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,
 unchanged_native_members_omitted=omitted,original_local_sources_preserved=True,
 shared_reservation_dependency=dict(path='../R182_study/raw/R182-supply-reservations/result.json',sha256=sha(b/'R182-supply-reservations/result.json'),source_sha256=expected),
 reconstruction='Restore source commit native members by SHA, then the selected raw/R183A or B PCB and any changed project member. For search reproduction also restore the R182 reservation directory and helpers. Neither A nor B is accepted.'))
for r in payloads:
    p=study/r['path'];assert sha(p)==r['sha256']
    data=gzip.decompress(p.read_bytes()) if r['gzip'] else p.read_bytes()
    assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_trials=2,all_original_byte_hashes_match=True,
 source_native_members_unchanged=True,protected_non_PCB_members_unchanged=77,local_originals_preserved=True,actual_viewed_image_count=3))
status.update(last_followup_study='R183',latest_study_evidence='evidence/R183_study/summary.json',latest_study_adopted=False,
 latest_study_note='No remaining fixed-layout route proposal in 17 pairs, including the diagnostic power-reservation comparison. D301 moves fail PTH courtyard or lose CLR; the available NRST detour is unbuilt. Joint clamp/cap placement finds no displaced mutual combination under current fixed neighbors. No PCB adopted; R181C and 19 opens remain.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(archived=str(study),payload_count=len(payloads),canonical_unchanged='R181C',opens=19,adopted=False)))
