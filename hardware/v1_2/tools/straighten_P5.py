"""Remove geometrically avoidable two-segment offsets; native DRC gates each edit."""
import sys,math,json,subprocess,collections
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';log=[];tried=set()
backup=r/'before_visual_straightening.kicad_pcb';k.SaveBoard(str(backup),b)
def check():
 k.SaveBoard(str(p),b);subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/'straighten-drc.json'),str(p)],check=True,capture_output=True);j=json.loads((r/'straighten-drc.json').read_text());return j
cur=check()
def bad(j):return collections.Counter(v['type']for v in j['violations'] if v['type'] not in ['silk_over_copper','silk_overlap','track_dangling','via_dangling'])
for iteration in range(80):
 connected(b);nodes=collections.defaultdict(list)
 for t in b.GetTracks():
  if isinstance(t,k.PCB_VIA)or t.GetWidth()>mm(.25)or t.GetNetname()in['/GND','/+3V3','/M5_FB','/C5_FB','/M5_BOOT','/C5_BOOT']:continue
  for v in [xy(t.GetStart()),xy(t.GetEnd())]:nodes[(t.GetNetname(),t.GetLayer(),v)].append(t)
 candidates=[]
 for (net,l,v),ts in nodes.items():
  if len(ts)!=2:continue
  ids=tuple(sorted(t.m_Uuid.AsString()for t in ts))
  if ids in tried:continue
  a=xy(ts[0].GetEnd())if xy(ts[0].GetStart())==v else xy(ts[0].GetStart());z=xy(ts[1].GetEnd())if xy(ts[1].GetStart())==v else xy(ts[1].GetStart())
  gain=math.dist(a,v)+math.dist(v,z)-math.dist(a,z)
  if gain<.25 or math.dist(a,z)<.5:continue
  angle=abs(math.degrees(math.atan2(z[1]-a[1],z[0]-a[0])))%45
  if min(angle,45-angle)>.5:continue
  if any(isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),v)<.5 for t in b.GetTracks()):continue
  if any(q.GetNetname()==net and q.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(pt(*v),mm(.02))for f in b.GetFootprints()for q in f.Pads()):continue
  if not Guard(b,net).line_clear(a,z,l,k.ToMM(ts[0].GetWidth())):continue
  candidates.append((-gain,ids,a,v,z,net,l,k.ToMM(ts[0].GetWidth())))
 if not candidates:break
 gain,ids,a,v,z,net,l,w=min(candidates);tried.add(ids);checkpoint=p.read_bytes()
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString()in ids:b.Delete(t)
 track(b,net,[a,z],w,l);nxt=check();old=bad(cur);new=bad(nxt)
 if len(nxt['unconnected_items'])<=len(cur['unconnected_items']) and all(new[t]<=old[t]for t in new):
  log.append(dict(net=net,layer=b.GetLayerName(l),old=[a,v,z],new=[a,z],length_saved_mm=-gain));cur=nxt;print('straightened',net,round(-gain,3),flush=True)
 else:p.write_bytes(checkpoint);b=k.LoadBoard(str(p))
cur=check();(r/'visual_straightening.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,len(log),'accepted',bad(cur),'opens',len(cur['unconnected_items']))
