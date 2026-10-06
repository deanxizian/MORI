"""Reconnect power-carrying terminals first, retaining P3 load widths.
No narrow-signal fallback is permitted for these jobs. Native DRC and later
width/connectivity review are mandatory. Existing connected paths are skipped.
"""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,xy,track,via,pt,mm,F,B
from route_local_P3R1 import connect
from geometry_guard_P3R1 import Guard
from close_routes_P2 import merge_lines
name,d,p,r=paths('power');b=k.LoadBoard(str(p));pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
def pad(key):return pads[key[0],str(key[1])]
def connected(a,z,width):
 c=k.CONNECTIVITY_DATA();c.Build(b);target=z.m_Uuid.AsString();seen=set();q=[a]
 while q:
  u=q.pop();uid=u.m_Uuid.AsString()
  if uid==target:return True
  if uid in seen:continue
  seen.add(uid)
  for t in c.GetConnectedTracks(u):
   if t.Type()==k.PCB_VIA_T:q.append(t);continue
   tw=k.ToMM(t.GetWidth())
   if tw>=width-.001:q.append(t);continue
   # Documented short necks at MOS banks, shunt or narrow power pads.
   near=c.GetConnectedPads(t)
   if tw>=.35-.001 and t.GetLength()<=mm(2) and any(v.GetParentFootprint().GetReference()=='J17' for v in near):q.append(t);continue
   if tw>=.6-.001 and t.GetLength()<=mm(3) and any(v.GetParentFootprint().GetReference() in ['Q1','Q10','Q30','Q20','Q40','R2'] for v in near):q.append(t)
  q.extend(c.GetConnectedPads(u))
 return False
# External wide buses avoid crossing an AO4407A body. Their .6 mm short
# parallel pad necks are unchanged; jobs start on the outside broad bus.
jobs=[
 ('BAT_IN',('J1',2),('Q1',7),2,(8.925,14.365)),
 ('BAT_REV',('R2',1),('Q1',2),2,(17.075,14.365)),
 ('BAT_MON',('R2',2),('J2',2),2,None),
 ('BAT_MON',('J2',2),('J4',2),2,None),
 ('BAT_MON',('J2',2),('F60',1),1,None),
 ('BAT_MON',('J2',2),('F70',1),1,None),
 ('BAT_MON',('J2',2),('J6',2),2,None),
 ('W9_IN',('J3',2),('D10',2),1.5,None),
 ('W_PRE',('D10',1),('Q10',2),1.5,(38.225,22.635)),
 ('W_VM',('C10',1),('Q10',6),1.5,(46.775,21.365)),
 ('W_VM',('C10',1),('J7',2),1.5,None),
 ('W_VM',('J7',2),('J8',2),1.5,None),
 ('W_VM',('J7',2),('J11',2),1.5,None),
 
 ('H6_IN',('J5',2),('D30',2),1,None),
 ('H_PRE',('D30',1),('Q30',2),1,(32.825,35.135)),
 ('H_VM',('C30',1),('Q30',6),1,(40.175,33.865)),
 ('H_VM',('C30',1),('J9',2),1,None),
 ('H_VM',('J9',2),('J12',2),1,None),
 
 ('M5_VIN',('F60',2),('C60',1),.8,None),
 ('M5_VIN',('C60',1),('C66',1),.8,None),
 ('M5_VIN',('C60',1),('C61',1),.8,None),
 ('C5_VIN',('F70',2),('C70',1),.8,None),
 ('C5_VIN',('C70',1),('C76',1),.8,None),
 ('C5_VIN',('C70',1),('C71',1),.8,None),
 ('+5V_MOTION',('L60',2),('C63',1),1,None),
 ('+5V_MOTION',('L60',2),('J17',1),.8,None),
 ('+5V_CAM',('L70',2),('C73',1),1,None),
 ('+5V_CAM',('L70',2),('J18',1),.8,None),
 ('W_DUMP_D',('J11',1),('Q20',3),1,None),
 ('H_DUMP_D',('J12',1),('Q40',3),1,None),
]
log=[]
for net,a,z,w,anchor in jobs:
 try:
  pa,pz=pad(a),pad(z);net='/'+net
  assert pa.GetNetname()==pz.GetNetname()==net,(a,z,net,pa.GetNetname(),pz.GetNetname())
  if connected(pa,pz,w):log.append(dict(net=net,pins=[a,z],status='ALREADY_CONNECTED',minimum_route_width_mm=w));continue
  ap=xy(pa.GetPosition());zp=anchor or xy(pz.GetPosition());
  if a==('R2',1):ap=(20.8,15)
  if a==('R2',2):ap=(29.2,15)
  if z==('J17',1):zp=(8.1,20.625)
  if z==('Q40',3):zp=(76,45)
  if z==('Q1',2):zp=(17.0,14.3)
  al=[l for l in [F,B] if pa.IsOnLayer(l)];zl=[B] if anchor else [l for l in [F,B] if pz.IsOnLayer(l)]
  if anchor:
   # The bank must actually still reach its terminal before using it.
   assert any(t.GetNetname()==net and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(pt(*anchor),mm(.01)) for t in b.GetTracks()),('missing outside bank',a,z,anchor)
  # Reuse the nearest existing wide conductor in the source terminal's
  # native connected component. This avoids a redundant end-to-end trunk.
  c=k.CONNECTIVITY_DATA();c.Build(b);seen=set();queue=[pa];candidates=[(ap,al)]
  while queue:
   obj=queue.pop();uid=obj.m_Uuid.AsString()
   if uid in seen:continue
   seen.add(uid)
   if isinstance(obj,k.PCB_TRACK) and obj.Type()!=k.PCB_VIA_T and k.ToMM(obj.GetWidth())>=w-.001:
    ol=[l for l in [F,B] if obj.IsOnLayer(l)]
    candidates.extend([(xy(obj.GetStart()),ol),(xy(obj.GetEnd()),ol)])
   for t in c.GetConnectedTracks(obj):
    if t.GetNetname()!=net:continue
    if t.Type()==k.PCB_VIA_T or k.ToMM(t.GetWidth())>=min(w,.6)-.001:queue.append(t)
   queue.extend(q for q in c.GetConnectedPads(obj) if q.GetNetname()==net)
  candidates.sort(key=lambda v:__import__('math').dist(v[0],zp))
  for start,layers in candidates[:4]:
   try:
    result=connect(b,net,start,zp,layers,zl,(80,55),step=.05,width=w,vd=1,dr=.45,max_nodes=400000,time_limit=15);break
   except RuntimeError as exc:last_error=exc
  else:raise last_error
  log.append(dict(pins=[a,z],status='ROUTED',minimum_route_width_mm=w,**result))
 except (RuntimeError,AssertionError,KeyError) as e:log.append(dict(pins=[a,z],net=net,status='BLOCKED',minimum_route_width_mm=w,reason=str(e)));print('BLOCKED LOAD',a,z,str(e),flush=True)
 k.SaveBoard(str(p),b);(r/'load_path_reconnections.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
merge_lines(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
print('Power load reconnection pass complete',flush=True)
