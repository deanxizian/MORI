"""Repeat only the UPS reservation with bounds covering its native component.

The first rectangle omitted native copper at y < 4 mm. This preserves that
bounded failure and extends only the read-only planning search, not PCB rules.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_power_spines.py').read_text()
src=src.replace("'R175-power-spines.json'", "'R175-power-spines-v2.json'")
start=src.index('requests=['); end=src.index('\nrows=[]',start)
src=src[:start]+"requests=[('ups_central','/UPS_BAT','In2.Cu',(45.29,10.05),(51.35,6.2),(44,2,64,14))]"+src[end:]
src=src.replace('print(json.dumps(row),flush=True)', "print(json.dumps({k:v for k,v in row.items() if k!='points_mm'}),flush=True)")
exec(compile(src,str(__file__),'exec'))
