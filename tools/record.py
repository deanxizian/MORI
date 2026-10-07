"""Execute an argument vector and retain truthful exit code, timings and file hashes."""
import argparse,subprocess,pathlib,json,datetime,hashlib,time,sys,os
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();cmd=a.command
if cmd and cmd[0]=='--':cmd=cmd[1:]
out=pathlib.Path(os.environ.get('MORI_REPORT_ROOT','reports/v1'))/'runs'/a.name;out.mkdir(parents=True,exist_ok=True)
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
try:
 with (out/'output.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT);code=r.returncode
except OSError as e:(out/'output.log').write_text(str(e));code=127
meta={'command':cmd,'cwd':str(pathlib.Path.cwd()),'started_utc':start,'elapsed_s':time.monotonic()-t,'exit_code':code,'status':'PASS' if code==0 else 'FAIL','source':'HOST','log_sha256':hashlib.sha256((out/'output.log').read_bytes()).hexdigest()}
(out/'command.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta));sys.exit(code)
