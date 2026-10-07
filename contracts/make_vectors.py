import copy,json,pathlib
from .protocol import SPEC
base=dict(protocol='MORI/2',device_id='mori-sim-01',session_id='session',command_id='command',client_id='client',source='console',permissions=['control'],type='SET_VELOCITY',params={'v_m_s':.1,'yaw_rad_s':.5},sequence=1,sent_at_ms=100,basis_device_ms=100,valid_for_ms=300)
cases=[]
def add(name,valid,c):cases.append(dict(name=name,valid=valid,command=c))
add('velocity SI',True,base)
for name,rule in SPEC['commands'].items():
 p={}
 for k,r in rule['fields'].items():p[k]=True if r['kind']=='boolean' else 'test' if r['kind']=='string' else r['values'][0] if r['kind']=='enum' else r['min']
 c=dict(base,type=name,params=p,permissions=[rule['permission']],valid_for_ms=min(300,rule['ttl_max_ms']));add(name,True,c)
 for k in p:
  x=copy.deepcopy(c);del x['params'][k];add(name+' missing '+k,False,x)
  r=rule['fields'][k]
  if r['kind'] in ('number','integer'):
   for v in [r['max']+1,True,'0']:
    x=copy.deepcopy(c);x['params'][k]=v;add(name+' invalid '+k+str(v),False,x)
for key,value in [('sequence',True),('sequence',2147483648),('sequence',0),('protocol','MORI/1'),('valid_for_ms',301),('params',{'v_m_s':0,'yaw_rad_s':0,'extra':1}),('permissions',['control','control']),('session_id',''),('sent_at_ms',9007199254740992),('type','__proto__')]:
 c=copy.deepcopy(base);c[key]=value;add(key+str(value),False,c)
pathlib.Path('contracts/test_vectors.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
