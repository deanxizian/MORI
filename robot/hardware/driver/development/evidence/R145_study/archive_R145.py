"""Archive executed R145 work and adopt only the independently verified R145I."""
import csv,datetime,gzip,hashlib,json,shutil
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');native=dev/'native'
ev=dev/'evidence/R145I';study=dev/'evidence/R145_study'
source_sha='f783cf5dfad0ff8020aac8906f12dd018287af6a6d548600d4776fb3603225a5'
candidate_sha='1d32097f2b72c2add4d9a2fd68a2c4ed088b23cbf7606aa1ae3256cc5e48330c'
board=native/'MORI_Interface_C3.kicad_pcb';candidate=b/'R145I/MORI_Interface_C3.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(board)==source_sha and sha(candidate)==candidate_sha
result=json.loads((b/'R145I-verify/result.json').read_text());reg=json.loads((b/'R145I-verify/regression.json').read_text());delta=json.loads((b/'R145I-planned-delta.json').read_text());metrics=json.loads((b/'R145I-local-metrics.json').read_text())
assert result['unconnected_items']==28 and all(result[k]==0 for k in ['violations','schematic_parity','erc_violations','new_reference_gaps'])
assert delta['status']=='PASS' and metrics['same_face_body_hits']==0
assert json.loads((b/'R145I-independent-rebuild-v2.json').read_text())['status']=='PASS'
assert json.loads((b/'R145-via-move-guards/result.json').read_text())['status']=='PASS'
assert not reg['changed_project_members'] and len(reg['unchanged_project_members'])==77
for p in native.rglob('*'):
 if p.is_file() and p.suffix not in ['.kicad_pcb','.kicad_prl','.lck']:
  assert p.read_bytes()==(b/'R145I'/p.relative_to(native)).read_bytes()
ev.mkdir(exist_ok=False);study.mkdir(exist_ok=False)
payloads=[]
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();shutil.copy2(src,dst)
 payloads.append({'path':str(dst.relative_to(dev/'evidence')),'source_path':str(src),'sha256':sha(src),'kind':'byte_copy'})
