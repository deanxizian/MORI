"""Read-only changed-baseline fault and ADC reachability search from R168G.

All native permissions, body/ground/reference obstacles and foreign-power
screening remain. A result is a bounded proposal, not an adopted connection.
"""
import hashlib
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('fault_ina','/FAULT_N','U1701.5','Q1701.3'),('fault_diode','/FAULT_N','D302.1','Q1701.3'),('current_filtered','/ACT_CURRENT_FILTERED','R1102.2','U1001.9'),('bat_input','Net-(U1001-D1_{slash}_BAT_ADC)','R1021.1','U1001.3'),('wheel_input','Net-(U1001-D2_{slash}_WHEEL_ADC)','R1022.1','U1001.6')]"+code[end:]
code=code.replace("str(b/rev/'MORI_Interface_C3.kicad_pcb')",repr(str(source)))
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-initial-search'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
code=code.replace("for ly in p.layers}","for ly in LAYERS}")
code=code.replace("if pn in ['GND',net] or ly not in p.layers:continue", "if pn in ['GND',net]:continue")
exec(compile(code,str(__file__),'exec'))
