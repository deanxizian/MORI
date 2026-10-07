"""Strict JSON command checks shared by backend, simulator and replay."""
import json,math,pathlib,re
SPEC=json.loads(pathlib.Path(__file__).with_name('command_spec.json').read_text())
FIELDS={'protocol','device_id','session_id','command_id','client_id','source','permissions','type','params','sequence','sent_at_ms','basis_device_ms','valid_for_ms'}
IDENT=re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
class ProtocolError(ValueError):pass

def validate(c):
 if not isinstance(c,dict) or set(c)!=FIELDS:raise ProtocolError('ENVELOPE_FIELDS')
 if c['protocol']!=SPEC['protocol']:raise ProtocolError('VERSION')
 for k in ('device_id','session_id','command_id','client_id'):
  if not isinstance(c[k],str) or not IDENT.fullmatch(c[k]):raise ProtocolError('IDENTIFIER')
 if c['source'] not in SPEC['sources']:raise ProtocolError('SOURCE')
 p=c['permissions']
 if not isinstance(p,list) or not p or len(p)>len(SPEC['permissions']) or not all(isinstance(x,str) and x in SPEC['permissions'] for x in p) or len(set(p))!=len(p):raise ProtocolError('PERMISSIONS')
 for k,lo,hi in [('sequence',1,2147483647),('sent_at_ms',0,9007199254740991),('basis_device_ms',0,9007199254740991),('valid_for_ms',1,30000)]:
  if type(c[k]) is not int or not lo<=c[k]<=hi:raise ProtocolError('INTEGER_RANGE')
 rule=SPEC['commands'].get(c['type']) if isinstance(c['type'],str) else None
 if not rule or c['valid_for_ms']>rule['ttl_max_ms']:raise ProtocolError('COMMAND_OR_EXPIRY')
 if rule['permission'] not in p:raise ProtocolError('PERMISSION_MISSING')
 params=c['params']
 if not isinstance(params,dict) or set(params)!=set(rule['fields']):raise ProtocolError('PARAM_FIELDS')
 for key,r in rule['fields'].items():
  v=params[key];kind=r['kind']
  if kind in ('number','integer'):
   if type(v) not in (float,int) or not r['min']<=v<=r['max'] or not math.isfinite(v) or kind=='integer' and type(v) is not int:raise ProtocolError('NUMBER_RANGE')
  elif kind=='boolean':
   if type(v) is not bool:raise ProtocolError('BOOLEAN')
  elif kind=='string':
   if not isinstance(v,str) or len(v)>r['max'] or '\x00' in v:raise ProtocolError('STRING')
  elif kind=='enum':
   if v not in r['values']:raise ProtocolError('ENUM')
 return c

def parse(raw):
 if len(raw.encode('utf-8'))>SPEC['max_json_bytes']:raise ProtocolError('LENGTH')
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ProtocolError('DUPLICATE_KEY')
   out[k]=v
  return out
 try:return validate(json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ProtocolError('NONFINITE'))))
 except (TypeError,json.JSONDecodeError,RecursionError) as e:raise ProtocolError('JSON') from e
