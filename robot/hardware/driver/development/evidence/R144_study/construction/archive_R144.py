"""Archive actual R144 studies and the separately accepted R144M evidence.

No source or trial board is altered. Payloads are byte-preserved or losslessly
compressed, with round-trip hashes. R144M adoption happens only after this and
the exact-delta, electrical and scoped visual checks have passed.
"""
import copy, csv, datetime, gzip, hashlib, json, shutil
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
dev=Path('robot/hardware/driver/development')
study=dev/'evidence/R144_study'; accepted=dev/'evidence/R144M'
assert not study.exists() and not accepted.exists()
study.mkdir(); accepted.mkdir()
sha=lambda data:hashlib.sha256(data).hexdigest()
source=dev/'native/MORI_Interface_C3.kicad_pcb'
source_sha=sha(source.read_bytes())
assert source_sha=='2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
candidate=b/'R144M/MORI_Interface_C3.kicad_pcb';candidate_sha=sha(candidate.read_bytes())
assert candidate_sha=='f783cf5dfad0ff8020aac8906f12dd018287af6a6d548600d4776fb3603225a5'
proof=json.loads((b/'R144M-planned-delta.json').read_text())
assert proof['status']=='PASS' and not proof['errors']
manifests={study:[],accepted:[]}
def save(root,src,rel,compress=None):
 data=src.read_bytes();compress=(len(data)>131072 or src.suffix=='.svg') if compress is None else compress
 rel=Path(str(rel)+'.gz') if compress else Path(rel);dest=root/rel
 assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
 payload=gzip.compress(data,mtime=0) if compress else data;dest.write_bytes(payload)
 assert (gzip.decompress(dest.read_bytes()) if compress else dest.read_bytes())==data
 manifests[root].append({'source':str(src),'stored_file':str(rel),'encoding':'gzip' if compress else 'identity','uncompressed_bytes':len(data),'source_sha256':sha(data),'stored_sha256':sha(payload)})
revs=['R144A','R144B','R144C','R144D','R144E','R144F','R144H','R144I','R144J','R144K','R144L','R144M']
summary=[]
for rev in revs:
 a=json.loads((b/(rev+'-audit.json')).read_text());d=json.loads((b/(rev+'-drc.json')).read_text())
 assert a['board_sha256']==sha((b/rev/'MORI_Interface_C3.kicad_pcb').read_bytes())
 summary.append({'revision':rev,'board_sha256':a['board_sha256'],'unconnected_items':len(d['unconnected_items']),'other_drc':len(d['violations']),'schematic_parity':len(d['schematic_parity']),'violation_types':[r['type'] for r in d['violations']],'power_width_failures':[{'net':r['net'],'width_mm':r['width_mm'],'lost_pairs':len(r['lost_pairs'])} for r in a['power_width'] if r['status']=='FAIL'],'lost_nets':[{'net':r['net'],'lost_pad_pairs':len(r['lost_pad_pairs'])} for r in a['lost_pad_connections']],'ground_group_sizes':list(map(len,a['GND_groups'])),'critical_placement_failures':sum(r['status']=='FAIL' for r in a['critical_placement']),'retained_reference_losses':len(a['retained_trace_reference_loss']),'new_reference_gaps':sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),'historical_transition_flags':sum(r['status']=='FAIL' for r in a['reference_transitions']),'adoption_decision':'accepted development candidate after separate scoped review' if rev=='R144M' else 'not adopted'})
 save(study,b/rev/'MORI_Interface_C3.kicad_pcb',Path('boards')/(rev+'.kicad_pcb'),True)
 for name in ['MORI_Interface_C3.kicad_pro','edit_plan.json','edit_manifest.json']:
  save(study,b/rev/name,Path('construction')/rev/name,False)
for src in sorted(b.glob('R144*')):
 if src.is_file() and src.suffix in ['.json','.py','.log']:save(study,src,Path('reports')/src.name)
