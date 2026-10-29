"""Open a back-face wheel-sense corridor by rotating the nearby LIMIT resistor.

R1701 moves from (42.5,10.6)/0 to (43.2,9.9)/-90 degrees. Its LIMIT pad still
covers the unchanged old trace start at (43.325,10.6); the original protection
trace is retained. Test the new ground connection and all original regressions
with native fill. R1002, R1707 and every via stay fixed. The new 0.20 mm branch
serves only the 54.9k wheel-voltage divider, not the actuator load path.
"""
import json,hashlib
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');src=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');h=hashlib.sha256(src.read_bytes()).hexdigest();assert h=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
p={'revision':'R157A','board_sha256':h,'scope':__doc__,'translations':[{'reference':'R1701','from_mm':[42.5,10.6],'delta_mm':[.7,-.7],'rotation_deg':-90}],'delete_copper':[],'deleted_copper_expected':{},'routes':[{'net':'/WHEEL_VM','layer':'B.Cu','width_mm':.2,'points_mm':[[42.825,6.75],[42.825,7.2],[42.2,7.825],[42.2,10.95],[41.675,11.475],[41.675,12.15]]}],'vias':[],'adoption_prohibited_until_complete_verification':True}
f=b/'R157A-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
