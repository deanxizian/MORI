"""Validate new study provenance, scope, current status and served local links."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from urllib.request import urlopen
import json,hashlib,platform
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
STOCK=A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock'
OUT=STOCK/'install_order/shell16_packing_diagnosis';STEP=STOCK/'PH_shell16_stepped_entry'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
pub=read(OUT/'publication.json');step=read(STEP/'verification.json')
assert pub['script_sha256']==sha(A8/'publish_shell16_packing_review.py')
assert pub['status']=='PASS' and pub['stepped_PH_rigid']=='PASS' and pub['stepped_PH_segments']==7
assert pub['stepped_PH_first5mm_leads']=='PASS' and pub['stepped_PH_lead_segments']==24
assert pub['stepped_PH_wires']=='NOT_TESTED' and pub['complete_attached_assembly']=='BLOCKED'
assert not pub['main_applied'] and not pub['manufacturing_release']
assert step['continuous_translation_segments']==7 and step['max_padded_overlap_after_initial_exception_mm3']==0.
assert step['initial_mating']=='NOT_TESTED' and step['exterior_upper_clearance_mm']>0.
assert len(step['deferred_wire_ids'])==10 and len(step['deferred_plugs'])==4
for group in ['source_files','protected_sources']:
    for name,h in pub[group].items():assert sha(ROOT/name)==h,name
for name,h in pub['outputs'].items():assert sha(OUT/name)==h,name
state=read(A8.parent/'work_status.json')
assert state['CAM_shell16_packing_diagnosis']['publication_sha256']==sha(OUT/'publication.json')
assert state['CAM_shell16_packing_diagnosis']['stepped_PH_rigid']=='PASS'
assert state['CAM_shell16_packing_diagnosis']['complete_attached_assembly']=='BLOCKED'
item=next(x for x in state['remaining'] if x['id']=='harness')
assert item['status']=='BLOCKED' and item['latest_packing_evidence'].endswith('/shell16_packing_diagnosis/index.html')
overview=read(A8/'supplier_source_update/verification.json')
assert overview['script_sha256']==sha(A8/'publish_supplier_source_update.py')
assert overview['shell16_packing_publication_sha256']==sha(OUT/'publication.json')
assert overview['shell16_stepped_PH_rigid']=='PASS' and overview['whole_harness']=='BLOCKED'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.items=[]
    def handle_starttag(self,tag,attrs):self.items += [v for k,v in attrs if k in ['href','src'] and v]
files={OUT/n for n in ['index.html','README.md','publication.json','local_pairs.png']}
files.update(STEP/n for n in ['screen.json','verification.json','projections.json','path.png','plot.json','exit_leads.json'])
files.update([A8/'supplier_source_update/index.html',A8/'supplier_source_update/verification.json'])
parser=Links();parser.feed((OUT/'index.html').read_text())
for item in parser.items:
    url=urlparse(item)
    if not url.scheme and not url.netloc and url.path:files.add((OUT/unquote(url.path)).resolve())
http=[]
for p in sorted(files):
    assert p.is_file(),p
    rel=str(p.relative_to(ROOT))
    with urlopen('http://127.0.0.1:58201/'+rel,timeout=20) as reply:
        assert reply.status==200;data=reply.read()
    assert hashlib.sha256(data).hexdigest()==sha(p),rel
    http.append(dict(path=rel,sha256=sha(p),status=200))
r=dict(status='PASS',scope='Published file identity and evidence boundaries; not physical assembly qualification',
    generated_utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(SCRIPT),
    publication_sha256=sha(OUT/'publication.json'),protected_sources=pub['protected_sources'],
    python_version=platform.python_version(),blender_version='5.2.2 LTS d13f752e3b9c',
    visual_review=dict(status='PASS',method='Assistant viewed both generated PNGs',files=['local_pairs.png','../../PH_shell16_stepped_entry/path.png']),
    http=http,stepped_PH_rigid='PASS',stepped_PH_segments=7,first5mm_leads='PASS',lead_segments=24,attached_CAM_wires='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='PASS',http_files=len(http),bare_PH_segments=7,attached_CAM='NOT_TESTED',whole_assembly='BLOCKED',main_unchanged=True)))
