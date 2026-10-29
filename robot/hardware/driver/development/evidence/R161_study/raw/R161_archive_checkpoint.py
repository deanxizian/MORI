"""Preserve R161 joint-layout work and failures without adopting an incomplete PCB."""
import collections,gzip,hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R161_study';latest='R161T'
expected='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,value):
 with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['unconnected_items']==22 and status['board_sha256']==expected
members={r['member']:r['sha256'] for r in read(dev/'evidence/R159H/adoption.json')['member_checks']};assert len(members)==77
for n,h in members.items():assert sha(source/n)==h,n
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
v=read(b/(latest+'-verification/result.json'));a=read(b/(latest+'-verification/regression.json'));delta=read(b/(latest+'-planned-delta.json'));inspection=read(b/(latest+'-inspection.json'))
assert v['unconnected_items']==25 and v['violations']==4 and v['schematic_parity']==0 and v['erc_violations']==0
assert v['new_reference_gaps']==0 and v['historical_transition_flags']==6 and v['ina300_rlimit_return_screen']=='PASS'
assert delta['status']=='FAIL' and delta['errors']==['all_prior_pad_connections']
assert all(r['status']=='PASS' for r in a['power_width']) and len(a['power_width'])==50
assert len(a['GND_groups'])==1 and len(a['GND_groups'][0])==155
assert not a['retained_trace_reference_loss'] and not inspection['same_face_nominal_body_hits']
assert inspection['source_ground_vias_preserved']==114 and len(inspection['images_actually_viewed'])==13
study.mkdir();payloads=[];omitted=[];trials=[]
def preserve(p,rel):
 data=p.read_bytes();compress=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288
 dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R161*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch('R161[A-T]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'));changed=[]
  for q in sorted(p.rglob('*')):
   if not q.is_file() or q.name==board:continue
   rel=q.relative_to(p).as_posix()
   if rel in members and sha(q)==members[rel]:omitted.append({'local_path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});continue
   if rel in members:changed.append(rel)
   preserve(q,Path('raw')/p.name/rel)
  d=read(b/(p.name+'-drc.json'));reg=read(b/(p.name+'-audit.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':False,**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'DRC_types':dict(collections.Counter(x['type'] for x in d['violations'])),
   'power_width_failures':sum(x['status']!='PASS' for x in reg['power_width']),
   'old_reference_losses':len(reg['retained_trace_reference_loss']),
   'new_reference_gaps':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in reg['new_copper_review']),
   'lost_pad_connection_nets':[x['net'] for x in reg['lost_pad_connections']],
   'changed_non_PCB_members_in_saved_trial':changed,'physical':'NOT_TESTED'})
 else:
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
assert len(trials)==20
for n in ['build_trial.py','copper_geometry.py','audit_candidate.py','zone_expansion.py','plan_layered_route.py','verify_trial.py','review_planned_delta.py','audit_ina300_return.py']:
 preserve(dev/'scripts'/n,Path('raw/helpers')/n)
for n in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py']:
 preserve(b/n,Path('raw/helpers')/n)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R161.json'))
summary={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'remote_main_read_only_confirmed':'aa94dddebcc8ca40cc4b63616147f81448ef087f','source_revision':'R159H','source_sha256':expected,
 'adopted_revision':None,'working_layout':latest,'working_layout_sha256':v['board_sha256'],'working_native_result':v,
 'working_planned_delta_errors':delta['errors'],'planned_check_count':len(delta['checks']),
 'unchanged_formal_non_PCB_members':77,'source_ground_vias_preserved':114,'power_width_checks_preserved':50,'ground_pads_in_one_group':155,
 'source_old_reference_losses':0,'all_new_reference_gaps':0,'remaining_historical_transition_flags':6,
 'mounted_face_nominal_body_hits':0,'candidates':trials,
 'nomenclature_correction':{'D1803':'B340LA-13-F, C3_Packages:Diodes_SMA; Schottky negative-current recirculation branch. R160 wording calling this a TVS/SMB was incorrect. Native source design was correct and remains unchanged.','D1802':'SMBJ13CA-13-F, C3_Packages:Diodes_SMB; TVS. Both clamp poses, footprints and power branch are retained in the selected working layout.'},
 'progress':['Replaced the preliminary packing screen with one checking native courtyards, PTH lands, source ground vias and exact pads. Retained failed A/B and all diagnostics.',
  'Placed U1301 with local UV/OV/VDD parts while retaining both clamp branches. Explicit C1301 input path uses one transfer and a 5.45422618895781 mm nominal centreline; upstream UV divider is unfinished.',
  'Connected upstream OV without degrading J401 four-spoke thermal checks, any of the 50 power-width checks, source/new references, original ground transfers or return-transition count.',
  'Removed complete obsolete signal-transfer tails explicitly. The final working layout has 25 unconnected items and four dangling-only violations; four old circuit links are deliberately still incomplete, so it is not adopted.',
  'Actually inspected both six-layer local regions and the bias region. Removed the 0.015759856 mm2 C1303 ground escape Fab overlap found after native checks.'],
 'remaining_working_links':read(b/(latest+'-plan.json'))['unfinished_connections'],
 'next_actions':['Restore FAULT, UV_N, R1311 enable and upstream UV-divider links together with power and reference preservation; do not import the four independent E proposals together.',
  'The moved R1502 middle-node transfer at (67.45,28.35) and the F R1503 OV path constrain U1301.6 escape. Compare a joint transfer/branch change; no new transfer position is accepted by this checkpoint.',
  'The J weighted bias route is about 50.86 mm and cuts power regions. Compare bias-pair placement nearer the actual enable source rather than accepting that detour.',
  'Keep all failed boards and native reports. After restoring prior connectivity, run native/plan/reference/ground/power/INA checks and local visual/manufacturer review before any reception.',
  'Then continue all canonical remaining signals, full-board reviews, power/protection/BOM/pin-map and mechanical/harness handoff; this checkpoint does not finish the engineering goal.'],
 'images_actually_viewed':['raw/'+latest+'-views/'+n for n in inspection['images_actually_viewed']],
 'view_scope':'Two local six-layer regions plus the bias B region, not whole-board or physical qualification.',
 'remaining_unconnected_items_in_adopted_development':22,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,
 'connectivity_fraction_is_not_engineering_progress':True,'engineering_status':'FAIL','manufacturing_release':False,'physical':'NOT_TESTED','goal_complete':False}
write(study/'summary.json',summary)
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R159H_non_PCB_members':members,'unchanged_native_members_omitted':omitted,'original_local_sources_preserved':True,
 'reconstruction':'Use source R159H non-PCB members plus each compressed PCB and explicit metadata overlays. Both stored and restored byte hashes are verified.'})
for row in payloads:
 q=study/row['path'];assert sha(q)==row['sha256'];data=gzip.decompress(q.read_bytes()) if row['gzip'] else q.read_bytes()
 assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'stored_native_boards':len(trials),'all_original_byte_hashes_match':True,'source_native_all_members_unchanged':True,'source_local_trials_untouched':True,'source_board_sha256':expected})
status.update({'last_followup_study':'R161','latest_study_evidence':'evidence/R161_study/summary.json','latest_study_adopted':False,
 'latest_study_note':latest+' joint working layout has connected OV/local UV filter, 25 opens and four dangling-only DRC items; four old circuit links still unfinished. Exact delta fails only old-pad connection preservation; canonical R159H / 22 opens unchanged.'})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payloads':len(payloads),'native_boards':len(trials),'working_layout':latest,'adopted':False,'canonical':'R159H','unconnected_items':22,'source_unchanged':True}))
