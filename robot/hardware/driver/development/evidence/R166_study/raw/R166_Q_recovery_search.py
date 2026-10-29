"""Route-screen the courtyard-corrected Q1701 candidate and its original links.

Prefer preserving all foreign power fill. Weighted proposals still require
native refill and complete power/reference checks. Proposals are independent.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('enable_restore','/HEAD_UV_ENABLE','R1309.1','Q1701.1'),('act_uv_left','/17 {slash} Actuator_Overcurrent/ACT_UV_N','U1702.1','Q1701.2'),('act_uv_right','/17 {slash} Actuator_Overcurrent/ACT_UV_N','U1702.1','R1705.1'),('fault_Q','/FAULT_N','U1301.6','Q1701.3')]"+code[end:]
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-Q-recovery-search'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
exec(compile(code,str(__file__),'exec'))
