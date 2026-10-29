import concurrent.futures,json,subprocess,time
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute())
rows=json.loads((b/'R179-source-open-groups.json').read_text())['rows']
jobs=[]
skip={frozenset(['U301.3','D1601.2']),frozenset(['J102.25','U302.4']),frozenset(['J102.21','U501.3'])}
for n,row in enumerate(rows):
 for i,a in enumerate(row['groups']):
  for j,z in enumerate(row['groups'][i+1:],i+1):
   first,last=a[0]['pad'],z[0]['pad']
   if frozenset([first,last]) in skip:continue
   jobs.append((f'group{n:02d}-{i}-{j}',row['net'],first,last))
def run(j):
 start=time.monotonic()
 with (b/('R179-'+j[0]+'.log')).open('x') as out:
  p=subprocess.run([py,str(b/'R179_guarded_route.py'),'R179-source',*j],stdout=out,stderr=subprocess.STDOUT)
 path=b/('R179-source-R179-'+j[0])/'result.json'
 r=json.loads(path.read_text())['result'] if path.exists() else {'status':'SCRIPT_FAILED'}
 return dict(name=j[0],net=j[1],endpoints=j[2:],returncode=p.returncode,seconds=time.monotonic()-start,**{k:v for k,v in r.items() if k not in ['routes','activate_pth_layers']})
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for r in pool.map(run,jobs):
  results.append(r); print(json.dumps(r),flush=True)
  (b/'R179-source-other-search-summary.json').write_text(json.dumps(results,indent=2)+'\n')
