from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
import math
name,d,p=paths('motion');OUT=HERE/'reports/motion'
snapshot=OUT/'before_geometry_close.kicad_pcb'
if not snapshot.exists():snapshot.write_bytes(p.read_bytes())
b=k.LoadBoard(str(snapshot))
def eq(a,z):return math.dist(a,z)<.00001
removed=[]
for t in list(b.GetTracks()):
 n=t.GetNetname();a,z=xy(t.GetStart()),xy(t.GetEnd());iv=isinstance(t,k.PCB_VIA);remove=False
 if n=='/+3V3'and (eq(a,(10.7442,6.65))or eq(z,(10.7442,6.65))):remove=True
 if n in ['/ARM_Q','/ARM_FEEDBACK']and (eq(a,(31.175,16.7))or eq(z,(31.175,16.7))or eq(a,(32.825,16.7))or eq(z,(32.825,16.7))):remove=True
 if n=='/CURRENT_ADC_IN'and not iv and eq(a,(68.1,15.6))and eq(z,(68.1,27.85)):remove=True
 if n=='/FAULT_N'and not iv and (t.m_Uuid.AsString()=='430a6240-e99c-4186-8524-117338f05b97'or (t.GetLayer()==k.F_Cu and (eq(a,(29.362399,9.9568))or eq(a,(29.362399,13))))):remove=True
 if n=='/CHG_N'and not iv and t.GetLayer()==k.F_Cu:
  if any(eq(a,q)for q in [(7.4,11.35),(5.7,11.35),(5.7,8.55),(4.9,7.75),(4.9,7.35),(5.7,6.55),(5.7,.85),(44.9,.85),(48.9,7.25),(53.75,7.25)]):remove=True
 if remove:removed.append(t.m_Uuid.AsString());b.Delete(t)
f=next(f for f in b.GetFootprints()if f.GetReference()=='R19');f.Move(pt(0,-.125))
for z in b.Zones():
 if z.GetZoneName() in [a+'R19'+c for a in ['BODY_','NETBODY_','VIA_BODY_']for c in ['', '_OPPOSITE']]:z.Move(pt(0,-.125))
routes=[
('/+3V3',k.B_Cu,[(10.7442,7.95),(10.7442,6.8442),(10.5,6.6)]),
('/ARM_Q',k.B_Cu,[(31.175,15.138399),(31.175,16.575)]),
('/ARM_FEEDBACK',k.B_Cu,[(32.825,16.575),(32.825,23.5)]),
('/CURRENT_ADC_IN',k.F_Cu,[(68.1,15.6),(68.1,27.85)]),
('/FAULT_N',k.F_Cu,[(29.362399,9.9568),(27,12.319199),(21.539199,17.779999)]),
('/FAULT_N',k.F_Cu,[(27,12.319199),(27.680801,13),(34.2,13)]),
('/CHG_N',k.F_Cu,[(7.4,11.35),(4,11.35),(4,6.7),(5.7,5),(5.7,.85),(44.9,.85),(44.9,3.25)]),
('/CHG_N',k.F_Cu,[(48.9,7.25),(56.5,7.25),(56.5,10)]),
]
problems=[]
for net,l,qs in routes:
 g=Guard(b,net)
 for a,z in zip(qs,qs[1:]):
  if not g.line_clear(a,z,l):
   hits=[]
   for i in range(101):
    q=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100);o=obstacles(b,net,q,l)
    if o:hits.append((q,o))
   problems.append((net,a,z,hits[::max(1,len(hits)//5)]))
 track(b,net,qs,.2,l)
q=(10.5,6.6)
if not Guard(b,'/+3V3').via_clear(q):problems.append(('+3V3via',q,{b.GetLayerName(l):obstacles(b,'/+3V3',q,l,.8,True)for l in[k.F_Cu,k.B_Cu]}))
via(b,'/+3V3',*q,vd=.8,dr=.3,grid=False)
dump(OUT/'geometry_close_guard.json',{'removed':removed,'routes':routes,'problems':problems})
print(json.dumps(problems,ensure_ascii=False,indent=2),flush=True);assert not problems
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6');(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','geometry_closed')
