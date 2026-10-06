#!/usr/bin/env python3
"""Respond to the seven user-marked routing regions; never edits P5 sources.
Run with KiCad Python. Rebuilds only this script's P5R1 motion candidate.
"""
from pathlib import Path
import pcbnew as k
import sys,json,shutil,hashlib,math
from layout_P5 import H,pt,xy,F,B,track
from close_P5 import connected
from geometry_guard_P5 import Guard
src=H/'kicad/MORI_motion_P5'; dest=H/'kicad/MORI_motion_P5R1'; report=H/'layout_P5R1/reports/MORI_motion_P5R1'
dest.mkdir(exist_ok=True);report.mkdir(parents=True,exist_ok=True)
for p in src.rglob('*'):
 if not p.is_file() or p.name.startswith('~') or p.suffix in ['.lck','.kicad_prl','.ses','.dsn']:continue
 rel=p.relative_to(src);target=dest/rel.parent/p.name.replace('MORI_motion_P5.','MORI_motion_P5R1.');target.parent.mkdir(parents=True,exist_ok=True)
 data=p.read_bytes()
 if p.suffix in ['.kicad_pro','.kicad_sch']:data=data.replace(b'MORI_motion_P5',b'MORI_motion_P5R1')
 target.write_bytes(data)
pcb=dest/'MORI_motion_P5R1.kicad_pcb';b=k.LoadBoard(str(pcb));connected(b);changes=[];new=[]
b.SetFileName(str(pcb))
def rem(ids):
 removed=[]
 for t in list(b.GetTracks()):
  if any(t.m_Uuid.AsString().startswith(s)for s in ids):removed.append(t.m_Uuid.AsString());b.Delete(t)
 assert len(removed)==len(ids),(ids,removed)
 return removed
def add(net,l,points,w=.2):
 ts=track(b,net,points,w,l);new.extend(ts)
 return dict(net=net,layer=b.GetLayerName(l),points=points,width=w,uuids=[t.m_Uuid.AsString()for t in ts])
def move_via(prefix,p):
 v=next(t for t in b.GetTracks()if t.m_Uuid.AsString().startswith(prefix));assert isinstance(v,k.PCB_VIA)
 old=xy(v.GetPosition());v.SetPosition(pt(*p));return {'uuid':v.m_Uuid.AsString(),'from':old,'to':p}
# A: ARM_CLK must first leave U5.1 upward, not sideward across the adjacent pin edge.
ids=rem(['0512357b','a5957eaa','ffc5a80f'])
paths=[add('/ARM_CLK',B,[(9.91,4.8),(9.91,5.55),(9.25,6.21),(9.25,8.825),(7.825,10.25)]),
 add('/ARM_CLK',B,[(10.25,7.95),(10.25,7.45),(9.75,6.95),(9.25,6.95)])]
changes.append(dict(mark='A',reason='Outward U5.1 fanout and deliberate upstream branch',removed=ids,routes=paths))
# B: aligned connector entries and two continuous F.Cu status lanes above C8.
ids=rem(['814183d6','861fc887','8737f5a3','baa2c714'])
paths=[add('/+5V_MOTION',B,[(41.79,6.2),(58.0,6.2),(58.5,5.7),(58.5,3.0)],.5)]
ids+=rem(['22685d18','2bc3af75','56b59202','6e579450','d2d422b7','e8c0b7f9'])
paths.append(add('/CHG_N',F,[(36.474399,3.556),(45.0088,3.556),(47.5528,6.1),(56.0,6.1),(56.5,6.6),(56.5,10.0)]))
ids+=rem(['1f128f0b','2a68179d','383dad8a','573f8a22','5dfae30f','6a63a722','9b9f5086','a30a724f','ea6352ce','883bee12'])
paths.append(add('/FAULT_N',F,[(36.3728,5.9944),(42.2656,5.9944),(42.8712,6.6),(54.0,6.6),(54.5,7.1),(54.5,10.0)]))
changes.append(dict(mark='B',reason='Remove offset endpoints and C8 detour while retaining body clearance',removed=ids,routes=paths))
# C: one exact vertical centerline instead of the 0.055601mm mismatch.
ids=rem(['2b480e9d','4c08ebb2','794df78d','be607fbe','0c7ed134'])
paths=[add('/HEAD_OE_N',B,[(18.75,13.05),(18.75,16.718001),(19.507199,17.4752),(19.507199,24.384)])]
changes.append(dict(mark='C',reason='Align HEAD_OE_N centerline; remove overlapping tiny offset',removed=ids,routes=paths))
# D/E: place the buffer series resistor above the two local rail exits.
def place_group(ref,pos,angle):
 f=next(f for f in b.GetFootprints()if f.GetReference()==ref);old=xy(f.GetPosition());oa=f.GetOrientationDegrees()
 pivot=f.GetPosition();rot=k.EDA_ANGLE(angle-oa,k.DEGREES_T);delta=pt(pos[0]-old[0],pos[1]-old[1])
 for z in b.Zones():
  if z.GetZoneName() in [f'BODY_{ref}',f'NETBODY_{ref}',f'BODY_{ref}_OPPOSITE',f'NETBODY_{ref}_OPPOSITE']:
   z.Rotate(pivot,rot);z.Move(delta)
 f.SetOrientationDegrees(angle);f.SetPosition(pt(*pos))
 return dict(ref=ref,old_position=old,old_angle=oa,new_position=pos,new_angle=angle)
