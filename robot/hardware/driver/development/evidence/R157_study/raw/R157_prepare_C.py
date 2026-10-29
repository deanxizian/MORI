"""Alternative wheel-sense corridor preserving the existing LIMIT-resistor location.

Shift C1601 left 0.10 mm to open the back-face gap beside R1701. Both original
capacitor trace endpoints remain inside their original-net lands. All existing
tracks, vias, R1701 and its protection connection stay unchanged. Route only the
54.9k divider input through the widened corridor. The newly identified INA300
LIMIT-ground layout issue remains explicitly open; this trial does not fix it.
"""
import json,hashlib
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');src=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');h=hashlib.sha256(src.read_bytes()).hexdigest();assert h=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
p={'revision':'R157C','board_sha256':h,'scope':__doc__,'translations':[{'reference':'C1601','from_mm':[40,11.1],'delta_mm':[-.1,0]}],'delete_copper':[],'deleted_copper_expected':{},'routes':[{'net':'/WHEEL_VM','layer':'B.Cu','width_mm':.2,'points_mm':[[42.825,6.75],[42.825,7.3],[40.95,9.175],[40.95,11.3],[41.675,12.025],[41.675,12.15]]}],'vias':[],'adoption_prohibited_until_complete_verification':True}
f=b/'R157C-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
