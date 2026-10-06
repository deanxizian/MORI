"""Verify this documentation-only addition and refresh only its changed files."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
from urllib.request import urlopen
from datetime import datetime, timezone
import hashlib, json, sys, platform
import OCP, matplotlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PARENT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
assert sha(ROOT/'mechanical/mori_v1_2.blend')==expected
assert sha(PARENT/'head_harness/HEAD_HARNESS_REQUIREMENTS.md')=='caf8ede21503dc5f60b439ecc1ac60545a0b814e4e934ce82745f6d91d64e7be'
assert sha(HERE/'sources/SCS0009_A0_mirror.pdf')==sha(ROOT/'mechanical/sources/v1_2/scs0009_spec.pdf')
step=json.loads((HERE/'servo_step_inspection.json').read_text())
assert len(step['parts_local_coordinates'])==4 and all(x['valid'] for x in step['parts_local_coordinates'])
assert step['matching_horn_included'] is False
assert step['source_sha256']==sha(HERE/'sources/SCS009-20230110-S.stp')
assert 'USER_CONFIRMED_SUPPLIER_MADE' in json.loads((PARENT/'work_status.json').read_text())['prearrival_wire_addendum']['harness_build_method']

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for k in ['href','src']:
            if a.get(k):self.links.append(a[k])
local=[]
for page in [HERE/'index.html',PARENT/'index.html',PARENT/'head_harness/index.html']:
    parser=Links();parser.feed(page.read_text())
    for href in parser.links:
        u=urlparse(href)
        if u.scheme or u.netloc or not u.path:continue
        target=(page.parent/unquote(u.path)).resolve()
        assert target.exists(),(page,href)
        local.append({'page':str(page.relative_to(ROOT)),'href':href,'status':'PASS'})

changed={str((PARENT/x).relative_to(ROOT)) for x in [
    'work_status.json','index.html','SUPPLIER_DATA_REQUEST.md',
    'head_harness/index.html','head_harness/publish_head_review.py',
    'harness_A2/assembly_screen_review.html','harness_A2/publish_assembly_safe.py']}
refreshed=[]
for rel in ['M1_47_delivery.json','harness_A2/delivery.json','head_harness/delivery.json']:
    p=PARENT/rel;d=json.loads(p.read_text());updates=[]
    for name,digest in d['files'].items():
        current=sha(ROOT/name)
        if current!=digest:
            assert name in changed,('Unexpected changed file',name)
            d['files'][name]=current;updates.append(name)
    if updates:
        d['supplier_made_harness_document_update']={'utc':datetime.now(timezone.utc).isoformat(),'scope':'Decision/source documentation only. Prior geometry checks not rerun or relabelled.','updated_paths':updates,'review':'supplier_made_harness/index.html'}
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    refreshed.append({'manifest':str(p.relative_to(ROOT)),'updated_count':len(updates)})

url='http://127.0.0.1:58201/mechanical/studies/prearrival_finish/supplier_made_harness/index.html'
try:
    with urlopen(url,timeout=10) as r:b=r.read();http={'status':r.status,'matches_saved_file':hashlib.sha256(b).hexdigest()==sha(HERE/'index.html')}
except Exception as e:http={'status':'NOT_TESTED','reason':str(e)}
result={'status':'PASS','scope':'Source collection, decision and document consistency; not complete robot design qualification','verified_utc':datetime.now(timezone.utc).isoformat(),'main_model_unchanged':True,'source_main_sha256':expected,'received_hardware_requirements_unchanged':True,'harness_build_method':'USER_CONFIRMED_SUPPLIER_MADE_TO_DRAWING','servo_reference':{'part_class':'PURCHASED_REFERENCE','evidence_status':'ASSUMED','source_validation':'PASS','exact_purchased_revision_match':'BLOCKED','matching_horn_included':False},'final_harness_drawing':'BLOCKED','manufacturing_release':'BLOCKED','local_links':local,'http':http,'updated_manifests':refreshed,'versions':{'python':platform.python_version(),'OCP':getattr(OCP,'__version__','unknown'),'matplotlib':matplotlib.__version__},'commands':['/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/supplier_made_harness/fetch_sources.py','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/supplier_made_harness/inspect_servo_step.py','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/supplier_made_harness/render_servo_reference.py','pdftoppm -f 1 -singlefile -scale-to 1800 -png sources/JST_GAM-050.pdf JST_GAM-050','/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/studies/prearrival_finish/supplier_made_harness/verify_delivery.py']}
files=[p for p in HERE.rglob('*') if p.is_file() and p.name!='delivery.json' and '__pycache__' not in p.parts]
files += [PARENT/'work_status.json',ROOT/'AGENTS.md']
result['files']={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','local_links':len(local),'files':len(result['files']),'http':http,'main_unchanged':True,'manifests':refreshed},ensure_ascii=False))
