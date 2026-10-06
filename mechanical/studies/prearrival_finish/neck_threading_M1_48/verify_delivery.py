"""Verify this study's sources, disclosures, links, and unchanged deliverables."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=json.loads((HERE/'source_audit.json').read_text())
pub=json.loads((HERE/'publication.json').read_text())
for p,h in audit['protected_sources'].items():assert sha(PROJECT/p)==h,p
hardware=json.loads((HERE.parent/'camera_cam_adoption/approval.json').read_text())['protected_hardware']
for p,h in hardware.items():assert sha(PROJECT/p)==h,p
for p,h in pub['files'].items():assert sha(HERE/p)==h,p
for p,d in pub['changed_presentation_files'].items():assert sha(PROJECT/p)==d['after'],p

static=json.loads((HERE/'outer_corridor_screen.json').read_text())
assert len(static['trials'])==456 and len(static['passing'])==72
latest=json.loads((HERE/'outer_corridor_motion_lowest.json').read_text())
assert latest['status']=='PASS' and latest['poses']==130 and not latest['failures']
assert latest['source_static_screen_sha256']==sha(HERE/'outer_corridor_screen.json')
assert latest['source_curve_sha256']==sha(HERE/'outer_corridor_curves.npz')
assert latest['script_sha256']==sha(HERE/'check_outer_corridor_motion.py')
for name,failures in [('outer_corridor_motion.json',91),('outer_corridor_motion_lower.json',89)]:
    d=json.loads((HERE/name).read_text())
    assert d['status']=='FAIL' and len(d['failures'])==failures
    assert d['source_static_screen_sha256']==sha(HERE/'outer_corridor_screen.json')
    assert d['source_curve_sha256']==sha(HERE/'outer_corridor_curves.npz')
    assert d['script_sha256']==sha(HERE/'check_outer_corridor_motion.py')
assert latest['whole_harness']=='BLOCKED' and latest['main_applied'] is False
for key in ['PCB_roots','upper_moving_loop','terminal_threading','unsampled_head_poses','retention_and_hands']:
    assert latest[key]=='NOT_TESTED',key

class Links(HTMLParser):
    def __init__(self):super().__init__();self.values=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ['href','src'] and v:self.values.append(v)

pages=[HERE/'index.html',HERE.parent/'index.html',PROJECT/'mechanical/index.html']
pages += [PROJECT/p for p in pub['changed_presentation_files'] if p.endswith('bridge_tail_order_review/index.html')]
checked=[]
for p in pages:
    parser=Links();parser.feed(p.read_text())
    for link in parser.values:
        u=urlsplit(link)
        if u.scheme or not u.path:continue
        target=(p.parent/unquote(u.path)).resolve()
        assert target.exists(),(p,link)
        checked.append(dict(page=str(p.relative_to(PROJECT)),link=link))
assert 'native-source-correction' in pages[-1].read_text()
assert '两端尚未接到PCB和头部服务环' in (HERE/'index.html').read_text()

# The published animation/STL/main sources need no rebuild for a diagnostic
# addendum. Compare their previous delivery hashes rather than implying a new
# complete build or a validated wire sequence.
old=json.loads((HERE.parent/'camera_cam_adoption/delivery.json').read_text())
unchanged=[]
for p,h in old['files'].items():
    if Path(p).suffix.lower() in ['.blend','.mp4','.stl']:
        assert sha(PROJECT/p)==h,p
        unchanged.append(p)
export_manifest=PROJECT/'mechanical/reports/export_manifest.json'
exported=json.loads(export_manifest.read_text())
assert exported['exported_count']==21
for part in exported['parts']:
    p=PROJECT/'mechanical'/part['file']
    assert sha(p)==part['sha256'],p
    unchanged.append(str(p.relative_to(PROJECT)))
http=[]
for rel in ['mechanical/studies/prearrival_finish/neck_threading_M1_48/index.html',
            'mechanical/studies/prearrival_finish/neck_threading_M1_48/bridge_comparison.png',
            'mechanical/studies/prearrival_finish/neck_threading_M1_48/outer_corridor.png',
            'mechanical/index.html?revision=V1.2-M1.48#camera-cam']:
    url='http://127.0.0.1:58201/'+rel
    with urlopen(Request(url,method='HEAD'),timeout=15) as r:
        assert r.status==200;http.append(dict(url=url,status=r.status))
result=dict(status='PASS',scope='Study publication and source integrity, not whole-harness completion',
    utc=datetime.now(timezone.utc).isoformat(),source_main_sha256=audit['source_main_sha256'],
    publication_sha256=sha(HERE/'publication.json'),verifier_sha256=sha(__file__),
    STL_export_manifest_sha256=sha(export_manifest),
    local_links_checked=len(checked),protected_hardware_files=len(hardware),
    unchanged_main_animation_STL=unchanged,http=http,whole_harness='BLOCKED',manufacturing_release=False)
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('NATIVE_NECK_DELIVERY',result['status'],'links',len(checked),'hardware',len(hardware),'unchanged_artifacts',len(unchanged),flush=True)