ids=rem(['1cd40ac6','2f449003','43124b0f','780c7a61','e4d8fffd','e9f5e5b2','bf12c415','2bc41f41'])
v=move_via('34c9c24f',(19.95,16.764))
paths=[add('/HEAD_BUS',B,[(19.95,16.764),(19.95,21.65),(20.25,21.95)]),add('/HEAD_BUS',F,[(19.95,16.764),(20.2548,17.0688),(21.2344,17.0688)])]
changes.append(dict(mark='D',reason='Single pin-pitch escape into a continuous straight corridor; eliminate three unrelated offsets',removed=ids,moved_via=v,routes=paths))
ids=rem(['321c0158','cc8af10d','e3f9f3f1','deb815b4'])
c2=place_group('C2',(24.25,22.75),0)
vv=[move_via('1a181a8b',(22.75,21.15)),move_via('8815c29e',(26.4668,22.75))]
paths=[add('/+3V3',B,[(21.75,21.95),(21.75,21.65),(22.25,21.15),(22.75,21.15)]),add('/+3V3',B,[(22.75,21.15),(22.75,22.025),(23.475,22.75)]),add('/GND',B,[(25.025,22.75),(26.4668,22.75)])]
changes.append(dict(mark='E',reason='Translate C2 toward U2; retain capacitor orientation after alternative rotation trials collided with the analog corridor; place supply via at the deliberate corner',removed=ids,moved_component=c2,moved_vias=vv,routes=paths))
# F: locate the layer transition near U2.3, shorten the HEAD_RX return to A14.
ids=rem(['5c164237','a3bd3e01','c0f4dcb3','20338789','4b104e73','bae073e0','d0ef92f1','e47a8e9e'])
v=move_via('5ff5a3f5',(20.25,27.84))
paths=[add('/HEAD_RX',B,[(20.75,25.05),(20.75,27.34),(20.25,27.84)]),add('/HEAD_RX',F,[(20.25,27.84),(22.61,30.2)])]
changes.append(dict(mark='F',reason='Shorter HEAD_RX without lower-header sideways detour',removed=ids,moved_via=v,routes=paths))
# G: route directly from through-hole connector on B; delete both redundant vias.
ids=rem(['5f70762a','6cf7637e','9893f4c7','f6302fb6','3dc79d2f','ccdd72a9'])
paths=[add('/IMU_SCK',B,[(54.5,25.0),(54.5,23.156799),(54.000001,22.6568),(41.147999,22.6568)])]
ids+=rem(['76359f0e','96972e80','b8fe5b46','c57a65c6','c70435d1','1ae176d8','73452b4b','85ee11fb','bd872397'])
paths.append(add('/IMU_MOSI',B,[(56.5,25.0),(56.5,22.343998),(56.000001,21.843999),(46.228,21.843999)]))
changes.append(dict(mark='G',reason='Remove same-net folded overlap and two unnecessary vias at J4',removed=ids,routes=paths))
# Exact preflight shape screening is diagnostic; KiCad DRC remains authoritative.
issues=[]
for t in new:
 if not Guard(b,t.GetNetname()).line_clear(xy(t.GetStart()),xy(t.GetEnd()),t.GetLayer(),k.ToMM(t.GetWidth())):issues.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),a=xy(t.GetStart()),z=xy(t.GetEnd()),layer=b.GetLayerName(t.GetLayer())))
original=k.LoadBoard(str(src/'MORI_motion_P5.kicad_pcb'))
pinmap=lambda bb:{(f.GetReference(),p.GetNumber()):str(p.GetNetname())for f in bb.GetFootprints()for p in f.Pads()}
assert pinmap(original)==pinmap(b),'No GPIO/circuit changes authorized'
k.SaveBoard(str(pcb),b)
(report/'marked_changes.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((src/'MORI_motion_P5.kicad_pcb').read_bytes()).hexdigest(),changes=changes,guard_candidates=issues,pad_net_map_identical=True),ensure_ascii=False,indent=2)+'\n')
print('regions',len(changes),'guard candidates',issues,'output',pcb,flush=True)
