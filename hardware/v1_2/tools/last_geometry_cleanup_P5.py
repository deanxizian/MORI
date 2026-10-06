"""Remove the remaining short V turns and align terminal approach corridors."""
import sys,json,subprocess,collections
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));connected(b);before=p.read_bytes();(r/'before_last_geometry_cleanup.kicad_pcb').write_bytes(before);changes=[]
def remove(ids):
 for t in list(b.GetTracks()):
  if any(t.m_Uuid.AsString().startswith(v)for v in ids):b.Delete(t)
def add(net,l,ps):
 assert all(Guard(b,net).line_clear(a,z,l)for a,z in zip(ps,ps[1:])),(net,ps)
 track(b,net,ps,.2,l);changes.append(dict(net=net,layer=b.GetLayerName(l),path=ps))
if kind=='power':
 # Straight sense corridor; align its local via by 0.0018mm, no net change.
 v=next(t for t in b.GetTracks()if t.m_Uuid.AsString().startswith('a20cac54'));v.SetPosition(pt(62,20.5232))
 remove(['391f6613','4b8f1725','7679b53f','caf41b58','cdadd8ac'])
 add('/W_SENSE',B,[(62,20.5232),(70.7136,20.5232)]);add('/W_SENSE',F,[(62,19.625),(62,20.5232)])
 # Move EN via along its existing diagonal on B, then approach JP70 from left.
 v=next(t for t in b.GetTracks()if t.m_Uuid.AsString().startswith('432af62d'));old=xy(v.GetPosition());v.SetPosition(pt(32.8168,41.148))
 assert all(Guard(b,'/C5_EN').clear((32.8168,41.148),l,.8,True)for l in[F,B])
 for t in list(b.GetTracks()):
  if not isinstance(t,k.PCB_VIA)and t.GetNetname()=='/C5_EN'and t.GetLayer()==F and min(t.GetStart().x,t.GetEnd().x)>mm(32):b.Delete(t)
 remove(['9691703b']);add('/C5_EN',B,[(32.003999,40.3352),(32.8168,41.148)])
 add('/C5_EN',F,[(32.8168,41.148),(32.8168,42.005201),(35.311599,44.5),(36.5,44.5)])
 remove(['1c9f2fd9','6947e511','fee07a63'])
 add('/H_VM',F,[(56.438799,30.022799),(56.4388,29.049598),(56.938799,28.549599),(57.2008,28.549599)])
 remove(['165fc214','3259fca3','654a9f4c','a39de247'])
 add('/CHG_N',B,[(45.0088,45.3136),(45.0088,44.797598),(45.508799,44.297599),(46.236001,44.297599),(46.736,43.7976),(46.736,39.014399)])
elif kind=='imu':
 remove(['83a3ca44','90310df8','9bb4d557','9d7929d6'])
 add('/+3V3',F,[(9.5,10.5125),(9.5,11.050001),(9.000001,11.55),(8.725,11.55),(8.225,12.05),(8.225,12.5)])
elif kind=='rear':
 for t in list(b.GetTracks()):
  if not isinstance(t,k.PCB_VIA)and t.GetNetname()=='/CLR_N'and t.GetLayer()==F:b.Delete(t)
 add('/CLR_N',F,[(12,15.7),(12,16.750001),(12.499999,17.25),(13.950001,17.25),(14.45,17.749999),(14.45,19.5)])
k.SaveBoard(str(p),b);cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/'last_geometry_drc.json'),str(p)],check=True,capture_output=True)
j=json.loads((r/'last_geometry_drc.json').read_text());hard=[v for v in j['violations']if v['type']not in['silk_over_copper','silk_overlap']]
accepted=not hard and not j['unconnected_items']
if not accepted:p.write_bytes(before)
(r/'last_geometry_cleanup.json').write_text(json.dumps(dict(accepted=accepted,changes=changes,native_remaining=collections.Counter(v['type']for v in j['violations']),unconnected=len(j['unconnected_items'])),indent=2)+'\n')
print(kind,'final geometry',accepted,collections.Counter(v['type']for v in hard),len(j['unconnected_items']),flush=True)
