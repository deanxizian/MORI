"""Read-only courtyard search. Not a routed/qualified board."""
import sys, json, math
from pathlib import Path
import wx, pcbnew as k
app=wx.App(False)
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'hardware/v1_2/tools'))
from layout_P5 import xy,pt,rect,courtyard,box,hit
SOURCE=HERE.parent/'j10_candidate/MORI_power_P5R7_J10_CANDIDATE/MORI_power_P5R7_J10_CANDIDATE.kicad_pcb'
b=k.LoadBoard(str(SOURCE)); fs={f.GetReference():f for f in b.GetFootprints()}
inventory={r:dict(xy_mm=xy(f.GetPosition()),rotation_deg=f.GetOrientationDegrees(),body=rect(f),court=courtyard(f),pads=[dict(pin=p.GetNumber(),xy_mm=xy(p.GetPosition()),net=p.GetNetname())for p in f.Pads()]) for r,f in fs.items()}
(HERE/'footprints_C1.json').write_text(json.dumps(inventory,indent=2)+'\n')
# Provisional minimum withdrawal +0.5mm margin; must be screened in 3D.
reserved=[30.9,25.05,45.85,42.95]
cost=lambda ref:1000 if ref.startswith(('J','H','L')) and not ref.startswith('JP') else 100 if ref in ['U60','U70','C60','C61','C62','C65','C66','R60','R61','C70','C71','C72','C75','C76','R70','R71'] else 60 if ref in ['C10','C30','Q1','Q90','Q10','Q30','R2','D10'] else 6 if ref.startswith(('U','Q')) else 3 if ref.startswith(('F','D')) else 1
rank=[];f=fs['D30']
for deg in [0,90,180,270]:
 f.SetOrientationDegrees(deg)
 for xx in range(20,141):
  x=xx/2
  for yy in range(20,99):
   y=yy/2;f.SetPosition(pt(x,y));c=courtyard(f)
   if c[0]<.8 or c[1]<.8 or c[2]>79.2 or c[3]>54.2 or hit(c,reserved,.3):continue
   collisions=[r for r in fs if r!='D30' and hit(c,inventory[r]['court'],.1)]
   score=sum(cost(r)for r in collisions)+.08*math.dist((x,y),(44,42))
   if score<20:rank.append(dict(score=score,xy_mm=[x,y],rotation_deg=deg,collisions=collisions,court=c))
rank.sort(key=lambda q:q['score'])
distinct=[]
for r in rank:
 if not any(math.dist(r['xy_mm'],q['xy_mm'])<2 and r['collisions']==q['collisions'] for q in distinct):distinct.append(r)
 if len(distinct)>=30:break
(HERE/'D30_search.json').write_text(json.dumps(dict(reserved=reserved,ranked=distinct,meaning='Courtyard-only search; electrical/thermal/3D checks not implied'),indent=2)+'\n')
print(json.dumps(distinct[:15],indent=2))
