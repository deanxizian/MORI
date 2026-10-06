"""Screen thermal spoke orientation, preserving gap, width and four-spoke rule."""
import sys,json,subprocess,collections
import pcbnew as k
from layout_P3R1 import paths
kind=sys.argv[1];_,_,p,r=paths(kind);cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def inspect(b):
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 subprocess.run([cli,'pcb','drc','--severity-all','--all-track-errors','--refill-zones','--format','json','-o',str(r/'thermal-drc.json'),str(p)],capture_output=True,check=True)
 return json.loads((r/'thermal-drc.json').read_text())
b=k.LoadBoard(str(p));cur=inspect(b);targets={i['uuid'] for row in cur['violations'] if row['type']=='starved_thermal' for i in row['items']};log=[]
for uid in sorted(targets):
 pad=next((q for f in b.GetFootprints() for q in f.Pads() if q.m_Uuid.AsString()==uid),None)
 if pad is None:continue
 before=p.read_bytes();old=pad.GetThermalSpokeAngle().AsDegrees() if hasattr(pad,'GetThermalSpokeAngle') else None
 base=sum(v['type']=='starved_thermal' for v in cur['violations']);choice=None
 for angle in [0,15,30,45,60,75]:
  p.write_bytes(before);b=k.LoadBoard(str(p));pad=next(q for f in b.GetFootprints() for q in f.Pads() if q.m_Uuid.AsString()==uid);pad.SetThermalSpokeAngleDegrees(angle);nxt=inspect(b)
  count=sum(v['type']=='starved_thermal' for v in nxt['violations'])
  aa=collections.Counter(v['type'] for v in nxt['violations'] if v['type']!='starved_thermal');zz=collections.Counter(v['type'] for v in cur['violations'] if v['type']!='starved_thermal')
  if count<base and len(nxt['unconnected_items'])<=len(cur['unconnected_items']) and all(aa[t]<=zz[t] for t in aa):
   choice=angle;log.append(dict(ref=pad.GetParentFootprint().GetReference(),pin=pad.GetNumber(),angle=angle,remaining_thermal_findings=count));cur=nxt;print(kind,log[-1],flush=True);break
 if choice is None:p.write_bytes(before);b=k.LoadBoard(str(p))
cur=inspect(b);(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n');(r/'thermal_angle_screen.json').write_text(json.dumps(log,indent=2)+'\n')
print(kind,'thermal findings',sum(v['type']=='starved_thermal' for v in cur['violations']),flush=True)
