"""Preserve the R143 studies without adopting any experimental PCB."""
import datetime,gzip,hashlib,json,subprocess
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=Path('robot/hardware/driver/development/evidence/R143_study');assert not out.exists();out.mkdir(parents=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
canonical=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');baseline=sha(canonical.read_bytes());assert baseline=='2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
rows=[]
def save(src,target,compress=None):
 data=src.read_bytes();compress=len(data)>131072 if compress is None else compress
 target=Path(str(target)+'.gz') if compress else Path(target);dest=out/target;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
 payload=gzip.compress(data,mtime=0) if compress else data;dest.write_bytes(payload)
 assert (gzip.decompress(dest.read_bytes()) if compress else dest.read_bytes())==data
 rows.append({'source':str(src),'stored_file':str(target),'encoding':'gzip' if compress else 'identity','uncompressed_bytes':len(data),'source_sha256':sha(data),'stored_sha256':sha(payload)})
save(b/'archive_R143.py',Path('construction')/'archive_R143.py')
for src in sorted(b.glob('R143*')):
 if src.is_file() and src.suffix in ['.json','.py','.log']:save(src,Path('reports')/src.name)
for name in ['R143-baseline-survey','R143-soft-obstacle-diagnostic','R143A-joint-search','R143B-joint-search','R143C-joint-search','R143D-joint-search','R143G-ground-search','R143G-ground-search-v2','R143-views','R143C-views','R143G-views']:
 for src in sorted((b/name).rglob('*')):
  if src.is_file():save(src,Path('reports')/name/src.relative_to(b/name),compress=src.suffix=='.svg' or src.stat().st_size>131072)
for name in ['R143-via-removal-checks','R143J-removal-proof']:
 for src in sorted((b/name).glob('*.json')):save(src,Path('verification')/name/src.name)
revisions=['R143A','R143B','R143C','R143D','R143G','R143J','R143K','R143M','R143N','R143O'];summary=[]
for rev in revisions:
 src=b/rev
 save(src/'MORI_Interface_C3.kicad_pcb',Path('boards')/(rev+'.kicad_pcb'),True)
 for name in ['MORI_Interface_C3.kicad_pro','edit_plan.json','edit_manifest.json']:save(src/name,Path('construction')/rev/name)
 a=json.loads((b/(rev+'-audit.json')).read_text());d=json.loads((b/(rev+'-drc.json')).read_text());assert a['board_sha256']==sha((src/'MORI_Interface_C3.kicad_pcb').read_bytes())
 summary.append({'revision':rev,'board_sha256':a['board_sha256'],'unconnected_items':len(d['unconnected_items']),'other_drc':len(d['violations']),'violation_types':[r['type'] for r in d['violations']],'schematic_parity':len(d['schematic_parity']),'lost_nets':[{ 'net':r['net'],'pad_pairs':len(r['lost_pad_pairs'])} for r in a['lost_pad_connections']],'power_width_failures':[{'net':r['net'],'width_mm':r['width_mm'],'lost_pairs':len(r['lost_pairs'])} for r in a['power_width'] if r['status']!='PASS'],'ground_group_sizes':list(map(len,a['GND_groups'])),'retained_reference_losses':len(a['retained_trace_reference_loss']),'new_reference_gaps':sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),'critical_placement_failures':sum(r['status']!='PASS' for r in a['critical_placement']),'historical_transition_flags':sum(r['status']=='FAIL' for r in a['reference_transitions']),'adopted':False})
(out/'summary.json').write_text(json.dumps({'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':'R142','source_sha256':baseline,'canonical_unchanged':sha(canonical.read_bytes())==baseline,'current_accepted_unconnected_items':29,'engineering_status':'FAIL','manufacturing_release':False,'goal_complete':False,'revisions':summary},indent=2,ensure_ascii=False)+'\n')
images=[]
for name,source,width in [('R143C-views/R1022-B.png','R143C',1000),('R143C-views/R1022-In4.png','R143C',1000),('R143G-views/CAM-In3.png','R143G',1800)]:
 p=b/name;images.append({'file':'reports/'+name,'sha256':sha(p.read_bytes()),'board_sha256':sha((b/source/'MORI_Interface_C3.kicad_pcb').read_bytes()),'actually_viewed':True,'kind':'Native-geometry diagnostic, not screenshot or manufacturing data','raster_width':width,'whole_board_review':'NOT_TESTED'})
(out/'visual_inspection.json').write_text(json.dumps({'scope':'Only these three newly rendered diagnostic PNGs were inspected in this goal turn; earlier R143 images retain their prior provenance. No board-wide PASS.','images':images},indent=2)+'\n')
(out/'archive_manifest.json').write_text(json.dumps({'scope':__doc__,'canonical_sha256':baseline,'payload_count':len(rows),'payloads':rows,'original_logs_preserved':True},indent=2)+'\n')
print(json.dumps({'payloads':len(rows),'boards':len(revisions),'canonical_unchanged':True,'native_summary':[(r['revision'],r['unconnected_items'],r['other_drc']) for r in summary]}))
