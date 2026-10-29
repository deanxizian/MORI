"""Read-only diagnostic comparison; no power acceptance criteria are waived."""
import concurrent.futures,json,subprocess,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');out=b/'R183-diagnostic-source-screen';out.mkdir(exist_ok=False)
jobs=json.loads((b/'R183-source-screen/inventory.json').read_text())['jobs']
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
def run(j):
 argv=[py,str(b/'R183_diagnostic_route.py'),'R183-source',j['name'],j['net'],j['first'],j['last']]
 st=time.monotonic();r=subprocess.run(argv,text=True,capture_output=True)
 p=b/('R183-source-R183-diagnostic-route-'+j['name'])/'result.json'
 result=json.loads(p.read_text())['result'] if p.exists() else None
 row=dict(**j,argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,total_seconds=time.monotonic()-st,result=result)
 (out/(j['name']+'-command.json')).write_text(json.dumps(row,indent=2)+'\n')
 print(json.dumps(dict(item=j['item'],net=j['net'],status=result['status'] if result else 'COMMAND_FAILURE',seconds=round(row['total_seconds'],1))),flush=True)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,jobs))
assert all(r['returncode']==0 and r['result'] for r in rows)
(out/'summary.json').write_text(json.dumps(dict(scope=__doc__,results=rows,adopted=False),indent=2)+'\n')
