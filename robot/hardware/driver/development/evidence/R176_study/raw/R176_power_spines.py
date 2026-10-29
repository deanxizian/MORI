"""Recompute power reservations on the actual native R176A geometry.

The retired upper 3V3 transfer is not an anchor. Preserve the remaining 0.48 mm
path between unchanged upper and relocated lower source transfers, plus UPS.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_power_spines.py').read_text()
src=src.replace("'R175-power-spines.json'", "'R176-power-spines.json'")
src=src.replace("b/'R174B/MORI_Interface_C3.kicad_pcb'", "b/'R176A/MORI_Interface_C3.kicad_pcb'")
start=src.index('requests=[');end=src.index('\nrows=[]',start)
src=src[:start]+"requests=[('ups_central','/UPS_BAT','In2.Cu',(45.29,10.05),(51.35,6.2),(44,2,64,14)),('ups_right','/UPS_BAT','In2.Cu',(51.35,6.2),(59.9,10.35),(49,4,62,15)),('3v3_retained','MOTION_3V3','In3.Cu',(47.15,10.55),(47.775,14.25),(43,7,54,18))]"+src[end:]
src=src.replace('print(json.dumps(row),flush=True)',"print(json.dumps({k:v for k,v in row.items() if k!='points_mm'}),flush=True)")
exec(compile(src,str(__file__),'exec'))
