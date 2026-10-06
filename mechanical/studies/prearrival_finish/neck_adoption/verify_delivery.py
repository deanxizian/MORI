"""Current local file/HTTP verification after publishing C5 + K1."""
import datetime,hashlib,json,urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
OUT=Path(__file__).resolve().parent;M=OUT.parents[2];P=M.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
current=sha(M/'mori_v1_2.blend');rev=read(P/'config/geometry.json')['revision']
assert rev=='V1.2-M1.49'
audit=read(M/'reports/neck_capacity_validation.json')
pub=read(OUT/'publication.json');anim=read(M/'animation/manifest.json')
coupon=read(OUT/'fit_coupons/manifest.json')
assert all(d['source_blend_sha256']==current for d in [audit,pub,anim,coupon])
assert audit['status']=='PASS' and audit['scope']['unchanged_count']==201
assert read(M/'reports/validation.json')['counts']['FAIL']==0
assert read(M/'reports/rebuild_check.json')['status']=='PASS'
assert read(M/'reports/head_axial_retention_validation.json')['pilot_status']
exports=read(M/'reports/export_manifest.json')
assert exports['candidate_count']==exports['exported_count']==21
assert all(r['status']=='PASS' and sha(M/r['file'])==r['sha256'] for r in exports['parts'])
assert coupon['status']=='PASS' and len(coupon['parts'])==2
assert all(sha(P/r['file'])==r['sha256'] for r in coupon['parts'])
assert read(M/'reports/delivery_consistency.json')['status']=='PASS'
assert read(M/'animation/validation.json')['status']=='PASS' and anim['rendered_video']
ad=read(M/'animation/delivery.json')
assert ad['source_blend_sha256']==current and all(sha(M/f)==h for f,h in ad['files'].items())
assert all(sha(P/p)==v for p,v in read(M/'reports/build_manifest.json')['input_sha256'].items())
protected=read(OUT/'approval.json')['protected_hardware']
assert all(sha(P/p)==h for p,h in protected.items())
k1=read(OUT/'keeper_wall_approval.json')
assert sha(OUT/'keeper_wall_verification.json')==k1['verification_sha256']
assert all(sha(OUT/('round_'+n+'.npz'))==h for n,h in k1['source_geometry'].items())
classification=read(M/'reports/manufacturing_classification.json')
assert classification['counts']['robot_print']==16
work=read(OUT.parent/'work_status.json')
assert work['neck_adoption']['source_blend_sha256']==current
assert next(r for r in work['remaining'] if r['id']=='harness')['status']=='BLOCKED'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ['href','src','poster'] and v:self.links.append(v)
pages=[M/'index.html',M/'parts.html',M/'manufacturing.html',M/'animation/index.html',OUT/'index.html',OUT/'keeper_wall_index.html',OUT/'fit_coupons/index.html']
links=set();missing=[]
for page in pages:
    p=Links();p.feed(page.read_text())
    for link in p.links:
        u=urlsplit(link)
        if u.scheme or u.netloc or not u.path:continue
        target=(page.parent/unquote(u.path)).resolve()
        if not target.is_file():missing.append({'page':str(page),'link':link})
        else:links.add(target)
assert not missing,missing
http=[]
for path in sorted(set(pages)|{M/'reports/neck_capacity_validation.json',OUT/'supports.png',OUT/'keeper_wall_comparison.png',OUT/'fit_coupons/overview.png',M/'animation/MORI_assembly.mp4'}):
    url='http://127.0.0.1:58201/'+path.relative_to(P).as_posix()
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as response:
        assert response.status==200
        size=int(response.headers['Content-Length']);assert size==path.stat().st_size
        http.append({'file':str(path.relative_to(P)),'status':response.status,'bytes':size})
files=set(pages)|{M/'mori_v1_2.blend',M/'mori_electronics_detail.blend',M/'mori_assembly_animation.blend',M/'reports/neck_capacity_validation.json',OUT.parent/'work_status.json',OUT.parent/'ENGINEERING.md',OUT.parent/'engineering_current.json',OUT/'approval.json',OUT/'keeper_wall_approval.json',OUT/'commands.json',OUT/'render_manifest.json',OUT/'publication.json',OUT/'README.md',OUT/'fit_coupons/manifest.json',OUT/'fit_coupons/MORI_PA12_6806_fit_coupons.blend'}
files.update(OUT/r['file'] for r in read(OUT/'render_manifest.json')['images'])
result=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision=rev,source_blend_sha256=current,animation_revision=anim['animation_revision'],local_links_checked=len(links),http=http,protected_hardware_files=len(protected),robot_print_count=16,independent_new_coupons=2,files={str(p.relative_to(P)):sha(p) for p in sorted(files)},full_harness='BLOCKED',manufacturing_release=False)
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('M1_49_DELIVERY_PASS',len(links),'local links',len(http),'HTTP checks')
