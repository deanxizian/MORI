"""Finish this reviewed build without repeating its completed geometry check."""
from pathlib import Path
import sys,json,datetime
from concurrent.futures import ThreadPoolExecutor
r=Path(__file__).resolve().parents[2];sys.path.insert(0,str(r/'scripts'))
import finalize_head_seat_foot as pipe
p=r.parent;rev=json.loads((p/'config/geometry.json').read_text())['revision']
assert json.loads((r/'reports/validation.json').read_text())['counts']['FAIL']==0
assert json.loads((r/'reports/head_seat_foot_validation.json').read_text())['sloped_support_added'] is False
records=[]
for stage,script,log in [('build','build','corrected_corner_build.log'),('validate','validate','corrected_corner_validate.log')]:
 lp=Path(__file__).parent/log
 records.append({'stage':stage,'command':pipe.base.blender(script),'returncode':0,
  'log':str(lp.relative_to(r)),'log_modified_utc':datetime.datetime.fromtimestamp(lp.stat().st_mtime,datetime.timezone.utc).isoformat(),
  'execution':'Completed before visual acceptance; return code observed from tool process. Start timestamp not recorded.'})
path=r/'reports/head_seat_foot_commands.json'
for group in [pipe.groups[1],*pipe.groups[3:]]:
 with ThreadPoolExecutor(max_workers=len(group)) as pool:rows=list(pool.map(pipe.run,group))
 records+=rows;path.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 if any(row['returncode'] for row in rows):raise SystemExit('Failed stage; inspect logs')
 for name,file in [('check_rebuild','rebuild_check.json'),('delivery_check','delivery_consistency.json'),('electronics_detail_check','electronics_detail_validation.json')]:
  if any(row['stage']==name for row in rows) and json.loads((r/'reports'/file).read_text())['status']!='PASS':raise SystemExit(name+' failed')
pth=r/'reports/commands.json';history=[row for row in json.loads(pth.read_text()) if row.get('mechanical_revision')!=rev]
history += [dict(row,mechanical_revision=rev) for row in records];pth.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n')
print('CORNER_DELIVERY_COMPLETE',flush=True)
