"""Move passives to open fine-pitch escape corridors; keep all pin/net identities."""
import pcbnew as k,json,shutil
from layout_P3 import paths,xy,pt,track,via,setplace,update_records,F,B
name,d,p,r=paths('motion');shutil.copy2(p,r/'before_corridor_trial.kicad_pcb');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
changes={'R1':(32.5,10.075,90),'R2':(20.925,19.75,180),'R5':(6,10.5,180),'C2':(24.25,21,270)}
log=[]
for ref,pos in changes.items():
 f=fps[ref];log.append(dict(ref=ref,before=[*xy(f.GetPosition()),f.GetOrientationDegrees()],after=pos));setplace(f,*pos,side='B')
names=['S288_TX_BUF','S288_BUS','HEAD_TX_BUF','HEAD_BUS','ARM_CLK','+3V3','ARM_Q_N','S288_OE_REQ_N','HEAD_OE_N','S288_OE_N']
for t in list(b.GetTracks()):
 if t.GetNetname().lstrip('/') in names or t.GetNetname()=='/GND' and not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<.299:b.Delete(t)
for z in list(b.Zones()):
 if not z.GetIsRuleArea():b.Delete(z)
for f in fps.values():
 if not f.GetReference().startswith('U') or f.GetReference()=='U100':continue
 pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(p.GetPosition())[0],3) for p in pads))<=2 else 1
 for pad in pads:
  if str(pad.GetNetname()).lstrip('/') not in names+['GND']:continue
  a=list(xy(pad.GetPosition()));z=list(a);z[axis]+=.8*(1 if a[axis]>[cx,cy][axis] else -1);track(b,pad.GetNet(),[a,z],.2,B)
# Two series resistors now align with their IC pins; no via required in either short local pair.
track(b,'S288_TX_BUF',[(29.55,9.75),(30.35,9.75),(31.5,10.9),(32.5,10.9)],.2,B)
track(b,'S288_BUS',[(29.55,9.25),(32.5,9.25)],.2,B)
track(b,'HEAD_TX_BUF',[(21.25,22.95),(21.25,20.25),(21.75,19.75)],.2,B)
track(b,'HEAD_BUS',[(20.75,22.95),(20.75,20.4),(20.1,19.75)],.2,B)
# The moved pull-down leaves room for VCC and ARM fanout on the formerly trapped side.
for net,start,target in [('+3V3',(9.45,12.25),(7.65,12.25)),('ARM_Q_N',(9.45,11.75),(8,11.15)),('ARM_Q_N',(15.45,11.25),(13.7,11.25)),('ARM_Q_N',(18.55,10.75),(20.3,10.75))]:
 z=via(b,net,*target,grid=False)
 if abs(start[1]-z[1])<.01:points=[start,z]
 else:points=[start,(z[0]+abs(z[1]-start[1]),start[1]),z]
 track(b,net,points,.2,B)
update_records('motion',b,json.loads((d/'connectivity.json').read_text()));k.SaveBoard(str(p),b);(r/'corridor_placement_changes.json').write_text(json.dumps(log,indent=2)+'\n')
