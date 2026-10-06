"""Evidence/link checks plus unchanged production and hardware hashes."""
from pathlib import Path
from html.parser import HTMLParser
import json,hashlib,urllib.request,urllib.parse,datetime,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
approval=load(BASE/'camera_cam_adoption/approval.json')
baseline=load(BASE/'camera_cam_adoption/delivery.json')
exports=load(ROOT/'mechanical/reports/export_manifest.json')
animation=load(ROOT/'mechanical/animation/manifest.json')
expected={f:h for f,h in baseline['files'].items() if Path(f).suffix=='.blend'}
expected.update({'mechanical/'+r['file']:r['sha256'] for r in exports['parts']})
expected['mechanical/animation/'+animation['video']['file']]=animation['video']['sha256']
assert exports['exported_count']==21 and animation['animation_revision']=='V1.2-M1.48-A1'
errors=[];native={}
for f,digest in expected.items():
    actual=sha(ROOT/f);native[f]=actual
    if actual!=digest:errors.append('Native delivery changed: '+f)
for f,digest in approval['protected_hardware'].items():
    if not (ROOT/f).exists() or sha(ROOT/f)!=digest:errors.append('Protected hardware differs: '+f)
for name in ['C1_build.json','C2_build.json','C2_verification.json','packing.json','posed_sections.json','review.json']:
    r=load(HERE/name)
    if r['source_main_sha256']!=native['mechanical/mori_v1_2.blend']:errors.append('Source mismatch: '+name)
    if r.get('main_applied',False):errors.append('Unexpected adoption: '+name)
build=load(HERE/'C2_build.json')
for p,h in build['sources'].items():
    if sha(ROOT/p)!=h:errors.append('Input changed: '+p)
verify=load(HERE/'C2_verification.json')
assert verify['status']=='BLOCKED' and verify['new_overlaps']
assert build['status']=='PASS' and not build['wire_hits']
assert verify['build_sha256']==sha(HERE/'C2_build.json')
assert verify['script_sha256']==sha(HERE/'verify_candidate.py')
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,t,a):
        a=dict(a)
        self.links.extend(a[k] for k in ['src','href'] if k in a)
checked=[]
for p in [HERE/'index.html',BASE/'index.html',BASE/'whole_head_harness_M1_48/index.html']:
    parser=Links();parser.feed(p.read_text())
    for u in parser.links:
        split=urllib.parse.urlsplit(u)
        if split.scheme or not split.path:continue
        target=(p.parent/urllib.parse.unquote(split.path)).resolve()
        if target==HERE/'delivery.json':continue
        checked.append(str(target.relative_to(ROOT)))
        if not target.is_file():errors.append('Missing linked file: '+str(target))
http={}
for name in ['index.html','head_motion_sections.png','local_sections.png','C2_verification.json']:
    url='http://127.0.0.1:58201/mechanical/studies/prearrival_finish/neck_bearing_capacity_M1_48/'+name
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as r:http[name]=r.status
        if http[name]!=200:errors.append('HTTP error: '+name)
    except Exception as exc:errors.append('HTTP '+name+': '+str(exc))
out=dict(status='PASS' if not errors else 'FAIL',
    scope='Delivery and source integrity only; proposed neck design and full harness remain BLOCKED',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_main_sha256=native['mechanical/mori_v1_2.blend'],
    revision='V1.2-M1.48',animation_revision=animation['animation_revision'],
    checked_hardware_files=len(approval['protected_hardware']),unchanged_native_files=native,
    local_links_checked=len(checked),http=http,
    visual_review='Both generated PNGs inspected: actual posed solid intersections and local source sections; orange circles mark wireOD at sampled centers.',
    tools=dict(report_python=sys.version,Blender='5.2.2 LTS d13f752e3b9c'),
    files={str(p.relative_to(ROOT)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.name not in ['delivery.json','verify_delivery.log'] and '__pycache__' not in p.parts},
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,errors=errors)
(HERE/'delivery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','checked_hardware_files','local_links_checked','http','errors']},ensure_ascii=False))
assert not errors
