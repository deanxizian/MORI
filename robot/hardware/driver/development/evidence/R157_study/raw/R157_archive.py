"""Preserve the unadopted R157 studies and add the manufacturer-return blocker."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import gzip,hashlib,json,re,shutil,subprocess
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');native=dev/'native';study=dev/'evidence/R157_study';board='MORI_Interface_C3.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
source_sha='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7';assert sha(native/board)==source_sha
members={x['member']:x['sha256'] for x in read(dev/'evidence/R156G/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(native/name)==digest,name
source_all={p.relative_to(native).as_posix():sha(p) for p in native.rglob('*') if p.is_file()}
assert read(b/'R157-return-checker-tests/result.json')['status']=='PASS'
v=read(b/'R157B-verify/result.json');assert (v['unconnected_items'],v['violations'],v['schematic_parity'],v['erc_violations'],v['ina300_rlimit_return_screen'])==(22,0,0,0,'FAIL')
current=read(dev/'STATUS.json');assert current['board_sha256']==source_sha and current['unconnected_items']==23
study.mkdir(exist_ok=False);payloads=[];trials=[]
def preserve(src,rel,force_plain=False):
 data=src.read_bytes();compress=(src.suffix=='.kicad_pcb' or len(data)>524288) and not force_plain;dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R157*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch(r'R157[A-C]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for name in ['edit_plan.json','edit_manifest.json']:preserve(p/name,Path('raw')/p.name/name)
  changed=[]
  for name,digest in members.items():
   assert (p/name).is_file(),name
   if sha(p/name)!=digest:changed.append(name);preserve(p/name,Path('raw')/p.name/name)
  d=read(b/(p.name+'-drc.json'));a=read(b/(p.name+'-audit.json'));g=read(b/(p.name+'-ina300-return-R157.json'))
  trials.append({'revision':p.name,'board_sha256':sha(p/board),'adopted':False,**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'erc_violations':0 if p.name=='R157B' else 'NOT_TESTED','old_power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'lost_connection_nets':len(a['lost_pad_connections']),'lost_pad_pair_count':sum(len(x['lost_pad_pairs']) for x in a['lost_pad_connections']),'ground_group_sizes':[len(x) for x in a['GND_groups']],'critical_placement_failures':sum(x['status']!='PASS' for x in a['critical_placement']),'old_reference_losses':len(a['retained_trace_reference_loss']),'new_reference_gaps':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),'ina300_return_screen':g['direct_return_screen'],'changed_non_PCB_native_members':changed,'whole_board_visual':'NOT_TESTED','manufacturing_release':False})
 else:
  root=Path('vendor') if p.name=='R157-vendor' else Path('images') if p.name=='R157-return-views' else Path('raw')/p.name
  for q in sorted(p.rglob('*')):
   if q.is_file():preserve(q,root/q.relative_to(p),force_plain=p.name=='R157-vendor')
preserve(b/'R156G-ina300-return-R157.json',Path('baseline-ina300-return.json'))
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R157.json'))
for name in ['audit_ina300_return.py','verify_trial.py','build_trial.py','copper_geometry.py','audit_candidate.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py']:
 preserve(b/name,Path('raw/helpers')/name)
now=datetime.now(timezone.utc).isoformat();pdf=study/'vendor/ina300.pdf';assert sha(pdf)=='348944688a1bdb7d343a4015ecd29a08bd1b78c63de1934d20f867aa61d34188'
write(study/'vendor/source.json',{'recorded_at_utc':now,'download_time':'NOT_RECORDED','url':'https://www.ti.com/lit/ds/symlink/ina300.pdf','file':'ina300.pdf','sha256':sha(pdf),'document':'SBOS613C','revision':'June 2021','printed_pages_reviewed':[29,30],'figure':'10-2 VSSOP','rendered_pages_actually_viewed':['ina300-layout-29.png','ina300-layout-30.png'],'source_file_unchanged':True})
write(study/'local_visual_review.json',{'recorded_at_utc':now,'images_actually_viewed':[{'path':p.relative_to(study).as_posix(),'sha256':sha(p)} for p in [study/'images/source-R156G-B.png',study/'images/unadopted-R157B-B.png',study/'raw/R157-source-wheel-B.png']],'scope':'Local B-side copper comparison only; not a full six-layer candidate acceptance. GND highlighted in the two return views. RLIMIT and GND pin 8 have separate local copper components. Pin 6 LATCH and C505 are not an adequate replacement for the actual device-ground return.','status':'FAIL','whole_board_visual':'NOT_TESTED','all_candidates_unadopted':True})
search=read(b/'R157-remaining-route-proposals.json');counts=Counter(x['result']['status'] for x in search['rows'])
write(study/'summary.json',{'recorded_at_utc':now,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_revision':'R156G','source_sha256':source_sha,'candidates':trials,'adopted_revision':None,'remaining_unconnected_items':23,'baseline_unconnected_items':40,'remaining_connectivity_fraction':.575,'not_engineering_progress':True,'new_baseline_manufacturer_screen':'FAIL: R1701.1 depends on filled planes to reach U1701.8. Full-net GND continuity and old adjacency regressions did not cover the direct return requirement.','checker_cases_passed':3,'verification_integration':'B reports 22 opens and 0 other DRC/parity/ERC, but INA300 screen and engineering status remain FAIL.','remaining_net_search':{'nets':19,'pairs':len(search['rows']),'results':dict(counts),'scope':'Fixed old copper, 0.05 mm grid, per-search expansion bound; no proof of global impossibility.'},'source_non_PCB_native_members_unchanged':77,'physical':'NOT_TESTED','manufacturing_release':False,'goal_complete':False})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R156G_non_PCB_native_members':members,'reconstruction':'Use current R156G native project members, replace only the archived board and the explicitly recorded changed project metadata per trial. All original local trial folders remain intact. The pre-verification B normalized project is separately retained.','local_only':'No source, vendor file, experiment or other worktree was removed.'})
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert len(data)==row['source_bytes'] and hashlib.sha256(data).hexdigest()==row['source_sha256']
assert source_all=={p.relative_to(native).as_posix():sha(p) for p in native.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'native_trial_count':3,'all_stored_and_original_byte_hashes_match':True,'canonical_board_sha256':source_sha,'all_existing_native_files_unchanged':len(source_all),'formal_non_PCB_native_members_unchanged':77,'all_local_sources_preserved':True})
current.update({'last_followup_study':'R157','ina300_rlimit_return_screen':'FAIL','ina300_rlimit_return_evidence':'evidence/R157_study/baseline-ina300-return.json','manufacturer_layout_qualification':'NOT_TESTED','electrical_regression_scope':'Recorded connectivity, power-width, ground-pad, critical-adjacency and reference checks only; not manufacturer layout qualification.','open_manufacturer_layout_items':[{'id':'INA300_RLIMIT_DIRECT_RETURN','status':'FAIL','from':'R1701.1','to':'U1701.8','reason':'Only filled-plane connectivity is present; no explicit track/pad/via return and no same-mounted-face filled component.','datasheet':'TI INA300 SBOS613C section 10.1, printed pages 29-30','evidence':'evidence/R157_study/baseline-ina300-return.json'}]})
(dev/'STATUS.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'archive_payloads':len(payloads),'native_candidates':3,'adopted':False,'current_unconnected':23,'remaining_fraction':.575,'ina300_return':'FAIL','native_source_unchanged':True,'goal_complete':False}))
