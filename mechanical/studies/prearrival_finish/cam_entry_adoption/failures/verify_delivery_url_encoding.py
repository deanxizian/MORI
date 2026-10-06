"""Check current deliverables, immutable history, protected hardware and links."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import datetime,hashlib,json,urllib.request,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3];M=ROOT/'mechanical';S=OUT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=sha(M/'mori_v1_2.blend');rev=read(ROOT/'config/geometry.json')['revision']
assert rev=='V1.2-M1.50'
prep=read(OUT/'preparation.json');scope=read(OUT/'check.json');pub=read(OUT/'publication.json')
assert pub['status']=='PASS' and pub['source_blend_sha256']==source
assert scope['status']=='PASS' and scope['sources']['mechanical/mori_v1_2.blend']==source
assert scope['changed_native_parts']==['CAM_Mainboard'] and scope['unchanged_native_parts']==208
assert len(scope['unchanged_CAM_components'])==130 and not scope['printed_geometry_change']
assert all(sha(ROOT/n)==h for n,h in scope['production_inputs'].items())
for name,row in prep['files'].items():assert sha(ROOT/row['snapshot'])==row['sha256'],name
for name,h in prep['protected_hardware'].items():assert sha(ROOT/name)==h,name
v=read(M/'reports/validation.json');assert v['counts']['FAIL']==0
assert read(M/'reports/rebuild_check.json')['status']=='PASS'
assert all(sha(ROOT/n)==h for n,h in read(M/'reports/build_manifest.json')['input_sha256'].items())
assert read(M/'reports/delivery_consistency.json')['status']=='PASS'
for name in ['neck_capacity_validation.json','head_axial_retention_validation.json']:
    d=read(M/'reports'/name);assert d['status']=='PASS' and d['source_blend_sha256']==source,name
ex=read(M/'reports/export_manifest.json');old=read(ROOT/prep['snapshot_root']/'mechanical/reports/export_manifest.json')
assert ex['exported_count']==ex['candidate_count']==21
assert all(x['status']=='PASS' and sha(M/x['file'])==x['sha256'] for x in ex['parts'])
assert {x['id']:x['sha256'] for x in ex['parts']}=={x['id']:x['sha256'] for x in old['parts']}
assert read(M/'reports/manufacturing_classification.json')['counts']['robot_print']==16
am=read(M/'animation/manifest.json');av=read(M/'animation/validation.json');ad=read(M/'animation/delivery.json')
assert am['animation_revision']==rev+'-A1' and am['rendered_video'] and av['status']=='PASS'
assert am['source_blend_sha256']==ad['source_blend_sha256']==source
assert all(sha(M/n)==h for n,h in ad['files'].items())
render=read(OUT/'render_manifest.json');assert render['status']=='PASS' and render['source_blend_sha256']==source
assert not render['geometry_substitution'] and all(sha(ROOT/r['file'])==r['sha256'] for r in render['images'])
visual=read(OUT/'visual_review.json');assert visual['status']=='PASS'
assert all(sha(ROOT/n)==h for n,h in visual['images'].items())
assert read(M/'reports/electronics_detail_manifest.json')['source_main_sha256']==source
assert read(S/'engineering_current.json')['source_blend_sha256']==source
work=read(S/'work_status.json');assert work['source_blend_sha256']==source
assert work['status']=='BLOCKED' and not work['manufacturing_release']
assert next(r for r in work['remaining'] if r['id']=='harness')['status']=='BLOCKED'
history=read(OUT/'m1_49_history_verification.json');assert history['status']=='PASS'
assert history['source_blend_sha256']==prep['source_blend_sha256'] and history['current_main_sha256']==source
commands=read(OUT/'commands.json');latest={}
for row in commands:
    assert sha(ROOT/row['log'])==row['log_sha256'],row['log']
    latest[row['stage']]=row
required=['build','rebuild','focused','export','structure_metadata','rear_audit','validate','render','catalog',
    'electronics','electronics_check','detail_render','metal','engineering','body_sequence','printability','consistency','animation']
assert all(latest[n]['returncode']==0 for n in required)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):self.urls.extend(v for k,v in attrs if k in ['src','href','poster'] and v)
pages=[M/'index.html',M/'parts.html',M/'manufacturing.html',M/'animation/index.html',OUT/'index.html',S/'index.html']
links=set(pages)
for path in pages:
    parser=Links();parser.feed(path.read_text())
    for link in parser.urls:
        u=urlsplit(link)
        if u.scheme or u.netloc or not u.path:continue
        target=(path.parent/unquote(u.path)).resolve();assert target.is_file(),(path,link);links.add(target)
http=[]
for path in sorted(links):
    url='http://127.0.0.1:58201/'+path.relative_to(ROOT).as_posix()
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as response:
        assert response.status==200 and int(response.headers['Content-Length'])==path.stat().st_size
        http.append(dict(file=str(path.relative_to(ROOT)),status=response.status,bytes=path.stat().st_size))
owned=set(pages)|{ROOT/'config/geometry.json',ROOT/'contracts/mechanical_interfaces.json',
    M/'mori_v1_2.blend',M/'mori_electronics_detail.blend',M/'mori_assembly_animation.blend',
    M/'README.md',S/'work_status.json',S/'engineering_current.json',S/'ENGINEERING.md'}
owned.update(p for p in OUT.iterdir() if p.is_file() and p.suffix in ['.json','.py','.png','.md'] and p.name!='delivery.json')
owned.update(M/'reports'/n for n in ['validation.json','delivery_consistency.json','build_manifest.json','export_manifest.json',
    'head_motion.json','static_interference.json','neck_capacity_validation.json','head_axial_retention_validation.json',
    'electronics_detail_manifest.json','manufacturing_classification.json','render_manifest.json','parts_preview_manifest.json'])
result=dict(status='PASS',revision=rev,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_blend_sha256=source,animation_revision=am['animation_revision'],validation=v['counts'],
    unchanged_native_parts=208,unchanged_CAM_components=130,unchanged_STL_files=21,robot_prints=16,
    protected_hardware_files=len(prep['protected_hardware']),immutable_M1_49_snapshot_files=len(prep['files']),
    current_commands=len(commands),preserved_failed_stages=[r for r in commands if r['returncode']],
    historical_integrity_only=dict(commands=history['commands_checked'],reexecuted_against_current=False),
    local_links=len(links),http=http,files={str(p.relative_to(ROOT)):sha(p) for p in sorted(owned)},
    full_harness='BLOCKED',exact_FPC_mating='BLOCKED',manufacturing_release=False,
    actual_command=[sys.executable,str(Path(__file__))],script_sha256=sha(Path(__file__)))
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('M1_50_DELIVERY_PASS',v['counts'],len(http),'HTTP',len(prep['files']),'snapshots',flush=True)
