"""Local offline memory backup/restore. Stop gateway before restoring.
Default retention is seven days. Deletion journal lives outside snapshot and is
mandatory when restoring; never restore credentials from an old backup.
"""
import argparse,pathlib,time,shutil,datetime
from backend.mori.memory import Memory
p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','restore','prune']);p.add_argument('--data',default='.state');p.add_argument('--backups',default='.state/backups');p.add_argument('--snapshot');p.add_argument('--gateway-stopped',action='store_true');a=p.parse_args()
data=pathlib.Path(a.data);backups=pathlib.Path(a.backups);backups.mkdir(parents=True,exist_ok=True)
if a.action=='backup':
 path=backups/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'.sqlite');m=Memory(data/'memory.sqlite');m.backup(path);m.close();path.chmod(0o600);print(path)
elif a.action=='restore':
 if not a.gateway_stopped or not a.snapshot:raise SystemExit('--gateway-stopped and --snapshot required')
 journal=data/'memory.deletions.jsonl'
 if not journal.exists():raise SystemExit('Independent deletion journal required (create empty only for confirmed never-deleted store)')
 temp=data/'restore.sqlite';shutil.copyfile(a.snapshot,temp);m=Memory(temp);m.apply_deletions(journal);m.close();temp.replace(data/'memory.sqlite');print('restored with deletion journal')
else:
 for p in backups.glob('*.sqlite'):
  if time.time()-p.stat().st_mtime>7*86400:p.unlink();print('pruned',p.name)
