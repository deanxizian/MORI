"""Static native-geometry diagnostics for rejected candidate R137K, not fabrication."""
from pathlib import Path
import sys
sys.path.insert(0,'robot/hardware/driver/development/scripts')
p=Path('robot/.state/c3-completion/trials');out=p/'R137K-views';out.mkdir(exist_ok=False)
s=Path('robot/hardware/driver/development/scripts/render_inspection.py').read_text()
s=s.replace("'#2b5e50' if net=='GND' else '#456470'", "'#2b5e50' if net=='GND' else ('#875729' if 'CAM_BAT_OUT' in net else '#315c81')")
ns={'__name__':'diagnostic_renderer'};exec(compile(s,'render_inspection.py','exec'),ns)
board=str(p/'R137K/MORI_Interface_C3.kicad_pcb')
for layer in ['F.Cu','In3.Cu','B.Cu']:
 ns['render'](board,layer,(12,12,25,20),str(out/(layer+'.svg')),'GND' if layer=='B.Cu' else '/07 {slash} CAM_Protection_Start/CAM_BAT_OUT')
print(str(out),flush=True)
