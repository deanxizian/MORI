"""Preserve unfinished R160 relocation diagnostics without adopting a PCB."""
import collections,gzip,hashlib,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R160_study'
expected='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def write(p,value):
 with p.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['unconnected_items']==22 and status['board_sha256']==expected
members={row['member']:row['sha256'] for row in read(dev/'evidence/R159H/adoption.json')['member_checks']}
assert len(members)==77
for name,digest in members.items():assert sha(source/name)==digest,name
source_all={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
study.mkdir();payloads=[];omitted=[];trials=[]
def preserve(p,rel):
 data=p.read_bytes();compress=p.suffix in ('.kicad_pcb','.kicad_prl') or len(data)>524288
 dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),
  'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R160*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch('R160[AB]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  changed=[]
  for q in sorted(p.rglob('*')):
   if not q.is_file() or q.name==board:continue
   rel=q.relative_to(p).as_posix()
   if rel in members and sha(q)==members[rel]:
    omitted.append({'local_path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});continue
   if rel in members:changed.append(rel)
   preserve(q,Path('raw')/p.name/rel)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'))
  assert not any(v['type']=='courtyards_overlap' for v in d['violations'])
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'diagnostic_only':True,'adopted':False,
   **{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},
   'DRC_types':dict(collections.Counter(v['type'] for v in d['violations'])),
   'changed_retained_copper':a['changed_retained_copper'],'changed_non_PCB_source_members':changed,
   'old_power_width_failures':sum(v['status']!='PASS' for v in a['power_width']),
   'lost_pad_connection_nets':len(a['lost_pad_connections']),'ERC':'NOT_TESTED','physical':'NOT_TESTED'})
 else:
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,Path('raw')/q.relative_to(b))
assert len(trials)==2
assert trials[0]['changed_retained_copper']==[{'uuid':'0e3037d9-c29e-4eda-9f7f-a8ef15dfb01e','source_net':'GND','candidate_net':'MOTION_3V3'}]
assert not trials[1]['changed_retained_copper']
for name in ['build_trial.py','copper_geometry.py','audit_candidate.py','zone_expansion.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py']:
 preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R160.json'))
packing=read(b/'R160-joint-packing.json')
write(study/'summary.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
 'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_revision':'R159H','source_sha256':expected,'adopted_revision':None,'candidates':trials,
 'bounded_placement_search':{'poses_each':4092,'U1301_only_candidates':0,'joint_with_all_vias_fixed_candidates':0,
  'joint_with_only_ground_and_PTH_fixed_candidates':5,'passive_packing_grid_mm':packing['grid_mm'],
  'passive_domain_counts':{ref:d['valid_poses'] for ref,d in packing['diagnostics'].items()},
  'compatible_combinations_returned':len(packing['solutions']),'search_nodes':packing['search_nodes'],
  'limit':'Eight early compatible packing results are not an optimum, routing proof, or global impossibility proof.'},
 'A_source_ground_identity_failure':'Old GND via 0e3037d9-c29e-4eda-9f7f-a8ef15dfb01e at (66.5,26.125) overlaps relocated C1303. The refilled failed A board assigns MOTION_3V3; retain source identity GND. Never use failed A as the net authority.',
 'packing_screen_correction':'The first packing run compared drill-only body obstacles against full-annulus conflicts. V2 consistently screens full source GND annuli; both failed script and log are retained.',
 'B_scope':'Seven component transforms only. All old copper is deliberately retained to expose required rerouting. No source ground via moves or net changes, and no courtyard-overlap violation; the board remains electrically invalid.',
 'next_work':['Plan input-filter, decoupling and output escapes together before accepting a packing score. Preserve original GND vias and J702.2 native four-spoke requirement.',
  'Jointly replace conflicting WHEEL_VM 0.80 mm TVS branch, U1501 OV/divider copper and affected non-ground transfers; restore all old connections and widths.',
  'Rebuild from R159H with exact replacements and native refill. If this bounded group cannot provide clean escapes, compare a broader movable group; do not force long detours or waive checks.',
  'Then continue the remaining 22 opens and the full engineering review; R160 A/B do not reduce the adopted count.'],
 'images_actually_viewed':['raw/R160A-views/source-F.png','raw/R160A-views/source-B.png',
  'raw/R160A-views/R160A-F.png','raw/R160A-views/R160A-B.png',
  'raw/R160B-views/R160B-F.png','raw/R160B-views/R160B-B.png'],
 'view_scope':'Two outer-layer local regions, not six-layer or whole-board acceptance.',
 'remaining_unconnected_items':22,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.55,
 'not_engineering_progress':True,'engineering_status':'FAIL','manufacturing_release':False,'physical':'NOT_TESTED','goal_complete':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R159H_non_PCB_members':members,
 'unchanged_native_members_omitted':omitted,'original_local_sources_preserved':True,
 'reconstruction':'Use source R159H non-PCB members plus each compressed native board and explicit project metadata overlays. All stored/restored payload hashes are checked.'})
for row in payloads:
 q=study/row['path'];assert sha(q)==row['sha256']
 data=gzip.decompress(q.read_bytes()) if row['gzip'] else q.read_bytes()
 assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_all=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'stored_native_boards':2,
 'all_original_byte_hashes_match':True,'source_native_all_members_unchanged':True,'source_local_trials_untouched':True,
 'source_board_sha256':expected})
status.update({'last_followup_study':'R160','latest_study_evidence':'evidence/R160_study/summary.json',
 'latest_study_adopted':False,'latest_study_note':'Unfinished U1301/filter/divider joint-placement diagnostics A/B; original entry remains R159H / 22 opens.'})
(dev/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payloads':len(payloads),'native_boards':2,'adopted':False,'current':'R159H','unconnected_items':22,'source_unchanged':True}))
