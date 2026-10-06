"""Verify current sources, the narrow pass scope, and published local assets."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json,hashlib
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
pub=load(HERE/'publication.json')
for p,h in pub['native_sources'].items():assert sha(PROJECT/p)==h,p
for p,h in pub['files'].items():assert sha(HERE/p)==h,p
for p,r in pub['changed_presentation_files'].items():assert sha(PROJECT/p)==r['after'],p
hardware=load(HERE.parent/'camera_cam_adoption/approval.json')['protected_hardware']
for p,h in hardware.items():assert sha(PROJECT/p)==h,p

packing=load(HERE/'packing.json');v=load(HERE/'verification.json')
assert packing['status']==v['status']=='PASS'
assert len(packing['selected'])==4 and len(packing['selected_pairs'])==6
assert len(v['poses'])==130 and not v['failed_poses']
assert v['zero_pose_target_count']==252 and all(r['status']=='PASS' for r in v['zero_pose_checks'])
assert v['script_sha256']==sha(HERE/'verify_packed.py')
assert v['selection_sha256']==sha(HERE/'packing.json')
assert v['selected_curves_sha256']==sha(HERE/'packed_curves.npz')
assert packing['source_pools_sha256']==sha(HERE/'body_prefix_pools.json')
assert packing['source_curves_sha256']==sha(HERE/'body_prefix_curves.npz')
assert min(r['surface_gap_lower_bound_mm'] for r in packing['selected_pairs'])>=.3
assert all(r['minimum_three_point_radius_mm']>=6.9342 for r in v['zero_pose_checks'])
assert v['main_applied'] is False and v['whole_harness']=='BLOCKED'
assert v['assembly']==v['upper_service_loop']=='NOT_TESTED'
for name in ['outer_risers.json','outer_risers_R8.json','outer_risers_R10.json']:
    d=load(HERE/name)
    assert d['status']=='BLOCKED' and not d['motion_survivors']
    assert d['script_sha256']==sha(HERE/'screen_outer_risers.py')

old=load(HERE.parent/'camera_cam_adoption/delivery.json')
unchanged=[]
for p,h in old['files'].items():
    if Path(p).suffix.lower() in ['.blend','.mp4','.stl']:
        assert sha(PROJECT/p)==h,p;unchanged.append(p)
manifest=PROJECT/'mechanical/reports/export_manifest.json'
export=load(manifest);assert export['exported_count']==21
for r in export['parts']:
    p=PROJECT/'mechanical'/r['file'];assert sha(p)==r['sha256'],p
    unchanged.append(str(p.relative_to(PROJECT)))

class Links(HTMLParser):
    def __init__(self):super().__init__();self.values=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ['href','src'] and value:self.values.append(value)
pages=[HERE/'index.html']+[PROJECT/p for p in pub['changed_presentation_files'] if p.endswith('.html')]
links=[]
for p in pages:
    parser=Links();parser.feed(p.read_text())
    for link in parser.values:
        u=urlsplit(link)
        if u.scheme or not u.path:continue
        target=(p.parent/unquote(u.path)).resolve()
        if target==HERE/'delivery.json':continue
        assert target.exists(),(p,link)
        links.append(dict(page=str(p.relative_to(PROJECT)),link=link))
assert '表中不是裁线尺寸' in (HERE/'index.html').read_text()
assert '完整线束与带线装配仍未完成' in (HERE/'index.html').read_text()
http=[]
for name in ['index.html','body_routes.png','routes_plan.png','neck_connection.png','review.blend']:
    url='http://127.0.0.1:58201/'+str((HERE/name).relative_to(PROJECT))
    with urlopen(Request(url,method='HEAD'),timeout=15) as response:
        assert response.status==200
        http.append(dict(url=url,status=response.status,content_length=response.headers.get('Content-Length')))
result=dict(status='PASS',scope='Study delivery and immutable main/hardware check; full harness still incomplete',
    utc=datetime.now(timezone.utc).isoformat(),source_main_sha256=v['source_main_sha256'],
    script_sha256=sha(__file__),publication_sha256=sha(HERE/'publication.json'),
    local_links_checked=len(links),protected_hardware_files=len(hardware),
    unchanged_main_animation_STL=sorted(set(unchanged)),http=http,
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False)
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('OUTER_HARNESS_DELIVERY',result['status'],'links',len(links),'hardware',len(hardware),
      'unchanged_artifacts',len(result['unchanged_main_animation_STL']),flush=True)
