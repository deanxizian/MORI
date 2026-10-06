#!/usr/bin/env python3
"""Check/review native P5R2 boards; fill updates only candidate titles and fills.
No manufacturing export. Historical source projects are never written.
"""
import pcbnew as k
import sys,json,subprocess,hashlib,runpy
from datetime import datetime,timezone
from all_trace_review_P5R2 import paths,source,KINDS,H,ROOT,O,CLI,NODE,SHARP,sha,xy
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def run(args):
 c=subprocess.run(args,capture_output=True,text=True,timeout=300)
 return {'utc':datetime.now(timezone.utc).isoformat(),'argv':args,'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr}
def inputs(d):
 return {str(f.relative_to(ROOT)):sha(f)for f in sorted(d.rglob('*'))if f.is_file()and f.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_mod','.kicad_sym']}
action=sys.argv[1]
for kind in sys.argv[2:]or KINDS:
 name,d,p,r=paths(kind)
 if action=='fill':
  b=k.LoadBoard(str(p));tb=b.GetTitleBlock();tb.SetTitle(f'MORI {kind} / P5R2 / PROTOTYPE');tb.SetRevision('V1.2-H0.5-P5R2');tb.SetComment(0,'All-net routing review; circuit P5; physical tests NOT_TESTED');tb.SetComment(1,'Review and exceptions: hardware/v1_2/layout_P5R2/README.md');b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);print(kind,'filled',sha(p),flush=True)
 elif action=='check':
  commands=[[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(r/'drc.json'),str(p)],
   [CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(r/'erc.json'),str(d/(name+'.kicad_sch'))],
   [CLI,'sch','export','netlist','--format','kicadxml','-o',str(r/'netlist.xml'),str(d/(name+'.kicad_sch'))]]
  logs=[]
  for i,args in enumerate(commands):
   log={'input_sha256':inputs(d),**run(args)};logs.append(log);(r/f'check_{i}.log').write_text(log['stdout']+log['stderr']);print(kind,i,log['returncode'],flush=True)
  dump(r/'check_commands.json',logs)
  if any(v['returncode']for v in logs):raise SystemExit(1)
 elif action=='audit':
  import layout_P5
  layout_P5.paths=paths
  import audit_body_P5
  audit_body_P5.audit(kind)
  body_report=json.loads((r/'body_review_final.json').read_text());body_board=k.LoadBoard(str(p))
  for f in body_board.GetFootprints():
   if f.GetReference()in body_report['components']:body_report['components'][f.GetReference()]['footprint']=f.GetFPIDAsString()
  dump(r/'body_review_final.json',body_report)
  sys.argv=['corner_review_P5.py',kind];runpy.run_path(str(H/'tools/corner_review_P5.py'),run_name='__main__')
  if kind=='power':runpy.run_path(str(H/'tools/audit_load_paths_P5.py'),run_name='__main__')
  _,_,sp=source(kind);old=k.LoadBoard(str(sp));b=k.LoadBoard(str(p))
  stats=lambda bb:{'tracks':sum(not isinstance(t,k.PCB_VIA)for t in bb.GetTracks()),'vias':sum(isinstance(t,k.PCB_VIA)for t in bb.GetTracks()),'track_length_mm':round(sum(k.ToMM(t.GetLength())for t in bb.GetTracks()if not isinstance(t,k.PCB_VIA)),3)}
  pads=lambda bb:sorted((f.GetReference(),q.GetNumber(),q.GetNetname(),f.GetFPIDAsString())for f in bb.GetFootprints()for q in f.Pads())
  fps=lambda bb:{f.GetReference():{'position':xy(f.GetPosition()),'angle':f.GetOrientationDegrees(),'layer':bb.GetLayerName(f.GetLayer())}for f in bb.GetFootprints()}
  a,z=fps(old),fps(b)
  edges=lambda bb:sorted((int(s.GetShape()),xy(s.GetStart()),xy(s.GetEnd()),xy(s.GetCenter()))for s in bb.GetDrawings()if s.GetLayer()==k.Edge_Cuts)
  protected=lambda poses:{ref:v for ref,v in poses.items()if ref.startswith(('H','J'))or ref in ['USB1','SW1','U100']}
  delta={'source_pcb_sha256':sha(sp),'output_pcb_sha256':sha(p),'before':stats(old),'after':stats(b),'pad_net_footprint_map_identical':pads(old)==pads(b),'changed_placements':{ref:{'before':a[ref],'after':z[ref]}for ref in a if a[ref]!=z[ref]},'edge_geometry_identical':edges(old)==edges(b),'holes_connectors_and_module_poses_identical':protected(a)==protected(z),'copper_layers_unchanged':old.GetCopperLayerCount()==b.GetCopperLayerCount(),'inner_signal_tracks':sum(not isinstance(t,k.PCB_VIA)and t.GetLayer()not in[k.F_Cu,k.B_Cu]for t in b.GetTracks()),'drc_exclusions':json.loads((d/(name+'.kicad_pro')).read_text())['board']['design_settings']['drc_exclusions']}
  dump(r/'delta.json',delta);print(kind,'audit done',flush=True)
 elif action=='export':
  logs=[]
  for phase,src in [('before',source(kind)[2]),('after',p)]:
   target=O/'previews'/kind/phase;target.mkdir(parents=True,exist_ok=True);oldhash=sha(src);b=k.LoadBoard(str(src))
   for zone in list(b.Zones()):
    if not zone.GetIsRuleArea():b.Delete(zone)
   tmp=r/f'{phase}_REVIEW_ONLY.kicad_pcb';k.SaveBoard(str(tmp),b)
   for label,layers in [('combined','F.Cu,B.Cu,F.Fab,B.Fab,F.Silkscreen,B.Silkscreen,Edge.Cuts'),('front','F.Cu,F.Fab,B.Fab,F.Silkscreen,Edge.Cuts'),('back','B.Cu,F.Fab,B.Fab,B.Silkscreen,Edge.Cuts')]:
    svg=target/(label+'.svg');png=target/(label+'.png');logs.append(run([CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(svg),str(tmp)]))
    js='const sharp=require('+json.dumps(SHARP)+');sharp(process.argv[1],{density:500}).resize({width:2800}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
    cp=subprocess.run([NODE,'-e',js,str(svg),str(png)],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
   assert sha(src)==oldhash;tmp.unlink()
  logs.append(run([CLI,'sch','export','pdf','-o',str(O/'previews'/kind/(name+'.pdf')),str(d/(name+'.kicad_sch'))]))
  assert not any(q['returncode']for q in logs),logs
  dump(r/'review_exports.json',{'source_pcb_sha256':sha(p),'source_sch_sha256':sha(d/(name+'.kicad_sch')),'fills_omitted_in_temporary_copy':True,'back_is_mirrored':False,'commands':logs});print(kind,'native views exported',flush=True)
 else:raise SystemExit(action)
