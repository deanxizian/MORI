"""Check report links and unchanged native/hardware deliverables."""
from pathlib import Path
import json,hashlib,datetime,sys,urllib.parse,urllib.request
from html.parser import HTMLParser
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
approval=json.loads((BASE/'camera_cam_adoption/approval.json').read_text())
baseline=json.loads((BASE/'camera_cam_adoption/delivery.json').read_text())
previous=json.loads((BASE/'cam_retention_M1_48/delivery.json').read_text())
hardware=approval['protected_hardware'];errors=[]
for f,digest in hardware.items():
    if not (ROOT/f).exists() or sha(ROOT/f)!=digest:errors.append('Protected hardware changed: '+f)
exports=json.loads((ROOT/'mechanical/reports/export_manifest.json').read_text())
animation=json.loads((ROOT/'mechanical/animation/manifest.json').read_text())
expected_files={f:h for f,h in baseline['files'].items() if Path(f).suffix.lower() in ['.blend','.mp4','.stl']}
expected_files.update({'mechanical/'+r['file']:r['sha256'] for r in exports['parts']})
expected_files['mechanical/animation/'+animation['video']['file']]=animation['video']['sha256']
assert exports['exported_count']==21 and animation['animation_revision']=='V1.2-M1.48-A1'
native_files=previous['unchanged_main_animation_STL'];native_hashes={}
for f in native_files:
    expected=expected_files.get(f)
    if expected is None:errors.append('Missing baseline: '+f);continue
    actual=sha(ROOT/f);native_hashes[f]=actual
    if actual!=expected:errors.append('Native delivery changed: '+f)
assert len([f for f in native_hashes if f.endswith('.stl')])==21

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for k in ('href','src'):
            if k in a:self.links.append(a[k])
checked=[]
pages=[HERE/'index.html',BASE/'index.html',BASE/'yaw_service_M1_48/index.html',BASE/'cam_retention_M1_48/index.html']
for p in pages:
    parsed=Links();parsed.feed(p.read_text())
    for u in parsed.links:
        url=urllib.parse.urlsplit(u)
        if url.scheme or not url.path:continue
        target=(p.parent/urllib.parse.unquote(url.path)).resolve()
        if target==HERE/'delivery.json':continue
        checked.append(str(target.relative_to(ROOT)))
        if not target.is_file():errors.append('Missing local link: '+str(target))

reports=['packing.json','host_cuts.json','section_checks.json','section_checks_four_line.json','outside_bearing_screen.json','review.json']
for name in reports:
    r=json.loads((HERE/name).read_text())
    if r['source_main_sha256']!=native_hashes['mechanical/mori_v1_2.blend']:errors.append('Wrong main provenance: '+name)
    if r.get('main_applied',False):errors.append('Unexpected application claim: '+name)
http={}
for rel in ['index.html','socket_comparison.png','section_checks.json']:
    url='http://127.0.0.1:58201/mechanical/studies/prearrival_finish/whole_head_harness_M1_48/'+rel
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as response:
        http[rel]=response.status
        if response.status!=200:errors.append('HTTP error: '+rel)

files={str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['delivery.json','verify_delivery.log']}
out=dict(status='FAIL' if errors else 'PASS',scope='Source integrity and presentation delivery only; routing/design still BLOCKED',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),script_sha256=sha(__file__),
    source_main_sha256=native_hashes['mechanical/mori_v1_2.blend'],revision='V1.2-M1.48',animation_revision='V1.2-M1.48-A1',
    tools={'report_python':sys.version,'geometry_blender':'5.2.2 LTS d13f752e3b9c'},
    checked_hardware_files=len(hardware),unchanged_native_files=native_hashes,
    source_manifest_hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'mechanical/reports/export_manifest.json',ROOT/'mechanical/animation/manifest.json',BASE/'camera_cam_adoption/delivery.json']},
    local_links_checked=len(checked),http=http,files=files,errors=errors,
    visual_review='socket_comparison.png inspected; actual native/candidate sections, no generated illustrative geometry',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(HERE/'delivery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['status','scope','checked_hardware_files','local_links_checked','http','errors']},ensure_ascii=False))
assert not errors
