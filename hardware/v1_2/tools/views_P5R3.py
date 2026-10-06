"""Native KiCad review views, filtered copies only; no manufacturing outputs."""
from review_P5R3 import *
from all_trace_review_P5R3 import NODE,SHARP
import re
out=O/'critical';out.mkdir(exist_ok=True);logs=[]
def export(src,dest,layers):
 args=[CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(dest),str(src)]
 cp=subprocess.run(args,capture_output=True,text=True);logs.append({'argv':args,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr});assert cp.returncode==0
def render(svg,box=None,width=1600):
 if box:
  x,y,w,h=box;s=svg.read_text();s=re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',f'width="{w}mm" height="{h}mm" viewBox="{x} {y} {w} {h}"',s,count=1);svg.write_text(s)
 js='const sharp=require('+json.dumps(SHARP)+');sharp(process.argv[1],{density:300}).resize({width:'+str(width)+'}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
 cp=subprocess.run([NODE,'-e',js,str(svg),str(svg.with_suffix('.png'))],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
for phase in ['before','after']:
 src=source('power')[2]if phase=='before'else paths('power')[2];h=sha(src)
 # Real saved fills, not guessed planes; all original copper retained.
 for label,layers in [('ground_front','F.Cu,F.Fab'),('ground_inner','In1.Cu,F.Fab')]:
  base=out/(phase+'_'+label+'_full.svg');export(src,base,layers)
  for cell,box in [('U60',(16,21,20,14)),('U70',(16,35,20,14))]:
   dest=out/(phase+'_'+label+'_'+cell+'.svg');dest.write_bytes(base.read_bytes());render(dest,box)
 # Filter copies to the requested net. Retained pads and traces keep exact
 # KiCad geometry; other copper and zone fills are hidden, Fab preserved.
 for net in ['BAT_REV','BAT_MON','KELVIN_P','KELVIN_N','M5_FB','C5_FB']:
  b=k.LoadBoard(str(src));nn='/'+net
  for t in list(b.GetTracks()):
   if t.GetNetname()!=nn:b.Delete(t)
  for z in list(b.Zones()):b.Delete(z)
  for f in b.GetFootprints():
   for p in f.Pads():
    if p.GetNetname()!=nn:p.SetLayerSet(k.LSET())
  tmp=out/'TEMP_FILTERED_REVIEW_ONLY.kicad_pcb';k.SaveBoard(str(tmp),b)
  dest=out/(phase+'_'+net+'.svg');export(tmp,dest,'F.Cu,B.Cu,F.Fab,B.Fab');tmp.unlink()
  render(dest,(24,9,18,15)if net in['BAT_REV','BAT_MON','KELVIN_P','KELVIN_N']else(22,23,13,11)if net=='M5_FB'else(22,37,13,11))
 assert sha(src)==h
for kind in KINDS:
 src=paths(kind)[2]
 for label,layers in [('paste_front','F.Paste,F.Fab'),('paste_back','B.Paste,B.Fab')]:
  p=out/(kind+'_'+label+'.svg');export(src,p,layers)
  w,h={'motion':(70,35),'imu':(20,16),'power':(80,55),'rear':(24,25)}[kind]
  render(p,(-.5,-.5,w+1,h+1),width=2200)
dump(O/'reports/critical_view_commands.json',{'purpose':'Native SVG/PNG review only; no Gerber/stencil/production output','filtered_net_views':'Foreign tracks/pads and fills hidden on temporary copies. Selected native copper geometry unchanged. Ground views retain actual saved filled copper.','logs':logs})
print('Native critical views complete')
