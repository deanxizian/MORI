"""Check published evidence, links and unchanged robot/hardware artifacts."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib, json
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
pub=load(HERE/'publication.json')
for p,h in pub['files'].items():assert sha(HERE/p)==h,p
for p,h in pub['native_sources'].items():assert sha(PROJECT/p)==h,p
for p,r in pub['changed_presentation_files'].items():assert sha(PROJECT/p)==r['after'],p
for report,script in [('anchors.json','check_anchors.py'),('material_stations.json','check_material_stations.py'),('tools_and_tail.json','check_tool_routes.py'),('neck_feed_verified.json','verify_neck_feed.py'),('board_installation.json','check_board_installation.py')]:
    d=load(HERE/report);assert d['status']=='PASS' and not d['main_applied'] and d['whole_harness']=='BLOCKED'
    assert d['script_sha256']==sha(HERE/script) and d['context_sha256']==sha(HERE/'current_context.py')
    assert d['source_main_sha256']==pub['source_main_sha256']
    for p,h in d['explicit_inputs'].items():assert sha(PROJECT/p)==h,p
anchors=load(HERE/'anchors.json');stations=load(HERE/'material_stations.json');feed=load(HERE/'neck_feed_verified.json');board=load(HERE/'board_installation.json')
assert len(anchors['poses'])==130 and anchors['wire_tests']==3120 and not anchors['wire_hits']
assert len(stations['stations'])==24 and all(r['status']=='PASS' and len(r['samples'])==130 for r in stations['stations'])
assert feed['clearance_requirement_mm']==.3 and min(feed['terminal_gap_lower_bound_mm'],feed['wire_gap_lower_bound_mm'])>.3
assert len(feed['rows'])==8 and all(r['status']=='PASS' and r['spans']==410 for r in feed['rows'])
assert len(feed['pairs'])==6 and all(r['status']=='PASS' for r in feed['pairs'])
assert len(board['rows'])==16 and all(r['status']=='PASS' and not r['wire_hits'] and not r['rigid_hits'] for r in board['rows'])
assert all(r['status']=='PASS' for r in board['rigid_sweeps'])
assert board['curve_cache_sha256']==sha(HERE/'board_installation_curves.npz')
status=load(HERE.parent/'work_status.json')
assert status['revision']=='V1.2-M1.48' and len([r for r in status['remaining'] if r['id']!='physical_validation'])==5
assert not status['camera_top_clearance_candidate']['pending_user_adoption']
hardware=load(HERE.parent/'camera_cam_adoption/approval.json')['protected_hardware']
for p,h in hardware.items():assert sha(PROJECT/p)==h,p
baseline=load(HERE.parent/'camera_cam_adoption/delivery.json');unchanged=[]
for p,h in baseline['files'].items():
    if Path(p).suffix.lower() in ['.blend','.mp4','.stl']:
        assert sha(PROJECT/p)==h,p
        unchanged.append(p)
exports=load(PROJECT/'mechanical/reports/export_manifest.json');assert exports['exported_count']==21
for row in exports['parts']:
    path=PROJECT/'mechanical'/row['file'];assert sha(path)==row['sha256'],str(path)
    unchanged.append(str(path.relative_to(PROJECT)))
animation=load(PROJECT/'mechanical/animation/manifest.json')
assert animation['animation_revision']=='V1.2-M1.48-A1' and animation['source_blend_sha256']==pub['source_main_sha256']
video=PROJECT/'mechanical/animation'/animation['video']['file'];assert sha(video)==animation['video']['sha256']
unchanged.append(str(video.relative_to(PROJECT)))

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):self.links.extend(v for k,v in attrs if k in ['href','src'] and v)
link_count=0
for page in [HERE/'index.html']+[PROJECT/p for p in pub['changed_presentation_files'] if p.endswith('.html')]:
    parser=Links();parser.feed(page.read_text())
    for link in parser.links:
        url=urlsplit(link)
        if url.scheme or not url.path:continue
        path=(page.parent/unquote(url.path)).resolve()
        if path==HERE/'delivery.json':continue
        assert path.exists(),(str(page),link)
        link_count+=1
http=[]
for name in ['index.html','anchors_front.png','anchors_rear.png','tail_workspace.png','review.blend']:
    url='http://127.0.0.1:58201/'+str((HERE/name).relative_to(PROJECT))
    with urlopen(Request(url,method='HEAD'),timeout=10) as response:
        assert response.status==200
        http.append(dict(url=url,status=response.status))
report=dict(status='PASS',scope='Published partial candidate evidence; robot, exports, animation and hardware preserved',
    utc=datetime.now(timezone.utc).isoformat(),script_sha256=sha(__file__),publication_sha256=sha(HERE/'publication.json'),
    source_main_sha256=pub['source_main_sha256'],local_links_checked=link_count,protected_hardware_files=len(hardware),
    unchanged_main_animation_STL=sorted(set(unchanged)),http=http,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(HERE/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_RETENTION_DELIVERY',report['status'],'hardware',len(hardware),'links',link_count,flush=True)
