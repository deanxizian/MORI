import hashlib,hmac,json,pathlib,secrets,sqlite3,time,uuid
from contracts.protocol import SPEC
from collections import OrderedDict
class Auth:
 def __init__(self,directory,clock=time.monotonic):
  self.path=pathlib.Path(directory);self.path.mkdir(parents=True,exist_ok=True)
  self.db=sqlite3.connect(self.path/'credentials.sqlite',check_same_thread=False);self.db.row_factory=sqlite3.Row
  self.db.execute('CREATE TABLE IF NOT EXISTS credentials(digest TEXT PRIMARY KEY,client_id TEXT,user_id TEXT,permissions TEXT,role TEXT,revoked INTEGER DEFAULT 0)');self.db.commit()
  self.clock=clock;self.pair_code=secrets.token_hex(4);self.expires=clock()+600;self.attempts=OrderedDict()
  p=self.path/'pairing.txt';p.write_text(self.pair_code);p.chmod(0o600)
 def pair(self,code,peer='local'):
  now=self.clock()
  if not isinstance(code,str) or len(code)>128 or now>=self.expires or not self.pair_code:raise ValueError('PAIRING_REJECTED')
  # A bounded fixed window per transport peer; rejected retries cannot extend it.
  started,count=self.attempts.get(peer,(now,0))
  if now-started>=60:started,count=now,0
  if count>=5:raise ValueError('PAIRING_REJECTED')
  self.attempts[peer]=(started,count+1);self.attempts.move_to_end(peer)
  while len(self.attempts)>1024:self.attempts.popitem(last=False)
  if not hmac.compare_digest(code,self.pair_code):raise ValueError('PAIRING_REJECTED')
  self.pair_code=None;(self.path/'pairing.txt').unlink(missing_ok=True)
  return self.create('owner',SPEC['permissions'])
 def create(self,role,permissions):
  token=secrets.token_urlsafe(32);client='client-'+uuid.uuid4().hex
  self.db.execute('INSERT INTO credentials VALUES(?,?,?,?,?,0)',(hashlib.sha256(token.encode()).hexdigest(),client,'personal-user',json.dumps(permissions),role));self.db.commit()
  return {'token':token,'client_id':client,'permissions':permissions,'user_id':'personal-user','role':role}
 def verify(self,token):
  if not isinstance(token,str) or len(token)>128:raise ValueError('UNAUTHORIZED')
  row=self.db.execute('SELECT * FROM credentials WHERE digest=? AND revoked=0',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
  if not row:raise ValueError('UNAUTHORIZED')
  return {'client_id':row['client_id'],'user_id':row['user_id'],'permissions':json.loads(row['permissions']),'role':row['role']}
 def revoke(self,client):self.db.execute('UPDATE credentials SET revoked=1 WHERE client_id=?',(client,));self.db.commit()