for name in ['R144-views','R144H-views','R144M-views','R144B-joint-search','R144I-joint-search','R144J-joint-search','R144H-verify','R144K-verify']:
 for src in sorted((b/name).rglob('*')):
  if src.is_file():save(study,src,Path('reports')/name/src.relative_to(b/name))
for name in ['archive_R144.py','run_R138_trial.py','R138_joint_search.py']:
 save(study,b/name,Path('construction')/name,False)
(study/'summary.json').write_text(json.dumps({'source_revision':'R142','source_sha256':source_sha,'accepted_revision':'R144M','accepted_board_sha256':candidate_sha,'remaining_unconnected_items':29,'manufacturing_release':False,'engineering_status':'FAIL','goal_complete':False,'revisions':summary},indent=2)+'\n')
# Source members include only project inputs, not KiCad's ignored session state.
members=[p for p in (dev/'native').rglob('*') if p.is_file() and p.suffix not in ['.kicad_pcb','.kicad_prl']]
assert len(members)==77
checks=[]
for rev in revs:
 diffs=[]
 for p in members:
  rel=p.relative_to(dev/'native');q=b/rev/rel
  if p.read_bytes()==q.read_bytes():continue
  assert rel.name=='MORI_Interface_C3.kicad_pro'
  expected=json.loads(p.read_text())
  for x in expected['board']['design_settings']['teardrop_parameters']:x.setdefault('td_enabled',False)
  for key in ['net_colors','netclass_assignments']:
   if expected['net_settings'][key] is None:expected['net_settings'][key]={}
  assert json.loads(q.read_text())==expected
  diffs.append({'path':str(rel),'reason':'Only recognized KiCad default-value normalization','source_sha256':sha(p.read_bytes()),'candidate_sha256':sha(q.read_bytes())})
 checks.append({'revision':rev,'checked_original_member_count':77,'recognized_normalizations':diffs,'status':'PASS'})
(study/'project_member_verification.json').write_text(json.dumps({'source_sha256':source_sha,'scope':'All 77 original non-PCB project inputs; ignored .kicad_prl excluded and preserved locally','revisions':checks},indent=2)+'\n')
for src in sorted((b/'R144M-verify').glob('*')):
 if src.is_file():save(accepted,src,src.name,False)
for src,name in [(b/'R144M-plan.json','plan.json'),(b/'R144M-planned-delta.json','planned-delta.json'),(b/'R144M-local-metrics.json','local-metrics.json'),(b/'R144M-commands.json','construction-commands.json'),(b/'R144M/edit_manifest.json','edit_manifest.json')]:save(accepted,src,name,False)
save(accepted,source,'source-R142.kicad_pcb',True)
for name in ['R142-B.Cu','R144M-B.Cu','R144M-F.Cu','R144M-In4.Cu']:
 for ext in ['.svg','.png']:save(accepted,b/'R144M-views'/(name+ext),Path('images')/(name+ext),False)
d=json.loads((accepted/'drc.json').read_text())
with (accepted/'remaining_connections.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['item','description','endpoint_descriptions'])
 for i,r in enumerate(d['unconnected_items'],1):w.writerow([i,r['description'],' | '.join(x['description'] for x in r['items'])])
for root,rows in manifests.items():
 (root/'archive_manifest.json').write_text(json.dumps({'scope':__doc__,'payload_count':len(rows),'payloads':rows},indent=2)+'\n')
 for r in rows:
  data=(root/r['stored_file']).read_bytes();assert sha(data)==r['stored_sha256']
  if r['encoding']=='gzip':data=gzip.decompress(data)
  assert sha(data)==r['source_sha256'] and len(data)==r['uncompressed_bytes']
 (root/'archive_verification.json').write_text(json.dumps({'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload_count':len(rows),'status':'PASS','all_stored_hashes_and_decoded_source_hashes_match':True},indent=2)+'\n')
assert sha(source.read_bytes())==source_sha
print(json.dumps({'boards':len(revs),'study_payloads':len(manifests[study]),'accepted_payloads':len(manifests[accepted]),'source_unchanged':True}))
