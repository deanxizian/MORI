import uuid
from simulation.device import Device
from contracts.protocol import SPEC
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
 def step(self,n):self.t+=n
class Rig:
 def __init__(self):self.clock=Clock();self.d=Device(self.clock);self.seq={};self.p={'client_id':'a','permissions':SPEC['permissions']}
 def cmd(self,kind,params=None,client='a',**changes):
  self.seq[client]=self.seq.get(client,0)+1
  c=dict(protocol='MORI/2',device_id=self.d.device_id,session_id=self.d.session,command_id=uuid.uuid4().hex,client_id=client,source='console',permissions=[SPEC['commands'][kind]['permission']],type=kind,params=params or {},sequence=self.seq[client],sent_at_ms=999999,basis_device_ms=self.clock(),valid_for_ms=300)
  return dict(c,**changes)
 def issue(self,kind,params=None,client='a',**changes):return self.d.issue(self.cmd(kind,params,client,**changes),dict(self.p,client_id=client))
 def arm(self):assert self.issue('CLAIM_CONTROL',{'supervised':True})['status']=='COMPLETED';assert self.issue('ARM',{'local_confirmation':True})['status']=='COMPLETED'
 def tick(self,n=10):self.clock.step(n);self.d.tick()
 def run(self,n):
  for _ in range(n//10):
   if self.clock.t%100==0:self.issue('HEARTBEAT')
   self.tick()

