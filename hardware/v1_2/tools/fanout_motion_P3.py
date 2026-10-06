"""Reserved fine-pitch escapes after actual corridor trials. P3 only."""
import pcbnew as k,json,shutil
from layout_P3 import paths,xy,pt,track,via,setplace,update_records,F,B
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));shutil.copy2(p,r/'before_reserved_fanout.kicad_pcb');fps={f.GetReference():f for f in b.GetFootprints()}
setplace(fps['R1'],33.5,10.075,90,side='B')
names=['ARM_Q','S288_TX_BUF','S288_BUS','HEAD_OE_N','S288_OE_REQ_N','S288_OE_N','+3V3','ARM_Q_N']
thermal=set()
for q in fps['U100'].Pads():
 if q.GetNetname()=='/GND':
  x,y=xy(q.GetPosition())
  for dx,dy in [(-1.27,-1.27),(-1.27,1.27),(1.27,-1.27),(1.27,1.27)]:thermal.add((round(x+dx,5),round(y+dy,5)))
for t in list(b.GetTracks()):
 if t.GetNetname().lstrip('/') in names or t.GetNetname()=='/GND' and (isinstance(t,k.PCB_VIA) and tuple(round(v,5) for v in xy(t.GetPosition())) not in thermal or not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<.299):b.Delete(t)
for z in list(b.Zones()):
 if not z.GetIsRuleArea():b.Delete(z)
# Outward from the package perimeter; special fanouts below supersede generic stubs.
for f in fps.values():
 if not f.GetReference().startswith('U') or f.GetReference()=='U100':continue
 pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(q.GetPosition())[0],3) for q in pads))<=2 else 1
 for q in pads:
  if str(q.GetNetname()).lstrip('/') not in names:continue
  a=list(xy(q.GetPosition()));z=list(a);z[axis]+=.4*(1 if a[axis]>[cx,cy][axis] else -1);track(b,q.GetNet(),[a,z],.2,B)
# Series link aligns with resistor pin 1; the extra 1 mm of placement opens GND fanout.
track(b,'S288_TX_BUF',[(29.55,9.75),(32.35,9.75),(33.5,10.9)],.2,B)
track(b,'S288_BUS',[(29.55,9.25),(33.5,9.25)],.2,B)
jobs=[
 ('ARM_Q',[(12.55,11.25),(12.95,11.25),(12.95,9.85),(12.8,9.7)]),
 ('ARM_Q_N',[(9.45,11.75),(8.6,11.75),(8,11.15)]),
 ('ARM_Q_N',[(15.45,11.25),(13.7,11.25)]),
 ('ARM_Q_N',[(18.55,10.75),(20.3,10.75)]),
 ('S288_OE_REQ_N',[(15.45,11.75),(14.65,11.75),(14.65,12.5),(15.15,13),(15.6,13)]),
 ('S288_OE_N',[(18.55,11.25),(19.4,11.25),(19.55,11.1),(21.4,11.1)]),
 ('HEAD_OE_N',[(15.45,10.75),(14.6,10.75),(14.1,10.25)]),
 ('HEAD_OE_N',[(22.25,26.05),(22.25,27.5)]),
 ('+3V3',[(9.45,12.25),(7.65,12.25)]),
 ('+3V3',[(12.55,12.25),(13.25,12.25),(14,13)]),
 ('+3V3',[(12.55,12.75),(13.75,12.75),(14,13)]),
 ('+3V3',[(18.55,11.75),(19.95,11.75),(20.3,12.1)]),
 ('+3V3',[(29.55,10.75),(30,10.75),(30.75,11.5),(30.75,12)]),
 ('+3V3',[(35.45,11.25),(34.6,11.25),(33.9,11.95),(33.9,12)]),
 ('+3V3',[(24.25,20.225),(24.25,18.85)]),
 ('GND',[(29.55,10.25),(30.65,10.25),(31,10.6)]),
 ('GND',[(35.45,11.75),(34.95,11.75),(34.15,12.55),(34.15,13.25)]),
 ('GND',[(21.75,22.95),(21.75,20.8)])]
seen=set()
for net,points in jobs:
 target=points[-1];key=(net,target)
 if key not in seen:via(b,net,*target,grid=False);seen.add(key)
 track(b,net,points,.2,B)
update_records('motion',b,json.loads((d/'connectivity.json').read_text()));k.SaveBoard(str(p),b)
(r/'reserved_fanout.json').write_text(json.dumps(jobs,indent=2)+'\n')
