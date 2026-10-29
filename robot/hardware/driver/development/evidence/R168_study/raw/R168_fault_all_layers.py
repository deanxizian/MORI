"""Search three remaining FAULT groups after the joint local port correction.

In2 is permitted only by the unchanged native whitelist. Potential power cuts
are reported on all copper layers; proposals are not adopted from searches.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('fault_main','/FAULT_N','Q1701.3','U1301.6'),('fault_ina','/FAULT_N','Q1701.3','U1701.5'),('fault_diode','/FAULT_N','Q1701.3','D302.1')]"+code[end:]
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-fault-all-layers'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
code=code.replace("for ly in p.layers}","for ly in LAYERS}")
code=code.replace("if pn in ['GND',net] or ly not in p.layers:continue", "if pn in ['GND',net]:continue")
exec(compile(code,str(__file__),'exec'))
