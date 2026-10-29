"""Static native-layer exports and explicitly labelled geometry diagnostics.

Review artwork only; no Gerber, drill, fabrication package or device operation.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from render_inspection import render

b=Path('robot/.state/c3-completion/trials');board=b/'R142/MORI_Interface_C3.kicad_pcb';source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');out=b/'R142-views';out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original=sha(board);source_sha=sha(source);commands=[];images=[]
for layer in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']:
 layers=layer+(',F.Fab' if layer=='F.Cu' else ',B.Fab' if layer=='B.Cu' else '')+',Edge.Cuts'
 path=out/(layer+'-native.svg')
 args=['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','export','svg','--mode-single','--layers',layers,'--page-size-mode','2','--exclude-drawing-sheet','--drill-shape-opt','2','-o',str(path),str(board)]
 r=subprocess.run(args,capture_output=True,text=True);commands.append({'argv':args,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 images.append({'file':path.name,'source_sha256':original,'kind':'Native KiCad layer SVG, not screenshot/fabrication','layer':layer})
for name,layer,bounds,net,which in [
 ('B-ADC-upper','B.Cu',[23,8,32,17],'/01 {slash} Core/ACT_CURRENT_ADC',board),
 ('B-ADC-lower','B.Cu',[16,24,24,33],'/01 {slash} Core/ACT_CURRENT_ADC',board),
 ('B-R301-CLR','B.Cu',[9.5,2,17,13.5],'/CLR_N',board),
 ('B-R903-before','B.Cu',[29.5,25,35,31.5],'/01 {slash} Core/ARMED',source),
 ('B-R903-after','B.Cu',[29.5,25,35,31.5],'/01 {slash} Core/ARMED',board),
 ('In3-OUT-CAM','In3.Cu',[14,13,29,20],'Net-(U1401-OUT)',board),
 ('In2-FAULT','In2.Cu',[17,25,34,30],'/FAULT_N',board)]:
 path=out/(name+'.svg');render(str(which),layer,bounds,str(path),net)
 images.append({'file':path.name,'source_sha256':sha(which),'kind':'Native-geometry diagnostic, not screenshot/full qualification','layer':layer,'bounds_mm':bounds,'highlight_net':net})
assert sha(board)==original and sha(source)==source_sha
(out/'render_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(out/'image_manifest.json').write_text(json.dumps({'scope':__doc__,'board_sha256':original,'source_sha256':source_sha,'images':images},indent=2)+'\n')
print(json.dumps({'native_layers':6,'diagnostics':7,'board_unchanged':True}),flush=True)
