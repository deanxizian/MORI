"""Explicit BAT_ADC/FAULT local alternative; ground restored above R1031."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R152D-plan.json').read_text());p['revision']='R152E';p['scope']=__doc__+' Independent candidate only.'
p['translations']=[{'reference':'R1031','from_mm':[44.5,27.75],'delta_mm':[0,.42]}]
net='/01 {slash} Core/BAT_ADC'
p['routes']=[
 {'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[41.575,27.75],[41.995,28.17],[43.675,28.17],[44.7,29.195],[44.7,33.758],[44.3585,34.0995],[13.5094,34.0995],[12.45,33.0401]]},
 {'net':'GND','layer':'F.Cu','width_mm':.2,'points_mm':[[45.325,28.17],[45.325,27.65],[45.045,27.37],[42.77,27.37],[42.5,27.1]]},
 {'net':'/FAULT_N','layer':'F.Cu','width_mm':.2,'points_mm':[[45.7,31.4125],[45.45,31.4125],[45.15,31.7125],[45.15,33.6125],[45.5,33.9625]]}
]
for id_ in ['01cd9d10-0dc5-4fbd-9ca3-d2446b1a29ca','0f0d607f-5879-46cb-908b-fe8843917dec','47cf0890-373d-45b6-9e46-1ec4e94044c9','7a5b9a44-57a4-4872-848a-80ba2b7a577a']:
 t=c.by_id[id_];assert type(t).__name__=='PCB_TRACK' and t.GetNetname()=='/FAULT_N'
 p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
out=b/'R152E-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'plan':str(out),'replaced_tracks':len(p['delete_copper']),'new_vias':len(p['vias'])}))
