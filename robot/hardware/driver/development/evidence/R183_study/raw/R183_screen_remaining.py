"""Screen current remaining native connections without modifying a PCB.

Resolve endpoints from native UUIDs, not translated DRC display net names.
Skip the already studied fixed U301 and U1701 ends. Source-bound power/body,
reference and native-layer constraints are retained. Proposals are unqualified.
"""
import concurrent.futures,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials')
out=b/'R183-source-screen';out.mkdir(exist_ok=False)
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
d=json.loads(Path('robot/hardware/driver/development/evidence/R181C/drc.json').read_text())
jobs=[];skipped=[]
for i,e in enumerate(d['unconnected_items'],1):
    objects=[c.by_id[x['uuid']] for x in e['items']]
    net=objects[0].GetNetname();assert all(x.GetNetname()==net for x in objects)
    gs=groups(c,net);ends=[]
    for o in objects:
        if isinstance(o,pcb.PAD):matches=[g for g in gs if c.pad_name(o) in g['pads']]
        else:
            shapes=[(ly,s) for (u,ly),s in c.shapes.items() if u==uid(o)]
            matches=[g for g in gs if any(ly in g['layers'] and g['layers'][ly].intersects(s) for ly,s in shapes)]
        assert len(matches)==1,(i,uid(o),len(matches))
        ends.append(matches[0])
    assert ends[0] is not ends[1]
    names=[g['pads'][0] for g in ends]
    row=dict(item=i,name=f'item{i:02d}',net=net,endpoint_group_pads=[g['pads'] for g in ends],first=names[0],last=names[1])
    if any(x in p for p in row['endpoint_group_pads'] for x in ['U301.3','U1701.5']):
        row['reason']='Fixed terminal already studied in current source lineage; no repeated micro-route search.';skipped.append(row)
    else:jobs.append(row)
(out/'inventory.json').write_text(json.dumps(dict(source_sha256=c.sha,jobs=jobs,skipped=skipped),indent=2)+'\n')
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
def run(j):
    argv=[py,str(b/'R183_route.py'),'R183-source',j['name'],j['net'],j['first'],j['last']]
    started=time.monotonic();r=subprocess.run(argv,text=True,capture_output=True)
    result_path=b/('R183-source-R183-route-'+j['name'])/'result.json'
    result=json.loads(result_path.read_text())['result'] if result_path.exists() else None
    row=dict(**j,argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,
             total_seconds=time.monotonic()-started,result=result)
    (out/(j['name']+'-command.json')).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(dict(item=j['item'],net=j['net'],returncode=r.returncode,
        status=result['status'] if result else 'COMMAND_FAILURE',seconds=round(row['total_seconds'],1))),flush=True)
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    rows=list(pool.map(run,jobs))
assert all(r['returncode']==0 and r['result'] for r in rows)
(out/'summary.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,
  attempted=len(rows),skipped=skipped,results=[{k:r[k] for k in ['item','net','first','last','total_seconds','result']} for r in rows],adopted=False),indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
