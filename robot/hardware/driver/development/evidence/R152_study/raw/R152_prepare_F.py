"""Independent ADC/ground geometry preparation with FAULT upper branch explicitly open for replacement. Not an accepted board."""
import sys,json
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R152D-plan.json').read_text());p['revision']='R152F';p['scope']=__doc__
net='/01 {slash} Core/BAT_ADC'
p['routes']=[
 {'net':net,'layer':'F.Cu','width_mm':.2,'points_mm':[[41.575,27.75],[43.675,27.75],[44.4912,28.5662],[44.4912,29.5],[45.05,30.0588],[45.05,30.8],[44.4912,31.3588],[44.4912,33.9668],[44.3585,34.0995],[13.5094,34.0995],[12.45,33.0401]]},
 {'net':'GND','layer':'F.Cu','width_mm':.2,'points_mm':[[45.325,27.75],[45.625,27.75],[46.325,28.45],[46.325,29.65],[45.975,30.0],[45.65,30.0]]},
 {'net':'/FAULT_N','layer':'F.Cu','width_mm':.2,'points_mm':[[45.7,31.4125],[45.45,31.4125],[45.15,31.7125],[45.15,33.6125],[45.5,33.9625]]}
]
p['vias']=[{'net':'GND','position_mm':[45.65,30.0],'diameter_mm':.5,'drill_mm':.3}]
ids=['01cd9d10-0dc5-4fbd-9ca3-d2446b1a29ca','0f0d607f-5879-46cb-908b-fe8843917dec','47cf0890-373d-45b6-9e46-1ec4e94044c9','7a5b9a44-57a4-4872-848a-80ba2b7a577a',
'045c976b-57a5-433e-a82a-d27a5e7660fc','72296577-a6a4-4133-9c18-3f91a75bc8ba','cad696ba-b08e-4cd8-b454-e27cc1329f43','dce214ec-17d0-4beb-9421-7531f609434c','ee7a53a1-33b9-417e-ad0c-75f24cffbe54']
for id_ in ids:
 t=c.by_id[id_];assert type(t).__name__=='PCB_TRACK' and t.GetNetname()=='/FAULT_N'
 p['delete_copper'].append(id_);p['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
p['unfinished_branch']={'net':'/FAULT_N','endpoint_vias_mm':[[44.2,26.825],[45.7,31.4125]],'next':'Compare B.Cu/In3.Cu/In2.Cu local replacement; preserve exact R13 and existing power/ground connections.'}
out=b/'R152F-plan.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'plan':str(out),'removed_tracks':len(p['delete_copper'])}))
