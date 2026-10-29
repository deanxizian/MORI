"""Preserve R162 routing progress, causal controls and bounded searches.
No incomplete candidate is adopted; canonical R159H remains unchanged.
"""
import collections,gzip,hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R162_study'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
expected='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['unconnected_items']==22 and status['board_sha256']==expected
members={r['member']:r['sha256'] for r in read(dev/'evidence/R159H/adoption.json')['member_checks']}
assert len(members)==77
for name,h in members.items():assert sha(source/name)==h
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
v=read(b/'R162D-verification/result.json');a=read(b/'R162D-verification/regression.json')
delta=read(b/'R162D-planned-delta.json');inspection=read(b/'R162D-inspection.json')
assert (v['unconnected_items'],v['violations'],v['schematic_parity'],v['erc_violations'])==(24,4,0,0)
assert delta['errors']==['all_prior_pad_connections'] and len(delta['checks'])==2730
assert len(a['power_width'])==50 and all(r['status']=='PASS' for r in a['power_width'])
assert len(a['GND_groups'])==1 and len(a['GND_groups'][0])==155
assert not a['retained_trace_reference_loss'] and not inspection['same_face_nominal_body_hits']
assert v['new_reference_gaps']==0 and v['historical_transition_flags']==6 and inspection['source_ground_vias_preserved']==114
assert v['ina300_rlimit_return_screen']=='PASS'
assert len(a['lost_pad_connections'])==3
study.mkdir();payloads=[];omitted=[];trials=[]
def write(p,value):
 with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def preserve(p,rel):
 data=p.read_bytes();compress=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288
 dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R162*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch('R162[A-G]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'));changed=[]
  for q in sorted(p.rglob('*')):
   if not q.is_file() or q.name==board:continue
   rel=q.relative_to(p).as_posix()
   if rel in members and sha(q)==members[rel]:omitted.append({'local_path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});continue
   if rel in members:changed.append(rel)
   preserve(q,Path('raw')/p.name/rel)
  d=read(b/(p.name+'-drc.json'));reg=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':False,
   **{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'DRC_types':dict(collections.Counter(r['type'] for r in d['violations'])),
   'power_width_failures':[{'net':r['net'],'width_mm':r['width_mm'],'lost_pair_count':len(r['lost_pairs'])} for r in reg['power_width'] if r['status']!='PASS'],
   'old_reference_losses':len(reg['retained_trace_reference_loss']),
   'new_reference_gaps':sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in reg['new_copper_review']),
   'lost_pad_connection_nets':[r['net'] for r in reg['lost_pad_connections']],
   'changed_non_PCB_members_in_saved_trial':changed,'physical':'NOT_TESTED'})
 else:
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
assert len(trials)==7
for name in ['build_trial.py','copper_geometry.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py','verify_trial.py','review_planned_delta.py','audit_ina300_return.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py','R161R_inspection.py','R161_power_aware_search.py','R161T-plan.json']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R162.json'))
summary={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_revision':'R159H','source_sha256':expected,'adopted_revision':None,'best_verified_working_layout':'R162D','experimental_entry':'R162G',
 'working_native_result':v,'working_planned_delta_errors':delta['errors'],'planned_check_count':len(delta['checks']),
 'source_ground_vias_preserved':114,'power_width_checks_preserved_in_D':50,'ground_pads_in_one_group_in_D':155,
 'source_old_reference_losses_in_D':0,'new_reference_gaps_in_D':0,'historical_transition_flags_in_D':6,
 'mounted_face_nominal_body_hits_in_D':0,'opposite_or_internal_projection_hits_in_D':len(inspection['opposite_or_internal_body_hits']),
 'remaining_working_links':[r['net'] for r in a['lost_pad_connections']],'candidates':trials,
 'progress':['Moved the R1502 middle-node transfer to (67.65,25.15), rerouted both branches and the OV input, and opened an outward U1301.6 FAULT escape at (67.45,28.35).',
  'D restored the old U1301 FAULT connection: 25 to 24 opens. It preserves the 50 power-width checks, 155 ground pads, 114 source ground vias and old/new references; only preservation of three old connection nets still fails exact-delta review.',
  'E moved FAULT to allowed In2. Native connectivity stayed at 24/4 but MOTION_3V3 failed 0.40 and 0.48 mm preservation, losing 182 source anchor pairs at each width. F removed only the final vertical tail; both failures remained, ruling out that tail as the sole cause.',
  'Derived a 17.743860018001282 mm centreline inside native source 0.48 mm In2 power copper as a planning obstacle. Restricted local In3 crossing searches did not find a path; no routing rule was relaxed.',
  'G establishes a shorter FAULT main-group transfer at (54.3,33.9), preserving power and references, but has not connected it to U1301. The earlier long B tail should not be blindly reused for the UV input.',
  'Strict bias-pair placement near ENABLE found no pair with fixed existing copper. A separate pending-copper diagnostic found 2046 nominal pairs; its leading result conflicts with the R159H UPS sample via and three UPS tracks and is not adopted.'],
 'next_actions':['Continue joint routing of the two UV links, FAULT and ENABLE; D is electrically closer but its fixed In3 route blocks both bounded UV searches. G is an unfinished alternate terminal, not a replacement accepted board.',
  'Preserve native J702 via keepouts. Read-only candidate positions (59.1,29.5) and (59.3,30.7) violate those guards; do not insert a local crossing there. The native HEAD_VM transfer at (58.6,28.6) has 0.20 mm sense-branch tracks and may be considered only with complete net/branch rerouting and source-ground preservation.',
  'Do not adopt the leading bias-packing result merely because it ranks first. It overlaps protected recent UPS sampling work. Compare a larger connected component group and explicit non-ground-copper changes before building a new candidate.',
  'After restoring all old connections, rerun native/plan/reference/ground/power/INA checks and actual mounted-face/opposite-layer visual/manufacturer review. Continue all 22 canonical remaining items and full engineering review afterward.'],
 'images_actually_viewed':['raw/R162-power-views/R162D-In2.png','raw/R162-power-views/R162E-In2.png'],
 'view_scope':'Two local In2 power-corridor comparisons only; no completed mounted-face or whole-board visual review for R162.',
 'unchanged_formal_non_PCB_members':77,'remaining_unconnected_items_in_adopted_development':22,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,
 'connectivity_fraction_is_not_engineering_progress':True,'whole_board_visual':'NOT_TESTED','physical':'NOT_TESTED','engineering_status':'FAIL','manufacturing_release':False,'goal_complete':False}
write(study/'summary.json',summary)
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R159H_non_PCB_members':members,'unchanged_native_members_omitted':omitted,'original_local_sources_preserved':True,
 'reconstruction':'Use R159H non-PCB members, the compressed candidate PCB and any saved metadata overlays. Stored and restored byte hashes are both checked.'})
for r in payloads:
 q=study/r['path'];assert sha(q)==r['sha256'];data=gzip.decompress(q.read_bytes()) if r['gzip'] else q.read_bytes()
 assert len(data)==r['source_bytes'] and hashlib.sha256(data).hexdigest()==r['source_sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'stored_native_boards':7,'all_original_byte_hashes_match':True,'source_native_all_members_unchanged':True,'source_local_trials_untouched':True,'source_board_sha256':expected})
status.update({'last_followup_study':'R162','latest_study_evidence':'evidence/R162_study/summary.json','latest_study_adopted':False,
 'latest_study_note':'R162D restores FAULT with 24 opens / 4 dangling items and preserved power/reference/ground checks. Three old nets remain incomplete; G is an unfinished alternate transfer. Canonical R159H / 22 opens unchanged.'})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payloads':len(payloads),'native_boards':len(trials),'working_layout':'R162D','adopted':False,'canonical':'R159H','unconnected_items':22}))
