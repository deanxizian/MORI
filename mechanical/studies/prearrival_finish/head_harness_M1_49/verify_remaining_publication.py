"""Verify published partial-harness evidence, file links and unchanged main."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import datetime,hashlib,json,urllib.request,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
publication=read(OUT/'publication.json')
assert publication['status']=='PASS' and publication['full_harness']=='BLOCKED'
for name,h in publication['files'].items():assert sha(ROOT/name)==h,name
assert sha(ROOT/'mechanical/mori_v1_2.blend')==publication['source_blend_sha256']
commands=read(OUT/'commands.json')
for row in commands['commands']:
    assert sha(ROOT/row['stdout_stderr_file'])==row['log_sha256']
    script=row['argv'][row['argv'].index('--python')+1]
    assert sha(ROOT/script)==row['script_sha256'],script
    assert sha(ROOT/row['result_file'])==row['result_sha256']
    result=read(ROOT/row['result_file'])
    assert result['status']==row['result_status']
continuation_file=OUT/'lane_height_commands.json'
continuation=read(continuation_file) if continuation_file.exists() else {'commands':[]}
entry_file=OUT/'entry_commands.json'
entry_commands=read(entry_file) if entry_file.exists() else {'commands':[]}
upper_file=OUT/'upper_connection_commands.json'
upper_commands=read(upper_file) if upper_file.exists() else {'commands':[]}
static_file=OUT/'static_flex/commands.json'
static_commands=read(static_file) if static_file.exists() else {'commands':[], 'failed_executions':[]}
flex_connector_file=OUT/'static_flex/connector_faces/commands.json'
flex_connector_commands=read(flex_connector_file) if flex_connector_file.exists() else {'commands':[], 'failed_executions':[]}
full_flex_file=OUT/'static_flex/full_route/commands.json'
full_flex_commands=read(full_flex_file) if full_flex_file.exists() else {'commands':[], 'failed_executions':[]}
cam_correction_file=OUT/'static_flex/connector_faces/correction/commands.json'
cam_correction_commands=read(cam_correction_file) if cam_correction_file.exists() else {'commands':[], 'failed_executions':[]}
for row in continuation['commands']+entry_commands['commands']+upper_commands['commands']+static_commands['commands']+flex_connector_commands['commands']+full_flex_commands['commands']+cam_correction_commands['commands']:
    assert row['exit_code']==0
    assert sha(ROOT/row['log'])==row['log_sha256'],row['log']
    script=row['argv'][row['argv'].index('--python')+1] if '--python' in row['argv'] else row['argv'][1]
    assert sha(ROOT/script)==row['script_sha256'],script
    assert sha(ROOT/row['result'])==row['result_sha256'],row['result']
    assert read(ROOT/row['result'])['status']==row['check_status']
failure_record=read(OUT/'execution_failures.json') if (OUT/'execution_failures.json').exists() else {'attempts':[]}
for row in failure_record['attempts']:
    assert row['exit_code']!=0
    assert sha(ROOT/row['script_snapshot'])==row['script_sha256']
    assert sha(ROOT/row['log'])==row['log_sha256']
for row in static_commands['failed_executions']+full_flex_commands['failed_executions']+cam_correction_commands['failed_executions']:
    assert row['exit_code']!=0
    assert sha(ROOT/row['log'])==row['log_sha256']
    if row.get('script_snapshot'): assert sha(ROOT/row['script_snapshot'])==row['script_sha256']
work=read(HERE.parent/'work_status.json')
remaining=next(r for r in work['remaining'] if r['id']=='harness')
assert remaining['status']=='BLOCKED'
assert remaining['evidence']=='head_harness_M1_49/remaining_routes/index.html'
main_delivery=read(HERE.parent/'neck_adoption/delivery.json')
assert main_delivery['status']=='PASS' and main_delivery['source_blend_sha256']==publication['source_blend_sha256']
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        self.urls.extend(v for k,v in attrs if k in ['src','href','poster'] and v)
pages=[OUT/'index.html']
if (OUT/'c6_left_slot_entry/index.html').exists():pages.append(OUT/'c6_left_slot_entry/index.html')
if (OUT/'static_flex/index.html').exists():pages.append(OUT/'static_flex/index.html')
if (OUT/'static_flex/connector_faces/index.html').exists():pages.append(OUT/'static_flex/connector_faces/index.html')
if (OUT/'static_flex/full_route/index.html').exists():pages.append(OUT/'static_flex/full_route/index.html')
if (OUT/'static_flex/connector_faces/correction/index.html').exists():pages.append(OUT/'static_flex/connector_faces/correction/index.html')
if (OUT/'cam_restraints/contact_continuous/index.html').exists():pages.append(OUT/'cam_restraints/contact_continuous/index.html')
if (OUT/'cam_restraints/power_sequence_review/index.html').exists():pages.append(OUT/'cam_restraints/power_sequence_review/index.html')
if (OUT/'cam_restraints/inner_head_sequence_review/index.html').exists():pages.append(OUT/'cam_restraints/inner_head_sequence_review/index.html')
if (OUT/'cam_restraints/body_front_rear_split/index.html').exists():pages.append(OUT/'cam_restraints/body_front_rear_split/index.html')
files=set(pages)
for page in pages:
    parser=Links();parser.feed(page.read_text())
    for url in parser.urls:
        u=urlsplit(url)
        if u.scheme or u.netloc or not u.path:continue
        path=(page.parent/unquote(u.path)).resolve();assert path.is_file(),url;files.add(path)
http=[]
for file in sorted(files):
    url='http://127.0.0.1:58201/'+file.relative_to(ROOT).as_posix()
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as response:
        assert response.status==200
        assert int(response.headers['Content-Length'])==file.stat().st_size
        http.append(dict(file=str(file.relative_to(ROOT)),status=200,bytes=file.stat().st_size))
result=dict(status='PASS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_blend_sha256=publication['source_blend_sha256'],files_checked=len(publication['files']),
    commands_checked=len(commands['commands'])+len(continuation['commands'])+len(entry_commands['commands'])+len(upper_commands['commands'])+len(static_commands['commands'])+len(flex_connector_commands['commands'])+len(full_flex_commands['commands'])+len(cam_correction_commands['commands']),http=http,
    preserved_failed_executions=len(failure_record['attempts'])+len(static_commands['failed_executions'])+len(full_flex_commands['failed_executions'])+len(cam_correction_commands['failed_executions']),
    main_delivery=dict(status=main_delivery['status'],hardware_files=main_delivery['protected_hardware_files'],robot_prints=main_delivery['robot_print_count']),
    current_main_lower_nine=publication.get('current_main_lower_nine',publication['lower_nine']),
    unapproved_C6_lower_nine=publication.get('C6_lower_nine','NOT_TESTED'),
    C6_main_applied=publication.get('C6_main_applied',False),full_harness='BLOCKED',manufacturing_release=False,
    actual_command=[sys.executable,str(Path(__file__))],script_sha256=sha(Path(__file__)),
    publication_sha256=sha(OUT/'publication.json'))
(OUT/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
print('REMAINING_DELIVERY_PASS',len(http),'HTTP',result['commands_checked'],'commands',result['main_delivery'])
