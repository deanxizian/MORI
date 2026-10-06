"""Independent control-routing candidate; P5 accepted artwork is not overwritten."""
import json,shutil,subprocess,sys,hashlib
import pcbnew as k
from layout_P5 import paths,F,B,xy,mm
from close_P5 import connected,clusters
from power_route_P5 import MAJOR
import route_P5 as rp
from functional_schematic import sexpr,encode
name,src,p,report=paths('power');d=report/'global_signals_trial';d.mkdir(exist_ok=True)
for f in src.iterdir():
 if f.is_file() and f.suffix not in ['.dsn','.ses']:shutil.copy2(f,d/f.name)
for sub in ['footprints']:
 shutil.copytree(src/sub,d/sub,dirs_exist_ok=True)
out=d/(name+'.kicad_pcb');b=k.LoadBoard(str(p));connected(b)
keepnets={'/GND','/KELVIN_N','/KELVIN_P','/M5_FB','/C5_FB','/M5_BOOT','/C5_BOOT','/BAT_ADC'}
kept=[];removed=[]
# Retain main load conductors and their vias; remove signal maze as a group.
loadnets=set(MAJOR)
for t in list(b.GetTracks()):
 keep=t.GetNetname() in keepnets or (not isinstance(t,k.PCB_VIA) and t.GetWidth()>=mm(.59)) or (isinstance(t,k.PCB_VIA) and t.GetNetname() in loadnets)
 (kept if keep else removed).append(t.m_Uuid.AsString())
 if not keep:b.Delete(t)
k.SaveBoard(str(out),b)
# Each major load must still connect through the protected wide copper.
checks={n:len(clusters(b,n,ts)) for n,ts in MAJOR.items()};print('load islands',checks,flush=True)
assert all(v==1 for v in checks.values()),checks
rp.paths=lambda _: (name,d,out,d)
rp.dsn('power')
fn=d/(name+'.dsn');tree=sexpr(fn.read_text());network=next(n for n in tree if isinstance(n,list) and n[0]=='network')
# Only new low-current branches are routed here. Wide load copper is protected.
for row in network:
 if not isinstance(row,list) or row[0]!='class':continue
 for rule in row:
  if isinstance(rule,list) and rule[0]=='rule':
   for entry in rule:
    if isinstance(entry,list) and entry[0]=='width':entry[1]='200'
fn.write_text(encode(tree)+'\n')
(d/'scope.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),retained=len(kept),removed=len(removed),load_checks=checks,not_accepted=True),indent=2)+'\n')
java='hardware/.tools/jdk-25.0.4.1+1-jre/Contents/Home/bin/java';jar='hardware/.tools/freerouting-2.4.1.jar'
cmd=[java,'-Xmx3g','-Djava.awt.headless=true','-jar',jar,'-de',str(fn),'-do',str(d/(name+'.ses')),'-mp','20','-mt','1','-oit','1','--gui.enabled=false']
with (d/'router.log').open('w') as log:q=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
print('router exit',q.returncode,flush=True)
if q.returncode==0:
 rp.import_ses('power')
 cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';cmd=[cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','-o',str(d/'drc.json'),str(out)]
 subprocess.run(cmd,check=True)
 j=json.loads((d/'drc.json').read_text());from collections import Counter
 print('candidate',Counter(v['type'] for v in j['violations']), 'opens',len(j['unconnected_items']),flush=True)
