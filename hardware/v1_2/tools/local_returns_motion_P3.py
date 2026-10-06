"""Short local supply/ground bridges; ordinary signal escapes remain outward.

These named power-return exceptions are electrical loop choices, not DRC exclusions.
"""
import pcbnew as k,json
from layout_P3 import paths,xy,pt,track,via,F,B
_,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
thermal=set()
for q in fps['U100'].Pads():
 if q.GetNetname()=='/GND':
  x,y=xy(q.GetPosition())
  for dx,dy in [(-1.27,-1.27),(-1.27,1.27),(1.27,-1.27),(1.27,1.27)]:thermal.add((round(x+dx,5),round(y+dy,5)))
rip=['/+3V3','/CAM_TX','/LINK_RX','/FAULT_N','/HEAD_TX','/WHEEL_ADC_IN','/S288_OE_N']
for t in list(b.GetTracks()):
 if t.GetNetname() in rip or t.GetNetname()=='/GND' and (isinstance(t,k.PCB_VIA) and tuple(round(v,5) for v in xy(t.GetPosition())) not in thermal or not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())<.299):b.Delete(t)
for z in b.Zones():
 if z.GetIsRuleArea() and z.GetZoneName().startswith('OUTWARD_U'):z.SetDoNotAllowTracks(False)
# Native net-specific rule preserves outward signal routing while allowing short local returns.
dru=d/(d.name+'.kicad_dru');s=dru.read_text();s=s.split('# P3 local return exceptions')[0]
s+='\n# P3 local return exceptions: GND / +3V3 / CAM_3V3 under logic IC bodies.\n'
for ref in ['U1','U2','U3','U4','U5','U6']:
 cond="A.Type == 'Track' && A.Layer == 'B.Cu' && A.intersectsArea('OUTWARD_"+ref+"') && A.NetName != '/GND' && A.NetName != '/+3V3' && A.NetName != '/CAM_3V3'"
 s+='(rule "P3 outward signals '+ref+'" (condition '+json.dumps(cond)+') (constraint disallow track))\n'
dru.write_text(s)
# Routing these local fixed-rail pins inside their package perimeter shortens the decoupling return.
for net,points in [
 ('GND',[(26.45,9.25),(27.5,9.25),(28.5,10.25),(29.55,10.25)]),
 ('GND',[(21.75,22.95),(21.75,24),(20.75,25),(20.75,26.05)]),
 ('GND',[(35.45,11.75),(36.725,11.75),(36.725,14)]),
 ('+3V3',[(9.45,12.25),(12.55,12.25),(12.55,12.75)]),
 ('+3V3',[(18.55,11.75),(17,11.75),(17,9.275),(17.775,8.5)]),
 ('+3V3',[(35.45,11.25),(36.3,11.25),(36.3,10.075),(35.225,9)])]:track(b,net,points,.2,B)
# Keep the valid outer supply takeoffs and move the S288 enable below the ARM fanout.
for net,points in [('+3V3',[(9.45,12.25),(7.65,12.25)]),('+3V3',[(29.55,10.75),(30,10.75),(30.75,11.5),(30.75,12)]),('+3V3',[(24.25,20.225),(24.25,18.85)]),('S288_OE_N',[(18.55,11.25),(19.35,11.25),(20.9,12.8),(21.4,12.8)])]:
 via(b,net,*points[-1],grid=False);track(b,net,points,.2,B)
# Deleted conflict nets get short outward starts before the general router.
for f in fps.values():
 if not f.GetReference().startswith('U') or f.GetReference()=='U100':continue
 pads=list(f.Pads());cx,cy=xy(f.GetPosition());axis=0 if len(set(round(xy(q.GetPosition())[0],3) for q in pads))<=2 else 1
 for q in pads:
  if q.GetNetname() not in rip or q.GetNetname() in ['/+3V3','/S288_OE_N']:continue
  a=list(xy(q.GetPosition()));z=list(a);z[axis]+=.6*(1 if a[axis]>[cx,cy][axis] else -1);track(b,q.GetNet(),[a,z],.2,B)
k.SaveBoard(str(p),b)
