"""Body-clear ADC escape and exact 0.08 mm move of the existing HEAD_BUCK input via. Source diode, all ground vias and fixed interfaces preserved."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R152J-plan.json').read_text());p['revision']='R152K';p['scope']=__doc__+' Independent candidate only.'
net='/01 {slash} Core/BAT_ADC';power='/09 {slash} Head_Buck/HEAD_BUCK_IN';old=p['routes']
p['routes']=[
{'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[41.575,27.75],[43.675,27.75]]},
{'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[42.9,27.75],[42.9,28.5],[44.53,28.5],[44.53,29.44],[45.05,29.96],[45.05,30.8],[44.53,31.32],[44.53,34.05],[44.43,34.15],[12.45,34.15],[12.45,33.0401]]},
{'net':'GND','layer':'F.Cu','width_mm':.2,'points_mm':[[45.325,27.75],[45.625,27.75],[46.425,28.55],[46.425,29.65],[46.075,30.0],[45.65,30.0]]},
old[2],old[3],
{'net':power,'layer':'B.Cu','width_mm':.8,'points_mm':[[46.0,27.25],[46.0,28.58],[45.48,29.1]]}]
v=c.by_id['f46e266a-dc0d-4c5d-91b0-d5adfa37d7e6'];p['move_vias']=[{'uuid':uid(v),'source_expected':via_snapshot(c.board,v),'position_mm':[45.48,29.1]}]
for u in ['64a1d662-325e-4063-9a25-9a77e41caa27','6be07159-3899-4a08-a013-3c0f4e0d807c']:
 t=c.by_id[u];p['delete_copper'].append(u);p['deleted_copper_expected'][u]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['local_review_required']=['J101.5 uses the shortest straight outward escape from its own PTH pad across the housing lip; native keepouts unchanged.','Moved power via retains 0.80/0.40 mm geometry and exact 0.80 mm diode connection; current and thermal qualification not asserted.','Zone expansion and full power/reference/old-connection regression require explicit independent verification.']
f=b/'R152K-plan.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n')
