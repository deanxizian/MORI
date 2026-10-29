"""Independent route proposals for the joint U1702/Q1701 preparation.

The native R167A board has deliberately removed obsolete leads. Preserve all
native constraints and try keeping every foreign power fill first. These
proposals are independent and must be combined and natively rechecked.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('fault_main','/FAULT_N','Q1701.3','U1301.6'),('fault_ina','/FAULT_N','Q1701.3','U1701.5'),('fault_diode','/FAULT_N','Q1701.3','D302.1'),('enable_restore','/HEAD_UV_ENABLE','R1309.1','Q1701.1'),('act_uv_left','/17 {slash} Actuator_Overcurrent/ACT_UV_N','U1702.1','Q1701.2'),('act_uv_right','/17 {slash} Actuator_Overcurrent/ACT_UV_N','U1702.1','R1705.1'),('ina_restore','Net-(U1702-INA+)','R1704.2','U1702.3'),('vdd_restore','MOTION_3V3','C1702.1','U1702.5')]"+code[end:]
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-joint-recovery-search'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
exec(compile(code,str(__file__),'exec'))
