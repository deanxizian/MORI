"""Archive R158 native failures and causal controls without adopting a board."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,json,re,subprocess
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');native=dev/'native';study=dev/'evidence/R158_study';board='MORI_Interface_C3.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
source_sha='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7';assert sha(native/board)==source_sha
members={x['member']:x['sha256'] for x in read(dev/'evidence/R156G/adoption.json')['member_checks']};assert len(members)==77
for name,digest in members.items():assert sha(native/name)==digest
source_all={p.relative_to(native).as_posix():sha(p) for p in native.rglob('*') if p.is_file()};state=read(dev/'STATUS.json');assert state['unconnected_items']==23 and state['board_sha256']==source_sha
control=read(b/'R158-fill-cause/redundant-via-screen.json');assert control['all_other_MOTION_3V3_anchor_width_pairs_preserved'] and not control['MOTION_3V3_lost_pad_connections']
first=read(b/'R158-fill-cause/remove_new_sampling_via-audit.json');assert all(x['status']=='PASS' for x in first['power_width'] if x['net'] in ['MOTION_3V3','/06 {slash} CAM_Buck/UPS_5V'])
assert read(b/'R158C-ina300-return.json')['direct_return_screen']=='PASS'
secondary=b/'R158-fill-cause/remove_sampling_and_3V3_vias/secondary_counterfactual.json';write(secondary,{'source_board_sha256':sha(b/'R158-fill-cause/remove_new_sampling_via'/board),'removed_via':'9fc6be27-25b2-4bce-8f44-98f39ccd1aa1','source_native_contacts':['In3.Cu'],'purpose':'Only redundancy and retained-anchor-width diagnostic; not a design candidate','final_board_sha256':sha(secondary.parent/board)})
study.mkdir(exist_ok=False);payloads=[];omitted=[]
def preserve(src,rel):
 data=src.read_bytes();compress=src.suffix=='.kicad_pcb' or len(data)>524288;dest=study/rel
 if compress:dest=dest.with_name(dest.name+'.gz')
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
 payloads.append({'path':dest.relative_to(study).as_posix(),'sha256':sha(dest),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'gzip':compress})
for p in sorted(b.glob('R158*')):
 if p.is_file():preserve(p,Path('raw')/p.name)
 elif re.fullmatch(r'R158[A-C]',p.name):
  preserve(p/board,Path('boards')/(p.name+'.kicad_pcb'))
  for q in sorted(p.rglob('*')):
   if not q.is_file() or q.name==board:continue
   rel=q.relative_to(p).as_posix()
   if rel in members and sha(q)==members[rel]:continue
   preserve(q,Path('raw')/p.name/rel)
 else:
  copies=[q.parent for q in p.rglob(board)]
  for q in sorted(p.rglob('*')):
   if not q.is_file():continue
   owner=next((root for root in copies if root in q.parents),None);rel=q.relative_to(owner).as_posix() if owner else None
   if rel in members and sha(q)==members[rel]:omitted.append({'path':q.relative_to(b).as_posix(),'source_member':rel,'sha256':sha(q)});continue
   prefix=Path('images') if p.name=='R158-views' else Path('raw')/p.name
   preserve(q,prefix/q.relative_to(p))
for name in ['audit_ina300_return.py','audit_candidate.py','build_trial.py','copper_geometry.py','plan_layered_route.py','plan_existing_copper.py']:
 preserve(dev/'scripts'/name,Path('raw/helpers')/name)
for name in ['R138_joint_search.py','R152_render_highlight.py','R153_run_trial.py']:preserve(b/name,Path('raw/helpers')/name)
preserve(dev/'STATUS.json',Path('raw/STATUS.before_R158.json'))
candidates=[]
for rev in ['R158B','R158C']:
 d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
 candidates.append({'revision':rev,'board_sha256':sha(b/rev/board),**{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'old_power_width_failures':sum(x['status']!='PASS' for x in a['power_width']),'lost_pad_connection_nets':[{'net':x['net'],'pair_count':len(x['lost_pad_pairs'])} for x in a['lost_pad_connections']],'ground_group_sizes':[len(x) for x in a['GND_groups']],'critical_placement_failures':sum(x['status']!='PASS' for x in a['critical_placement']),'old_reference_loss_count':len(a['retained_trace_reference_loss']),'new_reference_gap_count':sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for x in a['new_copper_review']),'ERC':'NOT_TESTED','adopted':False})
now=datetime.now(timezone.utc).isoformat()
causes=[]
for name in ['remove_new_sampling_via','restore_3V3_via','restore_UPS_via','remove_sampling_and_3V3_vias']:
 root=b/'R158-fill-cause';d=read(root/(name+'-drc.json'));a=read(root/(name+'-audit.json'))
 causes.append({'case':name,'board_sha256':sha(root/name/board),'unconnected_items':len(d['unconnected_items']),'violations':len(d['violations']),'schematic_parity':len(d['schematic_parity']),'power_failures':[{'net':x['net'],'width_mm':x['width_mm'],'lost_pair_count':len(x['lost_pairs'])} for x in a['power_width'] if x['status']!='PASS'],'not_a_layout_candidate':True})
write(study/'summary.json',{'recorded_at_utc':now,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'source_revision':'R156G','source_sha256':source_sha,'failed_build':{'revision':'R158A','reason':'Explicit via-move rationale omitted; builder refused before saving altered PCB.','copied_board_sha256':sha(b/'R158A'/board),'native_DRC':'NOT_TESTED'},'candidates':candidates,'counterfactuals':causes,'causal_finding':'Removing only the new UPS sampling via (45.3,8.6) restores both CAM UPS_5V and MOTION_3V3 original width/connectivity checks, but disconnects R1001 sampling. Restoring either moved source via alone does not restore those two supplies.','redundant_via_finding':'In the no-new-sampling-hole control, deleting the moved one-layer 3V3 via loses only width pairs whose endpoint is that deleted via UUID. All other 3V3 width pairs and pads remain connected. This is bounded evidence, not authority to waive a regression or delete source/ground vias.','MOTION_3V3_In2_tracks_allowed_by_existing_R13':True,'search_limits':'The 11.910660 mm, 0.50 mm In2 power bypass is only an unbuilt proposal; CAM 5V and LIMIT fixed-copper searches found no path. All are bounded, not global impossibility proofs.','source_ina300_screen':'FAIL','candidate_C_ina300_necessary_path_screen':'PASS; full layout/plane-contact/coupling qualification NOT_TESTED','current_unconnected_items':23,'remaining_connectivity_fraction':.575,'not_engineering_progress':True,'adopted':False,'manufacturing_release':False,'physical':'NOT_TESTED','goal_complete':False})
write(study/'local_visual_review.json',{'recorded_at_utc':now,'images_actually_viewed':[{'path':p.relative_to(study).as_posix(),'sha256':sha(p)} for p in sorted((study/'images').glob('*.png'))],'scope':'Three local views only: failed candidate B-side and source/candidate In2 comparison. Not complete six-layer acceptance. RLIMIT ground also contacts broad B-side filled copper; explicit-path PASS alone is not vendor layout approval.','candidate_status':'FAIL','whole_board_visual':'NOT_TESTED'})
write(study/'archive_manifest.json',{'scope':__doc__,'payloads':payloads,'source_R156G_non_PCB_members':members,'unchanged_native_members_omitted':omitted,'reconstruction':'Source R156G non-PCB members plus each archived board and its explicit project metadata overlay reproduce the stored studies. Counterfactuals and the LIMIT probe are intentionally invalid diagnostic boards, never candidates.','original_local_sources_preserved':True})
for row in payloads:
 p=study/row['path'];assert sha(p)==row['sha256'];data=gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_sha256'] and len(data)==row['source_bytes']
assert source_all=={p.relative_to(native).as_posix():sha(p) for p in native.rglob('*') if p.is_file()}
write(study/'archive_verification.json',{'status':'PASS','payload_count':len(payloads),'stored_native_boards':sum(x['path'].endswith('.kicad_pcb.gz') for x in payloads),'native_layout_candidates':2,'failed_build_copies':1,'counterfactuals':4,'routing_probes':1,'all_original_byte_hashes_match':True,'canonical_board_unchanged':source_sha,'formal_non_PCB_members_unchanged':77})
state['last_followup_study']='R158';state['latest_study_evidence']='evidence/R158_study/summary.json';(dev/'STATUS.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'payloads':len(payloads),'adopted':False,'canonical_unconnected':23,'remaining_fraction':.575,'source_board_unchanged':True}))
