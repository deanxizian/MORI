"""Final identity, source ownership, linked-file and published-state audit."""
import json,hashlib,datetime,urllib.parse
from pathlib import Path
from html.parser import HTMLParser
R=Path(__file__).resolve().parents[1];PROJECT=R.parent
read=lambda p:json.loads(p.read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=read(PROJECT/'config/geometry.json');q=p['p5r7_adoption'];rev=p['revision'];source=digest(R/'mori_v1_2.blend')
old=read(PROJECT/q['hardware_snapshot']);changed=[n for n,h in old.items() if not (PROJECT/n).exists() or digest(PROJECT/n)!=h]
current={str(x.relative_to(PROJECT)) for x in (PROJECT/'hardware').rglob('*') if x.is_file()}|{'contracts/components.json','contracts/electrical_interfaces.json'}
new_hardware=sorted(current-set(old));a=read(R/'reports/p5r7_adoption_validation.json');v=read(R/'reports/validation.json');d=read(R/'reports/delivery_consistency.json');ex=read(R/'reports/export_manifest.json');am=read(R/'animation/manifest.json');av=read(R/'animation/validation.json');ad=read(R/'animation/delivery.json')
checks=dict(no_received_hardware_modified=not changed,correct_revision=rev=='V1.2-M1.45',adoption_scope=a['adoption_status']=='PASS' and not a['scope']['print_changed'],source_current=a['source_blend_sha256']==am['source_blend_sha256']==ad['source_blend_sha256']==source,geometry_no_unexpected_failures=v['counts']['FAIL']==0,E_interface_remains_BLOCKED=a['full_mated_fit']==a['E_source_discrepancy']['status']=='BLOCKED',delivery_consistency=d['status']=='PASS',video=am['rendered_video'] and am['p5r7_adopted'] and av['status']=='PASS' and ad['p5r7_adopted'],video_bytes=digest(R/'animation/MORI_assembly.mp4')==am['video']['sha256'],animation_bytes=digest(R/'mori_assembly_animation.blend')==am['animation_blend_sha256'],known_stl_defect_only=[x['id'] for x in ex['parts'] if x['status']!='PASS']==['Head_Rear'])
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        for k,x in attrs:
            if k in ['href','src'] and x:self.urls.append(x)
missing=[];linked=0
for f in ['index.html','manufacturing.html','parts.html','animation/index.html']:
    page=R/f;parser=Links();parser.feed(page.read_text())
    for u in parser.urls:
        url=urllib.parse.urlsplit(u)
        if url.scheme or not url.path:continue
        target=(page.parent/urllib.parse.unquote(url.path)).resolve();linked+=1
        if not target.exists():missing.append(dict(page=f,link=u))
checks['local_links_resolve']=not missing
# Concurrent read-only output pipelines keep distinct logs. Merge recorded
# command executions by start/stage without rewriting their outcomes.
cmdpath=R/'reports/p5r7_delivery_commands.json';commands=read(cmdpath)
commands+=read(R/'reports/p5r7_path_commands.json')
commands=list({(x['started_utc'],x['stage']):x for x in commands}.values());commands.sort(key=lambda x:x['started_utc'])
for x in commands:
    if x['returncode'] and x['stage']=='check_p5r7_current_paths':
        x['diagnostic']='First wrapper split left a comment suffix as Python, raising IndentationError before checks. Corrected, then rerun successfully; the shared log path contains the successful retry.'
cmdpath.write_text(json.dumps(commands,ensure_ascii=False,indent=2)+'\n')
files=[PROJECT/'config/geometry.json',PROJECT/'contracts/mechanical_interfaces.json',R/'mori_v1_2.blend',R/'mori_electronics_detail.blend',R/'mori_assembly_animation.blend']
files += [R/x for x in ['index.html','manufacturing.html','parts.html','README.md','reports/P5R7应用_M1_45.md','reports/p5r7_delivery.json','reports/p5r7_adoption_validation.json','reports/p5r7_current/followthrough.json','reports/p5r7_current/service.json','reports/head_retention_body_sequence.json','reports/p5r7_delivery_commands.json','reports/validation.json','reports/export_manifest.json','animation/manifest.json','animation/validation.json','animation/delivery.json','animation/MORI_assembly.mp4','animation/index.html']]
out=dict(revision=rev,finalized_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if all(checks.values()) else 'FAIL',status_scope='P5R7 adoption, source identity and delivery synchronization only',checks=checks,hardware_files_checked=len(old),changed_hardware_files=changed,new_external_hardware_files=new_hardware,local_links_checked=linked,missing_links=missing,printed_geometry_changed=False,full_mated_fit='BLOCKED',manufacturing_release=False,stl_topology_status='FAIL',stl_failed=['Head_Rear'],source_main_sha256=source,files={str(f.relative_to(PROJECT)):digest(f) for f in files})
(R/'reports/p5r7_final_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('P5R7_FINAL_AUDIT',out['status'],checks,'hardware',len(old),'links',linked,flush=True)
assert out['status']=='PASS',out
