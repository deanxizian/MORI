import json,uuid,shutil,asyncio,pytest
from backend.mori.memory import Memory
from backend.mori.auth import Auth
from backend.mori.app import create_app,Gateway
from fastapi.testclient import TestClient
from simulation.tests.test_device import Clock,Rig

def test_memory_restart_scope_correct_delete_restore(tmp_path):
 p=tmp_path/'memory.sqlite';m=Memory(p)
 ident=m.remember('u','d','喜欢绿茶','preference','explicit-1',True)
 m.remember('u','other','喜欢咖啡','preference','explicit-2',True)
 m.close();m=Memory(p);assert m.query('u','d','绿茶')[0]['id']==ident
 assert m.query('attacker','d')==[]
 m.correct('u','d',ident,'喜欢红茶','explicit-3',True)
 row=m.query('u','d','红茶')[0];assert row['conflicts'][0]['previous_text']=='喜欢绿茶'
 assert m.query('u','d','绿茶')==[]
 m.backup(tmp_path/'backup.sqlite');m.delete('u','d',ident);assert m.export('u','d')==[]
 assert m.db.execute('SELECT count(*) FROM conflicts').fetchone()[0]==0
 assert m.db.execute('SELECT count(*) FROM memory_index WHERE id=?',(ident,)).fetchone()[0]==0
 m.close();shutil.copyfile(tmp_path/'backup.sqlite',p);m=Memory(p);m.apply_deletions(tmp_path/'memory.deletions.jsonl');assert m.query('u','d')==[];m.close()

def test_disable_inference_and_sensitive(tmp_path):
 m=Memory(tmp_path/'memory.sqlite')
 with pytest.raises(ValueError):m.remember('u','d','可能喜欢猫','fact','llm',False)
 m.remember('u','d','可能喜欢猫','inference','llm',False)
 assert not m.query('u','d')[0]['confirmed']
 with pytest.raises(ValueError):m.remember('u','d','sensitive','inference','s',False,True)
 m.set_enabled('u','d',False);assert m.query('u','d')==[]
 with pytest.raises(ValueError):m.remember('u','d','x','fact','s',True)
 m.close()

def test_pairing_onetime_revocation(tmp_path):
 a=Auth(tmp_path);code=a.pair_code;p=a.pair(code);assert a.verify(p['token'])['client_id']==p['client_id']
 with pytest.raises(ValueError):a.pair(code)
 a.revoke(p['client_id'])
 with pytest.raises(ValueError):a.verify(p['token'])
 a.db.close()

def test_gateway_cross_client_memory_collision_leaks_nothing(tmp_path):
 g=Gateway(tmp_path,Clock());r=Rig();r.d=g.device
 a=g.auth.create('owner',['memory']);b=g.auth.create('owner',['memory']);r.p=a
 c=r.cmd('MEMORY_REMEMBER',{'text':'private','category':'fact','confirmed':True,'sensitive':False,'source_id':'manual'},client=a['client_id'])
 asyncio.run(g.dispatch(c,a))
 q=r.cmd('MEMORY_QUERY',{'query':''},client=a['client_id']);out=asyncio.run(g.dispatch(q,a));assert out['data']
 copied=dict(q,client_id=b['client_id']);res=asyncio.run(g.dispatch(copied,b));assert res['status']=='REJECTED' and not res.get('data')
 g.close()

def test_http_auth_ws_and_real_pixel_input(tmp_path):
 app=create_app(tmp_path);g=app.state.gateway
 with TestClient(app) as c:
  assert c.get('/health').json()['source']=='SIMULATED';assert c.get('/api/status').status_code==401
  p=c.post('/api/pair',json={'code':g.auth.pair_code}).json();headers={'Authorization':'Bearer '+p['token']}
  assert c.get('/api/status',headers=headers).json()['enabled'] is False
  assert c.get('/api/camera/frame',headers=headers).status_code==409
  with c.websocket_connect('/ws') as ws:
   ws.send_json({'token':p['token']});s=ws.receive_json();assert s['type']=='telemetry'
   r=Rig();r.d=g.device
   for command,params in [('CLAIM_CONTROL',{'supervised':True}),('CAMERA_MODE',{'mode':'SNAPSHOT','upload_allowed':False})]:
    cmd=r.cmd(command,params,client=p['client_id']);cmd['basis_device_ms']=g.clock();ws.send_json(cmd)
    while (reply:=ws.receive_json())['type']!='result':pass
    assert reply['data']['status']=='COMPLETED'
   image=c.get('/api/camera/frame',headers=headers);assert image.status_code==200 and image.content[:2]==b'\xff\xd8' and image.headers['x-mori-source']=='SIMULATED'
   assert c.post('/api/camera/describe',headers=headers).status_code==403
  assert c.post('/api/credentials/revoke',headers=headers).status_code==200
  assert c.get('/api/status',headers=headers).status_code==401


def test_memory_delete_purges_gateway_result_cache(tmp_path):
 g=Gateway(tmp_path,Clock());r=Rig();r.d=g.device;p=g.auth.create('owner',['memory']);cid=p['client_id']
 def issue(k,params):return asyncio.run(g.dispatch(r.cmd(k,params,client=cid),p))
 ident=issue('MEMORY_REMEMBER',{'text':'private cache','category':'fact','confirmed':True,'sensitive':False,'source_id':'explicit'})['data']['id']
 issue('MEMORY_QUERY',{'query':''});issue('MEMORY_DELETE',{'id':ident})
 assert 'private cache' not in json.dumps(list(g.device.results.values()))
 g.close()

def test_auxiliary_json_rejects_wrong_shapes_and_extra_fields(tmp_path):
 app=create_app(tmp_path);g=app.state.gateway
 with TestClient(app) as client:
  p=g.auth.create('owner',['control']);h={'Authorization':'Bearer '+p['token']}
  for bad in [[],None,{'scenario':'single','extra':1},{'scenario':float('inf')}]:
   response=client.post('/api/simulation/scenario',headers=h,content=json.dumps(bad))
   assert response.status_code==400
  for raw in ['{"scenario":"single","scenario":"lost"}', '{"scenario":NaN}', '{']:
   assert client.post('/api/simulation/scenario',headers=h,content=raw).status_code==400
