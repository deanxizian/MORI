"""Joint placement: exchange C1301 and R1021 locations to restore UV with short leads.

U1301 remains stationary. All existing ground and supply vias stay unchanged.
The remote OV link is still pending and this partial model is not adoptable.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R155E-plan.json').read_text());assert p['board_sha256']==c.sha
p['revision']='R155F';p['scope']=__doc__
p['translations']=[
 {'reference':'C1301','from_mm':[41.525,25.85],'delta_mm':[-.775,1.9]},
 {'reference':'R1021','from_mm':[40.75,27.75],'delta_mm':[.775,-1.9]}]
id_='b898d2f0-b3c2-55c5-8680-795d36af7192';t=c.by_id[id_]
p['delete_copper'].append(id_)
p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['routes'] += [
 {'net':'Net-(U1301-INA+_{slash}_UV)','layer':'F.Cu','width_mm':.2,'points_mm':[[39.975,27.75],[40.75,28.6375]]},
 {'net':'GND','layer':'F.Cu','width_mm':.2,'points_mm':[[41.525,27.75],[42.5,27.1]]},
 {'net':'/01 {slash} Core/BAT_ADC','layer':'F.Cu','width_mm':.2,'points_mm':[[42.35,25.85],[42.35,26.0],[43.1,26.75],[43.1,27.75],[43.675,27.75]]}]
f=b/'R155F-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'revision':'R155F','scope':__doc__}))
