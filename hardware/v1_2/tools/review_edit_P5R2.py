"""Shared transactional native editor for specific reviewed routing fixes."""
import pcbnew as k
import json,subprocess,collections,math
from all_trace_review_P5R2 import paths,CLI,xy,pt,mm,F,B
from layout_P5 import track,via
from close_P5 import connected
class Edit:
 def __init__(self,kind):
  self.kind=kind;self.name,self.d,self.p,self.r=paths(kind);self.logpath=self.r/'manual_transactions.json';self.log=json.loads(self.logpath.read_text())if self.logpath.exists()else[];self.load()
 def load(self):
  self.b=k.LoadBoard(str(self.p));connected(self.b);self.b.SetFileName(str(self.p));self.saved=self.p.read_bytes();self.record={'removed':[],'routes':[],'placements':[],'vias':[]}
 def remove(self,ids=None,net=None,predicate=None):
  found=[]
  for t in list(self.b.GetTracks()):
   if (ids is not None and any(t.m_Uuid.AsString().startswith(u)for u in ids))or(ids is None and t.GetNetname()==net and (predicate is None or predicate(t))):
    found.append(t.m_Uuid.AsString());self.b.Delete(t)
  if ids is not None:assert len(found)==len(ids),(ids,found)
  self.record['removed']+=found
 def add(self,net,layer,points,width=.2):
  ts=track(self.b,net,points,width,layer);self.record['routes'].append({'net':net,'layer':self.b.GetLayerName(layer),'points':points,'width':width,'uuids':[t.m_Uuid.AsString()for t in ts]})
 def via(self,net,p):
  via(self.b,net,*p,grid=False);self.record['vias'].append({'net':net,'new':p})
 def move(self,ref,p,angle=None):
  f=next(f for f in self.b.GetFootprints()if f.GetReference()==ref);old=xy(f.GetPosition());oa=f.GetOrientationDegrees();na=oa if angle is None else angle
  pivot=f.GetPosition();delta=pt(p[0]-old[0],p[1]-old[1]);rot=k.EDA_ANGLE(na-oa,k.DEGREES_T)
  for z in self.b.Zones():
   if z.GetZoneName()in[f'BODY_{ref}',f'NETBODY_{ref}',f'BODY_{ref}_OPPOSITE',f'NETBODY_{ref}_OPPOSITE']:z.Rotate(pivot,rot);z.Move(delta)
  f.SetOrientationDegrees(na);f.SetPosition(pt(*p));self.record['placements'].append({'ref':ref,'old':[old,oa],'new':[p,na]})
 def movevia(self,prefix,pos):
  t=next(t for t in self.b.GetTracks()if t.m_Uuid.AsString().startswith(prefix));assert isinstance(t,k.PCB_VIA);old=xy(t.GetPosition());t.SetPosition(pt(*pos));self.record['vias'].append({'uuid':t.m_Uuid.AsString(),'old':old,'new':pos})
 def commit(self,reason):
  self.record['reason']=reason;k.SaveBoard(str(self.p),self.b)
  args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','--exit-code-violations','-o',str(self.r/'manual_candidate_drc.json'),str(self.p)]
  cp=subprocess.run(args,capture_output=True,text=True);j=json.loads((self.r/'manual_candidate_drc.json').read_text());ok=cp.returncode==0 and not j['violations'] and not j['unconnected_items']
  self.record.update(accepted=ok,argv=args,returncode=cp.returncode,violations=j['violations'],unconnected=j['unconnected_items'])
  self.log.append(self.record);self.logpath.write_text(json.dumps(self.log,ensure_ascii=False,indent=2)+'\n')
  if not ok:self.p.write_bytes(self.saved)
  print(self.kind,reason,'ACCEPTED'if ok else dict(collections.Counter(x['type']for x in j['violations'])),'opens',len(j['unconnected_items']),flush=True)
  self.load();return ok
