"""Refine actual R143B placement: reverse R1022, restore CLR and power width."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R143C-plan.json';assert not out.exists()
c=Copper(str(b/'R143B/MORI_Interface_C3.kicad_pcb'));assert c.sha=='0c9bfba1e677680617042d1a1caeee6044e4cfb0a1ae86ec142a690a0b7fe96a'
p={'revision':'R143C','board_sha256':c.sha,'purpose':__doc__,'translations':[{'reference':'R1022','from_mm':[41,17.6],'delta_mm':[0,0],'rotation_deg':90}],'delete_copper':[],'deleted_copper_expected':{},'routes':[]}
net='Net-(U1001-D2_{slash}_WHEEL_ADC)'
for t in c.segments:
 if t.GetNetname()==net and t.GetLayer()==pcb.B_Cu:
  u=uid(t);p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':'B.Cu','width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
assert len(p['delete_copper'])==3
p['routes']=[{'net':net,'layer':'B.Cu','width_mm':.2,'points_mm':[[30.8,13.0],[30.8,13.3],[30.4,13.7],[30.4,14]]},{'net':'MOTION_3V3','layer':'B.Cu','width_mm':.2,'points_mm':[[21.9375,12.4],[22.5,12.4]]},{'net':'/CLR_N','layer':'B.Cu','width_mm':.2,'points_mm':[[15.65,8.8],[18.1,11.25],[20.0625,11.25]]}]
out.write_text(json.dumps(p,indent=2)+'\n')