def compressed(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();data=src.read_bytes();dst.write_bytes(gzip.compress(data,mtime=0))
 payloads.append({'path':str(dst.relative_to(dev/'evidence')),'source_path':str(src),'sha256':sha(dst),'uncompressed_sha256':hashlib.sha256(data).hexdigest(),'kind':'gzip'})
for p in sorted(b.glob('R145*')):
 if p.is_file():copy(p,study/'records'/p.name)
for revision in ['R145A','R145B','R145C','R145D','R145E','R145F','R145H','R145I']:
 compressed(b/revision/'MORI_Interface_C3.kicad_pcb',study/'native'/(revision+'.kicad_pcb.gz'))
 for name in ['edit_plan.json','edit_manifest.json']:copy(b/revision/name,study/'native'/revision/name)
for folder in ['R145-views','R145-power-views','R145I-views']:
 for p in sorted((b/folder).iterdir()):
  if p.is_file():copy(p,study/'diagnostic_images'/folder/p.name)
for p in sorted((b/'R145-via-move-guards').glob('*.json')):copy(p,study/'via_move_guard_tests'/p.name)
copy(Path(__file__),study/'archive_R145.py')
for p in sorted((b/'R145I-verify').iterdir()):
 if p.is_file():copy(p,ev/p.name)
for src,name in [('R145I-plan.json','plan.json'),('R145I-planned-delta.json','planned-delta.json'),('R145I-commands.json','construction-commands.json'),('R145I-local-metrics.json','local-metrics.json'),('R145I-independent-rebuild-v2.json','independent-rebuild.json')]:copy(b/src,ev/name)
copy(b/'R145I/edit_manifest.json',ev/'edit_manifest.json')
copy(b/'R145-via-move-guards/result.json',ev/'via-move-guard-tests.json')
compressed(board,ev/'source-R144M.kicad_pcb.gz')
for ly in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']:
 for suffix in ['svg','png']:copy(b/'R145I-views'/(ly+'-isolated.'+suffix),ev/'images'/(ly+'.'+suffix))
for name in ['R144M-B.Cu','former-D1601-F.Cu']:
 for suffix in ['svg','png']:copy(b/'R145I-views'/(name+'.'+suffix),ev/'images'/(name+'.'+suffix))
def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
viewed=[{'path':'images/'+ly+'.png','status':'PASS','scope':'Local native-geometry diagnostic, rendered in a separate process and actually inspected.'} for ly in ['F.Cu','B.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu']]
viewed += [{'path':'images/R144M-B.Cu.png','status':'PASS','scope':'Previous local geometry inspected for comparison.'},{'path':'images/former-D1601-F.Cu.png','status':'PASS','scope':'Former D1601 location inspected; obsolete transfer removed, original inner-layer main junction retained.'}]
visual={'board_sha256':candidate_sha,'local_status':'PASS','whole_board':'NOT_TESTED','images_actually_viewed':viewed,'findings':['D1601 retains its 90 degree front-face orientation; both terminals escape outside the nominal body. EN joins the local U1601/R1602 branch.','The back-face ARMED path enters the existing R903 pad from above. The upper search zigzag is replaced by straight runs. The remaining dogleg follows the fixed J105 hole and its reference void; the attempted shortcut failed exact clearance/reference geometry.','C912, C913, R1602 and all fixed connectors remain in their original positions. D301 moved 0.075 mm left and 0.05 mm upward; its original CLR connection and NRST net assignment are retained.','The moved ACT_FET_SOURCE via retains its UUID, net, drill and annuli; its B/In3 tails are restored. No ground via was moved or reassigned.','The six local layers and corrected back-face pad annuli were inspected. The first batched back-face diagnostic omitted annuli; it is retained as superseded evidence, not used as the accepted view.'],'projection_review':[{'reference':'C912','relationship':'Opposite-face projection of the new back-face ARMED path','review':'Front input capacitor and copper unchanged. B signal remains outside the mounted-side bodies and references continuous In4. No placement beneath a same-face capacitor is introduced.','coupling_and_thermal':'NOT_TESTED'},{'reference':'D1602','relationship':'Front EN and inner source-tail projections','review':'D1602 stays fixed. The source tail is its existing electrical return group, with exact pad connectivity and reference coverage verified.','coupling_and_thermal':'NOT_TESTED'},{'reference':'D301','relationship':'Opposite-face projection of the front ARMED escape','review':'Actual D301 body/guards move together; mounted-side clearance and unchanged CLR/NRST mapping verified. Each route retains its own reference layer.','coupling_and_thermal':'NOT_TESTED'},{'reference':'J105','relationship':'Back-face and inner projection below the fixed front connector','review':'Actual pad lands, plated holes and native keepouts remain. Back-face path deliberately follows the In4 corridor between hole voids; no connector move or all-layer exemption.','coupling_and_thermal':'NOT_TESTED'}],'limits':['Scoped local visual review only; whole-board per-track/per-via review is unfinished.','The nominal Fab screen is not a measured body envelope or thermal/EMC qualification.','Six historical reference-transition flags remain.'],'manufacturing_release':False}
dump(ev/'visual_review.json',visual)
drc=json.loads((ev/'drc.json').read_text())
with (ev/'remaining_connections.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for i,r in enumerate(drc['unconnected_items'],1):w.writerow([i,r['description'],' | '.join(x['description'] for x in r['items'])])
rows=[]
for rev in ['R145A','R145B','R145C','R145D','R145E','R145F','R145H','R145I']:
 d=json.loads((b/(rev+'-drc.json')).read_text());r=json.loads((b/(rev+'-audit.json')).read_text())
 rows.append({'revision':rev,'native_unconnected':len(d['unconnected_items']),'native_violations':len(d['violations']),'parity':len(d['schematic_parity']),'power_losses':[{'net':x['net'],'width_mm':x['width_mm']} for x in r['power_width'] if x['status']!='PASS'],'lost_pad_connection_nets':[x['net'] for x in r['lost_pad_connections']],'retained_reference_losses':len(r['retained_trace_reference_loss']),'new_reference_gaps':sum(x.get('reference_uncovered_mm2_outside_existing_lands_and_own_transfers',0)>1e-6 for x in r['new_copper_review']),'adopted':rev=='R145I'})
dump(study/'summary.json',{'source_revision':'R144M','source_sha256':source_sha,'native_trial_count':8,'trials':rows,'R145G':'Read-only shortcut precheck rejected before a native candidate was built. The later runner reports missing plan; no G PCB exists.','accepted':'R145I','physical':'NOT_TESTED'})
dump(study/'archive_manifest.json',{'payloads':payloads,'scope':'Original payload bytes, or lossless deterministic gzip. The .state source folders remain intact.'})
verified=[]
for row in payloads:
 p=dev/'evidence'/row['path'];ok=sha(p)==row['sha256']
 if row['kind']=='gzip':ok &= hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==row['uncompressed_sha256']
 verified.append({'path':row['path'],'status':'PASS' if ok else 'FAIL'})
assert all(r['status']=='PASS' for r in verified)
dump(study/'archive_verification.json',{'status':'PASS','payload_count':len(verified),'results':verified})
# All source-input and acceptance guards above must pass before the one-board adoption.
assert sha(board)==source_sha and sha(candidate)==candidate_sha
board.write_bytes(candidate.read_bytes());assert sha(board)==candidate_sha
adoption={'adopted_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'from_revision':'R144M','source_sha256':source_sha,'to_revision':'R145I','board_sha256':candidate_sha,'only_native_board_replaced':True,'unchanged_original_nonpcb_members':77,'planned_delta_status':'PASS','planned_delta_checks':len(delta['checks']),'remaining_unconnected_items':28,'manufacturing_release':False,'goal_complete':False}
dump(ev/'adoption.json',adoption)
status=json.loads((dev/'STATUS.json').read_text());status.update(result)
status.update({'revision':'C3 R145I','previous_candidate':'C3 R144M','previous_candidate_sha256':source_sha,'strict_regression_explanation':'Raw audit retains FAIL for the explicit D1601/D301 transforms, one same-net source-via move, six replaced tracks and one removed obsolete ARMED via. Exact planned-delta review passes 2535 checks; connection, power, adjacency and reference regressions pass. This does not qualify the whole board or physical engineering.','planned_delta_check_count':len(delta['checks']),'local_visual_review':'PASS','local_visual_review_explanation':'Scoped D1601/ARMED/EN, D301 and source-via review; six local layers plus before/old-location images inspected. Full-board route, thermal, coupling and physical work remains.','segment_count':metrics['counts']['segments'],'via_count':metrics['counts']['vias'],'footprint_count':metrics['counts']['footprints'],'remaining_connectivity_fraction':.7,'remaining_D1601_K_groups':1,'remaining_ARMED_groups':len(metrics['net_groups']['/01 {slash} Core/ARMED'])})
dump(dev/'STATUS.json',status)
print(json.dumps({'adoption':adoption,'archived_payloads':len(verified)}))
