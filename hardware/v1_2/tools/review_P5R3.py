"""P5R3 external-review fixes. KiCad Python; only P5R3 is writable.
Original P5R2 sources are immutable. No manufacturing export.
"""
from pathlib import Path
import json,sys,shutil,hashlib,subprocess,collections,math
import pcbnew as k
from layout_P5 import track,via,xy,pt,mm,F,B
from close_P5 import connected
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P5R3'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KINDS=['motion','imu','power','rear']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paths(kind):
 n=f'MORI_{kind}_P5R3';d=H/'kicad'/n;r=O/'reports'/kind;r.mkdir(parents=True,exist_ok=True)
 return n,d,d/(n+'.kicad_pcb'),r
def source(kind):
 n=f'MORI_{kind}_P5R2';d=H/'kicad'/n;return n,d,d/(n+'.kicad_pcb')
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def init():
 log={}
 for kind in KINDS:
  sn,sd,sp=source(kind);n,d,p,r=paths(kind)
  if d.exists():raise RuntimeError('Refusing overwrite '+str(d))
  for f in sd.rglob('*'):
   if not f.is_file()or f.name.startswith('~')or f.suffix in ['.lck','.kicad_prl','.dsn','.ses']:continue
   rel=f.relative_to(sd);t=d/rel.parent/f.name.replace(sn+'.',n+'.');t.parent.mkdir(parents=True,exist_ok=True);data=f.read_bytes()
   if f.suffix in ['.kicad_sch','.kicad_pro']:data=data.replace(sn.encode(),n.encode())
   t.write_bytes(data)
  log[kind]={'source':str(sp.relative_to(ROOT)),'sha256':sha(sp),'candidate':str(p.relative_to(ROOT))}
 dump(O/'sources.json',log)
class Edit:
 def __init__(self,kind):
  self.kind=kind;self.name,self.d,self.p,self.r=paths(kind);self.b=k.LoadBoard(str(self.p));connected(self.b);self.saved=self.p.read_bytes();self.f={f.GetReference():f for f in self.b.GetFootprints()}
 def pad(self,ref,num):return next(p for p in self.f[ref].Pads()if p.GetNumber()==str(num))
 def pos(self,ref,num):return xy(self.pad(ref,num).GetPosition())
 def remove(self,ids=None,net=None,predicate=None):
  found=[]
  for t in list(self.b.GetTracks()):
   if (ids is not None and any(t.m_Uuid.AsString().startswith(u)for u in ids))or(ids is None and t.GetNetname()==net and(predicate is None or predicate(t))):found.append(t.m_Uuid.AsString());self.b.Delete(t)
  if ids is not None:assert len(found)==len(ids),(ids,found)
 def add(self,net,layer,points,width=.2):return track(self.b,net,points,width,layer)
 def via(self,net,p,vd=.8,dr=.3):return via(self.b,net,*p,vd=vd,dr=dr,grid=False)
 def move(self,ref,p,angle=None):
  f=self.f[ref];old=xy(f.GetPosition());oa=f.GetOrientationDegrees();na=oa if angle is None else angle
  pivot=f.GetPosition();delta=pt(p[0]-old[0],p[1]-old[1]);rot=k.EDA_ANGLE(na-oa,k.DEGREES_T)
  for z in self.b.Zones():
   if z.GetZoneName()in[f'BODY_{ref}',f'NETBODY_{ref}',f'BODY_{ref}_OPPOSITE',f'NETBODY_{ref}_OPPOSITE']:z.Rotate(pivot,rot);z.Move(delta)
  f.SetOrientationDegrees(na);f.SetPosition(pt(*p))
 def save(self):k.SaveBoard(str(self.p),self.b)
 def check(self,label,accept=True):
  self.save();(self.r/(label+'_candidate.kicad_pcb')).write_bytes(self.p.read_bytes());args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(self.r/(label+'_drc.json')),str(self.p)]
  cp=subprocess.run(args,capture_output=True,text=True);j=json.loads((self.r/(label+'_drc.json')).read_text());ok=cp.returncode==0
  dump(self.r/(label+'_command.json'),{'argv':args,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'candidate_sha256':sha(self.p),'accepted':ok and accept})
  print(label,cp.returncode,collections.Counter(q['type']for q in j['violations']),'opens',len(j['unconnected_items']),flush=True)
  if not ok or not accept:self.p.write_bytes(self.saved)
  else:(self.r/(label+'_accepted.kicad_pcb')).write_bytes(self.p.read_bytes())
  return ok,j
if __name__=='__main__':
 if sys.argv[1]=='init':init()
