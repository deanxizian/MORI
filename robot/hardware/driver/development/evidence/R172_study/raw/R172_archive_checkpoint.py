"""Freeze R172 read-only placement dependencies and native 2D space evidence.

No new native candidate was built in this study. Neither dependency enumeration
nor courtyard occupancy establishes routability, physical fit or qualification.
"""
import gzip,hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native';study=dev/'evidence/R172_study';board='MORI_Interface_C3.kicad_pcb';expected='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
members={r['member']:r['sha256'] for r in read(dev/'evidence/R168G/adoption.json')['member_checks']};assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
strict=read(b/'R172-ina-pose-screen.json');dep=read(b/'R172-ina-dependency-screen.json');space=read(b/'R172-space-review/report.json')
assert strict['source_sha256']==dep['source_sha256']==space['board_sha256']==expected
assert len(strict['poses'])==2 and not any(p['ports'] for p in strict['poses'])
assert dep['candidate_poses']==292 and space['ground_vias']==114
status=read(dev/'STATUS.json');assert status['revision']=='C3 R168G' and status['unconnected_items']==20
study.mkdir();payloads=[]
def preserve(p,rel):
 data=p.read_bytes();dest=study/rel
 if p.name.endswith('_syntax_failed.py'):dest=dest.with_name(dest.name+'.txt')
 compress=p.suffix=='.kicad_pcb' or len(data)>524288
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append(dict(path=dest.relative_to(study).as_posix(),sha256=sha(dest),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),gzip=compress))
for top in sorted(b.glob('R172*')):
 for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):preserve(p,Path('raw')/p.relative_to(b))
for n in ['R138_joint_search.py','R167_joint_pose_screen.py']:preserve(b/n,Path('raw/helpers')/n)
preserve(dev/'scripts/copper_geometry.py',Path('raw/helpers/copper_geometry.py'));preserve(source/board,Path('source_R168G.kicad_pcb'));preserve(dev/'STATUS.json',Path('raw/STATUS.before_R172.json'))
best={str(a):next((r for r in dep['poses'] if r['rotation_deg']==a),None) for a in [0,90,180,270]}
summary=dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_revision='C3 R168G',source_sha256=expected,source_unchanged=True,work_scope='Read-only placement and space review; no candidate PCB built',completed_new_native_trials=0,adopted_revision=None,remaining_unconnected_items=20,baseline_unconnected_items=40,remaining_connectivity_fraction=.5,connectivity_fraction_is_not_engineering_progress=True,strict_pose_screen=dict(position_grid_mm=.25,angles_deg=[0,90,180,270],bounds_mm=strict['bounds_mm'],remaining_poses=2,straight_fault_ports=0,prospectively_moved_parts=strict['prospectively_moved_parts'],prospectively_retired_tracks=len(strict['prospectively_retired_tracks']),prospectively_movable_non_ground_vias=len(strict['prospectively_movable_vias']),rejections=strict['rejections']),dependency_screen=dict(candidates=292,by_rotation=dep['by_rotation'],best_per_rotation=best,limits='Optimistic dependencies only. Every named part, non-ground via and copper conflict requires explicit replacement and complete restoration; no conflict is waived.'),space_inventory=dict(footprints=space['footprints'],segments=space['segments'],vias=space['vias'],ground_vias=space['ground_vias'],areas=space['areas'],missing_mounted_courtyards=space['missing_mounted_courtyards'],limits=space['scope']),visual_review=dict(images_actually_viewed=['raw/R172-space-review/overview.png'],image_type='Native geometry render; fills omitted, courtyards/parts/traces/vias shown',findings=['The front side has substantial power/package and fixed connector/header occupancy; its opposite-face projection is not a blanket routing keepout.','The INA300 area is constrained on both faces by power parts, its passives, U1302 and many fixed GND vias. The global rear courtyard fraction cannot be interpreted as available local routing capacity.','Candidate dependency results suggest expanding the group to U1302 and specific non-ground transfers; no finished new layout has been established.'],whole_board_route_visual='NOT_TESTED',mechanical_fit='NOT_TESTED'),conclusion='Current local layout congestion is supported. Whole-board area insufficiency or global infeasibility is not proved. Do not claim that resizing is necessary or sufficient.',next_actions=[
 'Use accepted R168G as the only source. R171E remains unadopted; the R172 dependency screen is not a native candidate or a new accepted route.',
 'Expand the functional group to include U1302 and explicitly listed supply-transfer dependencies. Compare original-orientation U1701 near (46.75,14)/0 and quarter-turn near (48.75,12.25)/90 as bounded candidate positions, with full passive, bypass and direct RLIMIT return placement before routing.',
 'The base screen prospectively releases five parts, 33 local tracks and three non-ground supply transfers; additional dependency lists are relative to that base. Do not describe a candidate as needing only one moved IC/via in total.',
 'Preserve all 114 GND vias, fixed 70x35 outline/interfaces and native rules. Every new placement must reconstruct exact native guards, recover original functions and pass native DRC/ERC, all original pad/power/reference checks and visual/manufacturer review.',
 'If a larger board or fixed-interface change becomes a concrete proposed alternative, prepare a native model and static comparison with mechanical consequences for user confirmation before adopting it. No board enlargement was performed.'
],source_non_PCB_members_unchanged=77,physical='NOT_TESTED',manufacturing_release=False,goal_complete=False)
write(study/'summary.json',summary);write(study/'archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,original_local_sources_preserved=True,syntax_failure_preserved_as_text=True))
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write(study/'archive_verification.json',dict(status='PASS',payload_count=len(payloads),canonical_unchanged=True,canonical_sha256=expected,source_non_PCB_members_unchanged=77,completed_new_native_trials=0,adopted=False,original_local_sources_untouched=True))
status.update(last_followup_study='R172',latest_study_evidence='evidence/R172_study/summary.json',latest_study_adopted=False,latest_study_note='R172 read-only native space and placement dependency review. Local INA300 congestion is demonstrated; whole-board area insufficiency is not proved. Wider grouped placement with U1302 has unverified dependencies, not a routed candidate. R168G remains 20 opens / 50 percent by connection count.',goal_complete=False)
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(payloads=len(payloads),source_unchanged=True,new_native_trials=0,remaining=20)))
