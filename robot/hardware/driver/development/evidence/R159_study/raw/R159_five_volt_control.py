"""Native causal control: does the lower 5 V via/trunk still transfer functional power?
This is not a deletion authorization or layout candidate. All source bytes retained.
"""
import sys,json,shutil,subprocess,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');source=Path('robot/hardware/driver/development/native');out=b/'R159-M5V-control';assert not out.exists();shutil.copytree(source,out,ignore=shutil.ignore_patterns('*.kicad_prl','*.lck'))
c=Copper(source/'MORI_Interface_C3.kicad_pcb');ids=['c9ef7bb5-bef9-48b7-b4cf-23501fe0a859','99ab00bb-6229-4bbd-bcab-fda844037095'];snap=[]
for id_ in ids:
 t=c.by_id[id_];snap.append({'uuid':id_,'type':type(t).__name__,'net':t.GetNetname()});assert t.GetNetname()=='/01 {slash} Core/MOTION_5V';c.board.Remove(t)
board=out/'MORI_Interface_C3.kicad_pcb';pcb.SaveBoard(str(board),c.board)
(out/'diagnostic.json').write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'removed':snap,'not_adopted':True},indent=2)+'\n')
py=str(Path('robot/.state/c3-completion/venv/bin/python').absolute());records=[]
for tag,cmd,allowed in [('native',['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--refill-zones','--save-board','--severity-all','--exit-code-violations','-o',str(out/'drc.json'),str(board)],(0,5)),('audit',[py,'robot/hardware/driver/development/scripts/audit_candidate.py',str(source/'MORI_Interface_C3.kicad_pcb'),str(board),str(out/'audit.json')],(0,))]:
 t=time.time();r=subprocess.run(cmd,capture_output=True,text=True);records.append({'step':tag,'argv':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'seconds':time.time()-t});(out/'commands.json').write_text(json.dumps(records,indent=2)+'\n');assert r.returncode in allowed
 print(tag,r.returncode,flush=True)
a=json.loads((out/'audit.json').read_text());d=json.loads((out/'drc.json').read_text());removed_via=ids[0]
fail=[{'net':r['net'],'width':r['width_mm'],'lost_pairs':len(r['lost_pairs']),'lost_pairs_without_removed_via':len([q for q in r['lost_pairs'] if removed_via not in q])} for r in a['power_width'] if r['status']!='PASS']
r={'source_sha256':c.sha,'candidate_sha256':hashlib.sha256(board.read_bytes()).hexdigest(),'native':{k:len(d[k]) for k in ['unconnected_items','violations','schematic_parity']},'strict_power_failures':fail,'lost_pad_nets':[{'net':r['net'],'pairs':len(r['lost_pad_pairs'])} for r in a['lost_pad_connections']],'old_reference_loss_count':len(a['retained_trace_reference_loss']),'not_a_candidate':True}
(out/'screen.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
