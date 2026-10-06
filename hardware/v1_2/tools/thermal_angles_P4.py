"""Try thermal-spoke rotations without changing gap/width/4-spoke rules."""
import sys,json,subprocess,collections
import pcbnew as k
from helpers_P4 import paths
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';log=[]
def inspect():
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 subprocess.run([cli,'pcb','drc','--severity-all','--all-track-errors','--refill-zones','--format','json','-o',str(r/'thermal-drc.json'),str(p)],capture_output=True,check=True)
 return json.loads((r/'thermal-drc.json').read_text())
def count(j):return sum(v['type']=='starved_thermal' for v in j['violations'])
cur=inspect();uids={i['uuid'] for v in cur['violations'] if v['type']=='starved_thermal' for i in v['items']}
for uid in uids:
 pad=next((q for f in b.GetFootprints() for q in f.Pads() if q.m_Uuid.AsString()==uid),None)
 if pad is None:continue
 for angle in [0,22.5,45,67.5,90]:
  pad=next(q for f in b.GetFootprints() for q in f.Pads() if q.m_Uuid.AsString()==uid);old=pad.GetThermalSpokeAngleDegrees()
  if abs(old-angle)<.001:continue
  backup=p.read_bytes();pad.SetThermalSpokeAngleDegrees(angle);nxt=inspect()
  aa=collections.Counter(v['type'] for v in nxt['violations']);zz=collections.Counter(v['type'] for v in cur['violations'])
  if count(nxt)<count(cur) and len(nxt['unconnected_items'])<=len(cur['unconnected_items']) and all(aa[t]<=zz[t] for t in aa if t!='starved_thermal'):
   log.append(dict(ref=pad.GetParentFootprint().GetReference(),pin=pad.GetNumber(),old_angle=old,new_angle=angle,before=count(cur),after=count(nxt)));cur=nxt;print(log[-1],flush=True)
  else:p.write_bytes(backup);b=k.LoadBoard(str(p))
cur=inspect();(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n');(r/'thermal_angles.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,'remaining thermals',count(cur))
