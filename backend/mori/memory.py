import datetime,json,pathlib,sqlite3,uuid

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
class Memory:
 def __init__(self,path):
  self.path=pathlib.Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.path,check_same_thread=False);self.db.row_factory=sqlite3.Row
  self.db.executescript('''PRAGMA foreign_keys=ON; PRAGMA secure_delete=ON;
  CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY); INSERT OR IGNORE INTO migrations VALUES(1);
  CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,user_id TEXT,device_id TEXT,category TEXT,text TEXT,source_id TEXT,confirmed INTEGER,created_at TEXT,updated_at TEXT);
  CREATE VIRTUAL TABLE IF NOT EXISTS memory_index USING fts5(id UNINDEXED,user_id UNINDEXED,device_id UNINDEXED,text,tokenize='unicode61');
  CREATE TABLE IF NOT EXISTS conflicts(id TEXT,previous_text TEXT,source_id TEXT,changed_at TEXT,FOREIGN KEY(id) REFERENCES memories(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS preferences(user_id TEXT,device_id TEXT,enabled INTEGER DEFAULT 1,PRIMARY KEY(user_id,device_id));
  CREATE TABLE IF NOT EXISTS deletion_ledger(id TEXT PRIMARY KEY,deleted_at TEXT);
  ''');self.db.commit()
 def enabled(self,user,device):
  row=self.db.execute('SELECT enabled FROM preferences WHERE user_id=? AND device_id=?',(user,device)).fetchone();return row is None or bool(row[0])
 def set_enabled(self,user,device,enabled):
  self.db.execute('INSERT OR REPLACE INTO preferences VALUES(?,?,?)',(user,device,int(enabled)));self.db.commit()
 def remember(self,user,device,text,category,source_id,confirmed,sensitive=False):
  if not self.enabled(user,device):raise ValueError('MEMORY_DISABLED')
  if not text.strip() or not source_id.strip():raise ValueError('EVIDENCE_REQUIRED')
  if category!='inference' and not confirmed:raise ValueError('CONFIRMATION_REQUIRED')
  if sensitive and not confirmed:raise ValueError('SENSITIVE_CONFIRMATION_REQUIRED')
  ident=uuid.uuid4().hex;t=utc()
  self.db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?)',(ident,user,device,category,text,source_id,int(confirmed),t,t))
  self.db.execute('INSERT INTO memory_index VALUES(?,?,?,?)',(ident,user,device,text));self.db.commit();return ident
 def query(self,user,device,query=''):
  if not self.enabled(user,device):return []
  # FTS for tokenized queries; literal LIKE fallback supports Chinese substrings.
  if query:
   quoted='"'+query.replace('"','""')+'"'
   rows=self.db.execute('SELECT m.* FROM memories m WHERE user_id=? AND device_id=? AND (text LIKE ? ESCAPE "\\" OR id IN (SELECT id FROM memory_index WHERE memory_index MATCH ? AND user_id=? AND device_id=?)) ORDER BY updated_at DESC LIMIT 100',(user,device,'%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%',quoted,user,device)).fetchall()
  else:rows=self.db.execute('SELECT * FROM memories WHERE user_id=? AND device_id=? ORDER BY updated_at DESC LIMIT 100',(user,device)).fetchall()
  return [{**dict(row),'confirmed':bool(row['confirmed']),'conflicts':[dict(x) for x in self.db.execute('SELECT previous_text,source_id,changed_at FROM conflicts WHERE id=?',(row['id'],))]} for row in rows]
 def correct(self,user,device,ident,text,source,confirmed):
  if not self.enabled(user,device) or not confirmed or not text.strip() or not source.strip():raise ValueError('CONFIRMATION_REQUIRED')
  row=self.db.execute('SELECT * FROM memories WHERE id=? AND user_id=? AND device_id=?',(ident,user,device)).fetchone()
  if not row:raise ValueError('NOT_FOUND')
  self.db.execute('INSERT INTO conflicts VALUES(?,?,?,?)',(ident,row['text'],row['source_id'],utc()))
  self.db.execute('UPDATE memories SET text=?,source_id=?,confirmed=1,updated_at=? WHERE id=?',(text,source,utc(),ident))
  self.db.execute('DELETE FROM memory_index WHERE id=?',(ident,));self.db.execute('INSERT INTO memory_index VALUES(?,?,?,?)',(ident,user,device,text));self.db.commit()
 def delete(self,user,device,ident):
  row=self.db.execute('SELECT id FROM memories WHERE id=? AND user_id=? AND device_id=?',(ident,user,device)).fetchone()
  if not row:raise ValueError('NOT_FOUND')
  self.db.execute('DELETE FROM memory_index WHERE id=?',(ident,));self.db.execute('DELETE FROM memories WHERE id=?',(ident,))
  self.db.execute('INSERT OR REPLACE INTO deletion_ledger VALUES(?,?)',(ident,utc()));self.db.commit();self.rebuild_index()
  # Independent deletion journal must be retained across restoration of older backups.
  with self.path.with_suffix('.deletions.jsonl').open('a') as f:f.write(json.dumps({'id':ident,'deleted_at':utc()})+'\n')
 def export(self,user,device):
  return [dict(r) for r in self.db.execute('SELECT * FROM memories WHERE user_id=? AND device_id=?',(user,device))]
 def backup(self,path):
  target=sqlite3.connect(path);self.db.backup(target);target.close()
 def apply_deletions(self,journal):
  for line in pathlib.Path(journal).read_text().splitlines():
   ident=json.loads(line)['id'];self.db.execute('DELETE FROM memory_index WHERE id=?',(ident,));self.db.execute('DELETE FROM memories WHERE id=?',(ident,))
  self.db.commit();self.rebuild_index()
 def rebuild_index(self):
  self.db.execute('DROP TABLE memory_index');self.db.execute("CREATE VIRTUAL TABLE memory_index USING fts5(id UNINDEXED,user_id UNINDEXED,device_id UNINDEXED,text,tokenize='unicode61')");self.db.execute('INSERT INTO memory_index SELECT id,user_id,device_id,text FROM memories');self.db.commit();self.db.execute('VACUUM')
 def close(self):self.db.close()
