"""Deliberate corridor/via placement, replacing the long camera detour."""
import route_motion_P5R7 as r
from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
from close_P5 import clusters
OUT=HERE/'reports/motion';name,d,p=paths('motion')
b=k.LoadBoard(str(OUT/'adc_priority_partial.kicad_pcb'))
base=k.LoadBoard(str(OUT/'socket_escape_v5_partial.kicad_pcb'))
old_chg={t.m_Uuid.AsString()for t in base.GetTracks()if t.GetNetname()=='/CHG_N'}
removed=[]
def delete(t):removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()});b.Delete(t)
def same(q,v):return math.dist(q,v)<.00001
import math
for t in list(b.GetTracks()):
 n=t.GetNetname();a,z=xy(t.GetStart()),xy(t.GetEnd());isvia=isinstance(t,k.PCB_VIA)
 if n=='/CAM_TX' or (n=='/CHG_N'and t.m_Uuid.AsString()not in old_chg):delete(t);continue
 if n=='/CLR_N':
  if isvia and same(a,(30.1,15.9)):delete(t);continue
  if not isvia and (t.m_Uuid.AsString()in ['36b89055-9930-400d-b2c3-6b9acb68ec74','d0d3839d-51e3-4148-b2c1-4386d7e28f10','081c9d09-b704-4a36-a1f3-0077e019bb3f','d75b90aa-3499-472e-bcdc-c51d58367cd4'] or (t.GetLayer()==k.F_Cu and (same(a,(30.1,15.9))or(same(a,(48,15.9))and same(z,(48,27.9)))))):delete(t);continue
 if n in ['/ARM_Q','/ARM_FEEDBACK'] and not isvia and (same(a,(31.175,16.5))or same(z,(31.175,16.5))or same(a,(32.825,16.5))or same(z,(32.825,16.5))):delete(t);continue
 if n=='/FAULT_N'and (same(a,(37.6,13))or same(z,(37.6,13))):delete(t);continue
 if n=='/BAT_ADC_IN'and not isvia and (t.GetLayer()==k.B_Cu and same(a,(38.3,13.75)) or t.GetLayer()==k.F_Cu and (same(a,(58.5,10))or same(a,(54.75,13.75)))):delete(t);continue
 if n=='/WHEEL_ADC_IN'and not isvia and t.GetLayer()==k.F_Cu and (same(a,(60.5,10))or same(a,(56.45,5.95))):delete(t);continue
 if n=='/CURRENT_ADC_IN'and not isvia and t.GetLayer()==k.F_Cu and same(a,(62.5,10)):delete(t);continue
f=next(f for f in b.GetFootprints()if f.GetReference()=='R19');f.Move(pt(0,.2))
for z in b.Zones():
 if z.GetZoneName() in [a+'R19'+c for a in ['BODY_','NETBODY_','VIA_BODY_']for c in ['', '_OPPOSITE']]:z.Move(pt(0,.2))
routes=[
('/ARM_Q',k.B_Cu,[(31.175,15.138399),(31.175,16.7)]),
('/ARM_FEEDBACK',k.B_Cu,[(32.825,16.7),(32.825,23.5)]),
('/CLR_N',k.B_Cu,[(26.1112,15.849599),(29.249599,15.849599),(29.7,16.3)]),
('/CLR_N',k.B_Cu,[(29.7,16.3),(30,16)]),
('/CLR_N',k.F_Cu,[(30,16),(48,16),(48,27.9)]),
('/FAULT_N',k.B_Cu,[(34.2,13),(36.5,13)]),
('/FAULT_N',k.F_Cu,[(36.5,13),(54.5,13)]),
('/BAT_ADC_IN',k.B_Cu,[(38.3,13.75),(39.8,13.75),(39.8,16.75),(35.3,16.75)]),
('/BAT_ADC_IN',k.F_Cu,[(58.5,10),(58.5,13.75),(38.3,13.75)]),
('/WHEEL_ADC_IN',k.F_Cu,[(60.5,10),(60.5,5.95),(48.2,5.95)]),
('/CURRENT_ADC_IN',k.F_Cu,[(62.5,10),(62.5,13),(65.5,13),(68.1,15.6)]),
('/CAM_TX',k.B_Cu,[(37.45,10.75),(37.45,14.8),(37.925,15.275),(39,15.275)]),
('/CAM_TX',k.F_Cu,[(39,15.275),(52,15.275),(52.5,15.775),(52.5,18)]),
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
   problems.append((net,b.GetLayerName(l),a,z,hits[::max(1,len(hits)//5)]))
 track(b,net,qs,.2,l)
for net,q in [('/CLR_N',(30,16)),('/FAULT_N',(36.5,13)),('/CAM_TX',(39,15.275))]:
 if not Guard(b,net).via_clear(q):problems.append((net,'via',q,{b.GetLayerName(l):obstacles(b,net,q,l,.8,True)for l in[k.F_Cu,k.B_Cu]}))
 via(b,net,*q,vd=.8,dr=.3,grid=False)
dump(OUT/'compact_communications_guard.json',{'removed':removed,'routes':routes,'problems':problems})
k.SaveBoard(str(OUT/'compact_communications_start.kicad_pcb'),b)
print(json.dumps(problems,ensure_ascii=False,indent=2),flush=True)
assert not problems
class SocketGuard(Guard):
 def clear(self,q,layer,width=.2,is_via=False):
  for x1,y1,x2,y2 in [(5.85,.99,44.45,6.07),(5.85,28.93,44.45,34.01)]:
   if x1-width/2<=q[0]<=x2+width/2 and y1-width/2<=q[1]<=y2+width/2:return False
  return super().clear(q,layer,width,is_via)
r.Guard=SocketGuard;r.b=b;r.SEARCH_BOUNDS=(.6,69.4,.6,34.4);r.GRID_OFFSET=(0,.05)
cs=clusters(b,'/CHG_N');options=[[(q,l)for q,ls in c.items()for l in ls]for c in cs];options.sort(key=len,reverse=True);assert len(cs)==2
r.START_OPTIONS=options[0];result=r.plan('/CHG_N',options[0][0],options[1]);dump(OUT/'compact_CHG_route.json',result)
assert len(clusters(b,'/CHG_N'))==1
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
oldname,oldd,_=paths('motion','P5R6');(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
checks('motion','compact_communications')
