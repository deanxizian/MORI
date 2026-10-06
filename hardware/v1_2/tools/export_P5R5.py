"""Native review SVGs and raster previews, not fabrication/stencil output."""
from review_P5R5 import *
from all_trace_review_P5R2 import NODE,SHARP
def run(args):
 c=subprocess.run(args,capture_output=True,text=True,timeout=180)
 assert c.returncode==0,(args,c.stderr)
 return {'argv':args,'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr}
def svgpng(tmp,target,layers):
 logs=[run([CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,*(['--mirror']if layers=='B.Silkscreen,Edge.Cuts'else[]),'-o',str(target.with_suffix('.svg')),str(tmp)])]
 js='const s=require('+json.dumps(SHARP)+');s(process.argv[1],{density:500}).resize({width:2400}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
 logs.append(run([NODE,'-e',js,str(target.with_suffix('.svg')),str(target.with_suffix('.png'))]))
 return logs
for kind in sys.argv[1:]or KINDS:
 n,d,p,r=paths(kind);logs=[]
 phases=[('before',source(kind)[2]),('after',p)]
 if kind=='imu':phases.insert(0,('P5R2',H/'kicad/MORI_imu_P5R2/MORI_imu_P5R2.kicad_pcb'))
 for phase,src in phases:
  oldsha=sha(src);b=k.LoadBoard(str(src));out=O/'previews'/kind/phase;out.mkdir(parents=True,exist_ok=True)
  # Export real filled GND view before omitting fills for trace review.
  if kind=='power':
   for lay,tag in [('F.Cu','ground_front'),('In1.Cu','ground_inner1'),('In2.Cu','ground_inner2')]:logs+=svgpng(src,out/tag,lay+',Edge.Cuts')
  for zone in list(b.Zones()):
   if not zone.GetIsRuleArea():b.Delete(zone)
  tmp=r/f'{phase}_REVIEW_ONLY.kicad_pcb';k.SaveBoard(str(tmp),b)
  for label,layers in [('combined','F.Cu,B.Cu,F.Fab,B.Fab,F.Silkscreen,B.Silkscreen,Edge.Cuts'),('front','F.Cu,F.Fab,B.Fab,F.Silkscreen,Edge.Cuts'),('back','B.Cu,F.Fab,B.Fab,B.Silkscreen,Edge.Cuts')]:
   logs+=svgpng(tmp,out/label,layers)
  logs+=svgpng(tmp,out/'silk_front','F.Silkscreen,Edge.Cuts')
  logs+=svgpng(tmp,out/'silk_back','B.Silkscreen,Edge.Cuts')
  assert sha(src)==oldsha;tmp.unlink()
 schout=O/'previews'/kind/'schematic';schout.mkdir(exist_ok=True)
 logs.append(run([CLI,'sch','export','svg','--output',str(schout),str(d/(n+'.kicad_sch'))]))
 dump(r/'review_exports.json',{'source_pcb_sha256':sha(p),'commands':logs,'manufacturing_data':False,'back_view_mirrored':False})
 print(kind,'native previews exported',flush=True)
