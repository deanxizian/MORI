#!/usr/bin/env python3
"""Recorded local P2 routing/check commands. Never purchase or export fabrication."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json
R=Path(__file__).resolve().parents[1];ROOT=R.parents[1]
PY='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
JAVA=ROOT/'hardware/.tools/jdk-25.0.4.1+1-jre/Contents/Home/bin/java'
JAR=ROOT/'hardware/.tools/freerouting-2.4.1.jar'
kind,action=sys.argv[1:3];name='MORI_'+kind+'_P2';d=R/'kicad'/name;o=R/'layout_P2/reports'/name;o.mkdir(parents=True,exist_ok=True)
commands=[]
if action=='route':
    dsn=d/(name+'.dsn');dsn.write_text(dsn.read_text().replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))'))
    commands=[[str(JAVA),'-Xmx3g','-Djava.awt.headless=true','-jar',str(JAR),'-de',str(dsn),'-do',str(d/(name+'.ses')),'-mp','45','-mt','1','-oit','1','--gui.enabled=false']]
elif action=='import':commands=[[PY,str(R/'tools/layout_P2.py'),kind,a] for a in ['import','finish']]
elif action=='check':
    commands=[[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(o/'drc.json'),str(d/(name+'.kicad_pcb'))],
      [CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(o/'erc.json'),str(d/(name+'.kicad_sch'))],
      [CLI,'sch','export','netlist','--format','kicadxml','-o',str(o/'netlist.xml'),str(d/(name+'.kicad_sch'))]]
else:raise SystemExit(action)
log=[]
for i,cmd in enumerate(commands):
    t=datetime.now(timezone.utc).isoformat();p=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
    f=o/(action+'_'+str(i)+'.log');f.write_text(p.stdout+p.stderr)
    log.append(dict(argv=cmd,utc=t,returncode=p.returncode,output=str(f.relative_to(R))))
    print(action,kind,i,'exit',p.returncode,flush=True)
    if p.returncode and action!='check':print((p.stdout+p.stderr)[-3000:]);break
(o/(action+'_commands.json')).write_text(json.dumps(log,indent=2)+'\n')
if action=='check' and (o/'drc.json').exists():
    drc=json.loads((o/'drc.json').read_text());from collections import Counter
    print('DRC',Counter(x['type'] for x in drc['violations']),'unconnected',len(drc['unconnected_items']),'parity',len(drc['schematic_parity']))
if any(l['returncode'] for l in log):sys.exit(1)
