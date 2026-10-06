"""Read back current body-split artifacts, protected inputs and local web assets."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote,quote
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,datetime,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=sha(M/'mori_v1_2.blend');cfg=read(ROOT/'config/geometry.json');rev=cfg['revision']
assert rev=='V1.2-M1.51'
prep=read(OUT/'preparation.json');protected={n:sha(ROOT/n)==h for n,h in prep['protected_hardware'].items()}
assert all(protected.values()),[n for n,v in protected.items() if not v]
ap=read(OUT/'approval.json');assert all(sha(ROOT/n)==h for n,h in ap['candidate_files'].items())
checks=read(OUT/'check.json');exports=read(M/'reports/export_manifest.json')
consistency=read(M/'reports/delivery_consistency.json');rebuild=read(M/'reports/rebuild_check.json')
validation=read(M/'reports/validation.json');engineering=read(OUT.parent/'engineering_current.json')
animation=read(M/'animation/manifest.json');av=read(M/'animation/validation.json');ad=read(M/'animation/delivery.json')
work=read(OUT.parent/'work_status.json');coupon=read(OUT/'fit_coupons/manifest.json');cr=read(OUT/'fit_coupons/readback.json')
assert all(x['status']=='PASS' for x in [checks,consistency,rebuild,engineering,av,coupon,cr])
assert validation['counts']['FAIL']==0
assert all(x['source_blend_sha256']==source for x in [checks,engineering,animation,ad,work,coupon,cr])
assert animation['animation_revision']==rev+'-A1' and animation['rendered_video']
assert sha(M/'animation/MORI_assembly.mp4')==animation['video']['sha256']==av['video']['sha256']
assert sha(M/'mori_assembly_animation.blend')==animation['animation_blend_sha256']
assert all(sha(M/n)==h for n,h in ad['files'].items())
assert sha(OUT/'fit_coupons'/coupon['editable']['file'])==coupon['editable']['sha256']==cr['editable_sha256']
assert all(sha(OUT/'fit_coupons'/p['file'])==p['sha256'] for p in coupon['parts'])
assert exports['exported_count']==21 and all(p['status']=='PASS' and sha(M/p['file'])==p['sha256'] for p in exports['parts'])
old=read(ROOT/prep['snapshot_root']/'mechanical/reports/export_manifest.json')
a={p['id']:p['sha256'] for p in old['parts']};b={p['id']:p['sha256'] for p in exports['parts']}
assert set(a)-set(b)=={'Body_Upper','Body_Lower'} and set(b)-set(a)=={'Body_Front','Body_Rear'}
assert len(set(a)&set(b))==19 and all(a[n]==b[n] for n in set(a)&set(b))
bom=read(M/'reports/bom.json');prints=[r['id'] for r in bom if r['category']=='PRINTABLE' and r['group'] not in ['dock','coupon']]
assert len(prints)==16 and len(read(M/'reports/build_manifest.json')['actuators'])==4
assert checks['scope']['unchanged']==199 and checks['scope']['changed']==[]
assert consistency['input_provenance_valid'] and consistency['all_render_hashes_match_final_model']
assert not work['manufacturing_release'] and work['status']=='BLOCKED'
pages=[M/'index.html',M/'animation/index.html',M/'parts.html',M/'manufacturing.html',OUT/'index.html',OUT/'fit_coupons/index.html']
class Page(HTMLParser):
 def __init__(self,text):super().__init__();self.links=[];self.ids=set();self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  for k in ['src','href','poster']:
   if k in a:self.links.append(a[k])
  if 'id' in a:self.ids.add(a['id'])
assets=set(pages);failures=[];external=[];fragments=0
for p in pages:
 for raw in Page(p.read_text()).links:
  u=urlsplit(raw)
  if u.scheme and (u.scheme not in ['http','https'] or u.netloc!='127.0.0.1:58201'):
   external.append(raw);continue
  local=unquote(u.path)
  target=(ROOT/local.lstrip('/') if local.startswith('/') else p.parent/local) if local else p
  target=target.resolve()
  if target.is_dir():target=target/'index.html'
  if not target.exists():failures.append(dict(page=str(p.relative_to(ROOT)),href=raw,problem='missing file'));continue
  assets.add(target)
  if u.fragment and target.suffix=='.html':
   fragments+=1
   if unquote(u.fragment) not in Page(target.read_text()).ids:failures.append(dict(page=str(p.relative_to(ROOT)),href=raw,problem='missing fragment'))
def head(p):
 try:
  url='http://127.0.0.1:58201/'+quote(str(p.relative_to(ROOT)))
  with urlopen(Request(url,method='HEAD'),timeout=15) as r:return dict(file=str(p.relative_to(ROOT)),status=r.status)
 except Exception as e:return dict(file=str(p),error=str(e))
with ThreadPoolExecutor(max_workers=4) as pool:http=list(pool.map(head,sorted(assets)))
for i,result in enumerate(http):
 if 'Errno 54' in result.get('error',''):
  retry=head(ROOT/result['file']);retry['initial_transient_error']=result['error'];http[i]=retry
failures += [x for x in http if x.get('status')!=200]
web=dict(status='FAIL' if failures else 'PASS',pages=[str(p.relative_to(ROOT)) for p in pages],local_assets=len(assets),fragments_checked=fragments,http=http,failures=failures,external_links_not_rechecked=sorted(set(external)))
(OUT/'web_check.json').write_text(json.dumps(web,ensure_ascii=False,indent=2)+'\n');assert not failures,failures
evidence=[M/'mori_v1_2.blend',M/'mori_assembly_animation.blend',M/'mori_electronics_detail.blend',
 M/'reports/validation.json',M/'reports/export_manifest.json',M/'reports/delivery_consistency.json',M/'reports/rebuild_check.json',
 M/'animation/manifest.json',M/'animation/validation.json',M/'animation/delivery.json',M/'animation/MORI_assembly.mp4',
 OUT/'check.json',OUT/'publication.json',OUT/'render_manifest.json',OUT/'web_check.json',
 OUT/'fit_coupons/manifest.json',OUT/'fit_coupons/readback.json',OUT.parent/'engineering_current.json',OUT.parent/'ENGINEERING.md',
 M/'reports/组装与打印.md',OUT.parent/'work_status.json']+pages
report=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision=rev,source_blend_sha256=source,
 scope='Current artifact consistency, digital geometry evidence and local page delivery; no manufacturing/physical qualification',
 protected_hardware_files=len(protected),protected_hardware_unchanged=True,robot_print_count=len(prints),exported_STL=21,unchanged_STL=19,
 unchanged_native_parts=199,removed_old_seam_hardware=8,validation_counts=validation['counts'],fresh_check_count=len(validation['current_rerun_ids']),
 animation_revision=animation['animation_revision'],video_seconds=animation['duration_seconds'],local_web_status=web['status'],
 full_harness='BLOCKED',physical_fit='NOT_TESTED',manufacturing_release=False,
 command=[sys.executable,str(Path(__file__))],files={str(p.relative_to(ROOT)):sha(p) for p in evidence})
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
audit=read(OUT.parent/'goal_block_audit.json');audit.update(main_revision=rev,source_blend_sha256=source,current_goal_turn_classification='progress',
 previous_progress='M1.51 body split delivered with current source, exports, path checks, animation, fit coupons and current instructions.',
 consecutive_impasse_turns=0,goal_status='active',completion_proven=False,next_action='Await the explicit C6 structural decision and continue remaining harness/interface work within its authorized scope.',
 last_revalidated_utc=report['utc'])
audit['live_state_checks'].update(main_matches_current_delivery=True,delivery_status='PASS',body_front_rear_approved=True)
audit['remaining_requirements'][0]['dependency']='C6/restraint choices, final horn and complete wired endpoints; adopted M1.51 body split is already delivered.'
(OUT.parent/'goal_block_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('M1_51_DELIVERY_PASS',len(assets),'local assets;',len(protected),'hardware files preserved',flush=True)
