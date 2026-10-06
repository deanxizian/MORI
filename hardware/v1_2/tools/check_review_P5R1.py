#!/usr/bin/env python3
"""Native checks, source hashes, body inventory, and actual review exports."""
from pathlib import Path
import pcbnew as k
import sys,json,hashlib,subprocess,re
H=Path(__file__).resolve().parents[1]; ROOT=H.parents[1]
name='MORI_motion_P5R1'; d=H/'kicad'/name;p=d/(name+'.kicad_pcb');out=H/'layout_P5R1';r=out/'reports'/name;r.mkdir(parents=True,exist_ok=True)
cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';action=sys.argv[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def inputs():return {str(f.relative_to(ROOT)):sha(f) for f in sorted(d.rglob('*'))if f.is_file() and f.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_mod','.kicad_sym']}
def run(args):
 result=subprocess.run(args,capture_output=True,text=True,timeout=300)
 return {'argv':args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
if action=='check':
 from datetime import datetime,timezone
 commands=[[cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(r/'drc.json'),str(p)], [cli,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(r/'erc.json'),str(d/(name+'.kicad_sch'))], [cli,'sch','export','netlist','--format','kicadxml','-o',str(r/'netlist.xml'),str(d/(name+'.kicad_sch'))]]
 logs=[]
 for i,args in enumerate(commands):
  log={'utc':datetime.now(timezone.utc).isoformat(),'input_sha256':inputs(),**run(args)};logs.append(log);(r/f'check_{i}.log').write_text(log['stdout']+log['stderr']);print(i,log['returncode'],flush=True)
 (r/'check_commands.json').write_text(json.dumps(logs,indent=2)+'\n')
 if any(x['returncode']for x in logs):raise SystemExit(1)
elif action=='audit':
 import layout_P5
 layout_P5.paths=lambda kind:(name,d,p,r)
 import audit_body_P5
 audit_body_P5.audit('motion')
 old=k.LoadBoard(str(H/'kicad/MORI_motion_P5/MORI_motion_P5.kicad_pcb'));b=k.LoadBoard(str(p))
 from layout_P5 import xy
 stats=lambda bb:{'tracks':sum(not isinstance(t,k.PCB_VIA) for t in bb.GetTracks()),'vias':sum(isinstance(t,k.PCB_VIA) for t in bb.GetTracks()),'track_length_mm':round(sum(k.ToMM(t.GetLength())for t in bb.GetTracks()if not isinstance(t,k.PCB_VIA)),3)}
 padmap=lambda bb:{f.GetReference()+'.'+q.GetNumber():str(q.GetNetname())for f in bb.GetFootprints()for q in f.Pads()}
 fps=lambda bb:{f.GetReference():{'position':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'layer':bb.GetLayerName(f.GetLayer())}for f in bb.GetFootprints()}
 before,after=fps(old),fps(b)
 j={'source_pcb_sha256':sha(H/'kicad/MORI_motion_P5/MORI_motion_P5.kicad_pcb'),'output_pcb_sha256':sha(p),'before':stats(old),'after':stats(b),'pad_net_map_identical':padmap(old)==padmap(b),'changed_placements':{ref:{'before':before[ref],'after':after[ref]}for ref in before if before[ref]!=after[ref]},'inner_signal_tracks':sum(not isinstance(t,k.PCB_VIA) and t.GetLayer()not in[k.F_Cu,k.B_Cu]for t in b.GetTracks()),'drc_exclusions':json.loads((d/(name+'.kicad_pro')).read_text())['board']['design_settings']['drc_exclusions']}
 (r/'delta.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
elif action=='export':
 node='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';sharp='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
 out.mkdir(exist_ok=True);logs=[]
 # Actual native before/after, top-coordinate comparison. No source fills removed.
 for revision,src in [('before',H/'kicad/MORI_motion_P5/MORI_motion_P5.kicad_pcb'),('after',p)]:
  target=out/'previews'/revision;target.mkdir(parents=True,exist_ok=True);old_hash=sha(src);b=k.LoadBoard(str(src))
  for z in list(b.Zones()):
   if not z.GetIsRuleArea():b.Delete(z)
  tmp=out/'reports'/f'{revision}_REVIEW_ONLY.kicad_pcb';k.SaveBoard(str(tmp),b)
  for label,layers in [('combined','F.Cu,B.Cu,F.Fab,B.Fab,F.Silkscreen,B.Silkscreen,Edge.Cuts'),('front','F.Cu,F.Fab,B.Fab,F.Silkscreen,Edge.Cuts'),('back','B.Cu,F.Fab,B.Fab,B.Silkscreen,Edge.Cuts')]:
   svg=target/(label+'.svg');png=target/(label+'.png')
   logs.append(run([cli,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(svg),str(tmp)]))
   js='const sharp=require('+json.dumps(sharp)+');sharp(process.argv[1],{density:500}).resize({width:2800}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
   q=subprocess.run([node,'-e',js,str(svg),str(png)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  assert sha(src)==old_hash
  tmp.unlink()
 logs.append(run([cli,'sch','export','pdf','-o',str(out/'previews'/f'{name}.pdf'),str(d/(name+'.kicad_sch'))]))
 assert not any(x['returncode']for x in logs),logs
 (r/'review_exports.json').write_text(json.dumps({'source_pcb_sha256':sha(p),'source_sch_sha256':sha(d/(name+'.kicad_sch')),'fills_omitted_in_temporary_copy':True,'back_is_mirrored':False,'commands':logs},indent=2)+'\n')
 print('Native per-layer and combined comparison views exported')
else:raise SystemExit(action)
