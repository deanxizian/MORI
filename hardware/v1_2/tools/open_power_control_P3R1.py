"""Orient the reference and head-gate networks toward the pins they serve.

Reserves local outward ports; does not alter values, pin identity or netlist.
Critical switch-node bootstrap branches are kept on F.Cu without vias.
"""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,setplace,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import obstacles
name,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};moves=[];removed=[];log=[]
for ref,pos in [('U21',(55,15,270)),('R20',(55,11,270)),('R31',(30.625,32.6,180)),('R30',(31.45,35,270))]:
 f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees())
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==q.GetNetCode() and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.001)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
 setplace(f,*pos,'B');moves.append(dict(ref=ref,before=old,after=pos))
 for t in list(b.GetTracks()):
  if any(t.IsOnLayer(B) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=q.GetNetCode()) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.205)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
create(b)
# Remove only the low-current bootstrap tap of each switch node.
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/M5_SW','/C5_SW'] and (isinstance(t,k.PCB_VIA) or k.ToMM(t.GetWidth())<.5):removed.append(t.m_Uuid.AsString());b.Delete(t)
jobs=[
 ('/W_REF',[(54.05,14.0625),(54.05,13.1),(55.95,13.1),(55.95,14.0625)],B,False),
 ('/W_REF',[(55,11.825),(55,13.1)],B,True),
 ('/W_REF',[(60.525,14.135),(58.9,14.135)],B,True),
 ('/W_REF',[(65.475,11.595),(67,11.595)],B,True),
 ('/H_GATE',[(34.025,32.595),(31.45,32.595),(31.45,34.175)],B,False),
 ('/H_PRE',[(31.45,35.825),(32.825,35.825)],B,False),
 ('/H_GATE_LOW',[(29.8,32.6),(28.2,32.6)],B,True),
 ('/H_GATE_LOW',[(43.4375,32),(44.9,32),(44.9,32.4)],B,True),
 ('/H_BRAKE_GATE',[(69,33.175),(69,31.6)],B,True),
 ('/FAULT_N',[(43.125,30.95),(43.125,34.0)],F,True),
 ('/BAT_ADC',[(45.625,30.95),(45.625,33.0)],F,True),
 ('/CURRENT_ADC',[(48.125,30.95),(48.125,33.0)],F,True),
 ('/CHG_N',[(55.375,31.95),(55.375,36.0)],F,True),
 ('/M5_SW',[(23.225,20),(24.9,20),(25.4,19.5),(30.225,19.5)],F,False),
 ('/C5_SW',[(23.225,40),(24.9,40),(25.4,39.5),(30.225,39.5)],F,False)]
for net,ps,layer,want_via in jobs:
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};bad=set();blocked=[]
 for a,z in zip(ps,ps[1:]):
  for i in range(121):
   pos=(a[0]+(z[0]-a[0])*i/120,a[1]+(z[1]-a[1])*i/120)
   for uid,info in obstacles(b,net,pos,layer):
    if uid in ts:bad.add(uid)
    else:blocked.append((uid,info))
 if want_via:
  for ll in [F,B]:
   for uid,info in obstacles(b,net,ps[-1],ll,.8,True):
    if uid in ts:bad.add(uid)
    else:blocked.append((uid,info))
 # Never displace a load conductor while reserving a control signal.
 for uid in bad:
  t=ts[uid]
  if not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())>.4 and t.GetNetname()!='/GND':blocked.append((uid,'LOAD_CONDUCTOR'))
 if blocked:log.append(dict(net=net,points=ps,status='BLOCKED',obstacles=sorted(set(blocked))));print('BLOCKED PORT',net,sorted(set(blocked)),flush=True);continue
 for uid in bad:removed.append(uid);b.Delete(ts[uid])
 track(b,net,ps,.2,layer)
 if want_via and not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),ps[-1])<.01 for t in b.GetTracks()):via(b,net,*ps[-1],grid=False)
 log.append(dict(net=net,points=ps,status='ROUTED'))
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'power_control_corridors.json').write_text(json.dumps(dict(moves=moves,ports=log,removed=removed),ensure_ascii=False,indent=2)+'\n')
