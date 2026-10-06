"""Isolated Specctra routing trial; never overwrites the active native board."""
import sys,json,subprocess,hashlib
import pcbnew as k
from layout_P3R1 import paths
from functional_schematic import sexpr,encode
kind=sys.argv[1];name,d,p,r=paths(kind);o=r/'routing_trial';o.mkdir(exist_ok=True)
b=k.LoadBoard(str(p));k.SaveBoard(str(o/'before.kicad_pcb'),b);dsn=o/'trial.dsn';ses=o/'trial.ses'
assert k.ExportSpecctraDSN(b,str(dsn));tree=sexpr(dsn.read_text())
wiring=next(x for x in tree if isinstance(x,list) and x[0]=='wiring');protected=0
critical={'/KELVIN_P','/KELVIN_N','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/M5_FB','/C5_FB'}
for row in wiring[1:]:
 if not isinstance(row,list):continue
 net=next((x[1] for x in row if isinstance(x,list) and x[0]=='net'),None)
 path=next((x for x in row if isinstance(x,list) and x[0]=='path'),None)
 large=(path is not None and float(path[2])>250) or (row[0]=='via' and '1000:' in row[1])
 if large or net in critical:
  t=next((x for x in row if isinstance(x,list) and x[0]=='type'),None)
  if t:t[1]='protect';protected+=1
dsn.write_text(encode(tree).replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))')+'\n')
root=d.parents[3];java=root/'hardware/.tools/jdk-25.0.4.1+1-jre/Contents/Home/bin/java';jar=root/'hardware/.tools/freerouting-2.4.1.jar'
cmd=[str(java),'-Xmx3g','-Djava.awt.headless=true','-jar',str(jar),'-de',str(dsn),'-do',str(ses),'-mp','30','-mt','1','-oit','1','--gui.enabled=false']
(o/'command.json').write_text(json.dumps(dict(argv=cmd,protected_wires=protected,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=2)+'\n')
with (o/'router.log').open('w') as f:run=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
print('router exit',run.returncode,flush=True)
if ses.exists():
 assert k.ImportSpecctraSES(b,str(ses));k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(o/'candidate.kicad_pcb'),b)
 cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
 subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(o/'candidate_drc.json'),str(o/'candidate.kicad_pcb')],check=True)
 report=json.loads((o/'candidate_drc.json').read_text());from collections import Counter
 print(Counter(x['type'] for x in report['violations']),len(report['unconnected_items']),flush=True)
