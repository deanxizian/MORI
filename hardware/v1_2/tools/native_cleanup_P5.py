"""Transactional copper cleanup, accepted only after KiCad's own DRC.

This does not suppress rules. Each edit is rejected if it introduces an
unconnected item or a new clearance/body/courtyard violation. Critical load
conductors are excluded from redundant-signal deletion.
"""
import sys,json,subprocess,math,collections
import pcbnew as k
from pathlib import Path
from layout_P5 import paths,xy,pt,mm
from geometry_guard_P5 import Guard
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
if not (r/'before_native_cleanup.kicad_pcb').exists():k.SaveBoard(str(r/'before_native_cleanup.kicad_pcb'),b)
accepted=r/'cleanup_accepted.kicad_pcb'
critical={'/GND','/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/KELVIN_P','/KELVIN_N',
 '/BAT_MON','/BAT_REV','/BAT_IN','/W9_IN','/W_PRE','/W_VM','/H6_IN','/H_PRE','/H_VM','/M5_VIN','/C5_VIN','/+5V_MOTION','/+5V_CAM'}
soft={'track_angle','track_not_centered_on_via','track_dangling','via_dangling','silk_over_copper','silk_overlap'}
log=[];calls=0
def inspect():
 global calls
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
 cmd=[cli,'pcb','drc','--severity-all','--all-track-errors','--refill-zones','--format','json','-o',str(r/'cleanup-drc.json'),str(p)]
 run=subprocess.run(cmd,capture_output=True,text=True);calls+=1
 if run.returncode:raise RuntimeError(run.stderr)
 return json.loads((r/'cleanup-drc.json').read_text())
def safe(j,old):
 if len(j['unconnected_items'])>len(old['unconnected_items']):return False
 a=collections.Counter(v['type'] for v in j['violations'] if v['type'] not in soft)
 z=collections.Counter(v['type'] for v in old['violations'] if v['type'] not in soft)
 return all(a[t]<=z[t] for t in a)
cur=inspect()
if cur['unconnected_items'] and '--allow-existing-open' not in sys.argv:raise SystemExit('Finish connections before transactional cleanup')
accepted.write_bytes(p.read_bytes())
def commit():
 accepted.write_bytes(p.read_bytes())
 (r/'native_cleanup.json').write_text(json.dumps(dict(native_drc_invocations=calls,changes=log),indent=2)+'\n')
def restore():
 global b
 p.write_bytes(accepted.read_bytes());b=k.LoadBoard(str(p))
# Place endpoints on the actual via centre. Guard prevents a new body route.
for row in list(cur['violations']):
 if row['type']!='track_not_centered_on_via':continue
 by={t.m_Uuid.AsString():t for t in b.GetTracks()};pair=[by.get(v['uuid']) for v in row['items']]
 vv=next((t for t in pair if t is not None and isinstance(t,k.PCB_VIA)),None)
 t=next((t for t in pair if t is not None and not isinstance(t,k.PCB_VIA)),None)
 if vv is None or t is None:continue
 pos=xy(vv.GetPosition());a,z=xy(t.GetStart()),xy(t.GetEnd());start=math.dist(a,pos)<math.dist(z,pos);near,far=(a,z) if start else (z,a)
 if math.dist(near,pos)>1.25 or not Guard(b,t.GetNetname()).line_clear(far,pos,t.GetLayer(),k.ToMM(t.GetWidth())):continue
 setter=t.SetStart if start else t.SetEnd;setter(pt(*pos));nxt=inspect()
 if safe(nxt,cur) and sum(v['type']=='track_not_centered_on_via' for v in nxt['violations'])<sum(v['type']=='track_not_centered_on_via' for v in cur['violations']):
  log.append(dict(action='centre_endpoint',uuid=t.m_Uuid.AsString(),net=t.GetNetname(),old=near,new=pos));cur=nxt;commit();print(kind,'centred',t.GetNetname(),flush=True)
 else:restore()
# Remove only copper proved unnecessary by the native checker, not an inferred
# geometric graph. Repeat because native dangling findings expose old tails.
tried=set()
for iteration in range(220):
 by={t.m_Uuid.AsString():t for t in b.GetTracks()};candidates=[]
 if '--plane-power-cleanup' in sys.argv:
  for uid,t in by.items():
   if uid not in tried and not isinstance(t,k.PCB_VIA) and t.GetNetname() in ['/+3V3','/GND'] and t.GetLength()>mm(.6):
    candidates.append((2,-k.ToMM(t.GetLength()),uid))
 for row in cur['violations']:
  typ=row['type']
  if typ not in {'track_angle','track_dangling','via_dangling'}:continue
  for it in row['items']:
   t=by.get(it['uuid'])
   if t is None or it['uuid'] in tried:continue
   dangling=typ in {'track_dangling','via_dangling'}
   if not dangling and (isinstance(t,k.PCB_VIA) or t.GetNetname() in critical or k.ToMM(t.GetWidth())>.25):continue
   candidates.append((0 if dangling else 1,0 if isinstance(t,k.PCB_VIA) else k.ToMM(t.GetLength()),it['uuid']))
 if not candidates:break
 _,_,uid=min(candidates);t=by[uid];tried.add(uid)
 info=dict(action='remove_redundant_or_dangling',uuid=uid,net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd()))
 b.Delete(t);nxt=inspect()
 if safe(nxt,cur) and (len(nxt['violations'])<len(cur['violations']) or not any(v['type']=='track_angle' and any(q['uuid']==uid for q in v['items']) for v in cur['violations'])):
  log.append(info);cur=nxt;commit();print(kind,'removed',info['net'],uid[:8],flush=True)
 else:restore()
# Ensure disk matches the accepted in-memory state, including the last reject.
cur=inspect();(r/'drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n')
(r/'native_cleanup.json').write_text(json.dumps(dict(native_drc_invocations=calls,changes=log),indent=2)+'\n')
print(kind,'native cleanup',len(log),'accepted edits',collections.Counter(v['type'] for v in cur['violations']),'unconnected',len(cur['unconnected_items']),flush=True)
