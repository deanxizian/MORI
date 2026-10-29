"""Compare connecting the moved Q1701 to the two other open FAULT groups.

Joining U1701 or D302 is also real connectivity progress; do not assume every
new branch must independently route to the already connected main group.
All proposals still require reconstruction and complete native validation.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R161_power_aware_search.py').read_text()
start=code.index('requests=[');end=code.index('\nrows=[]',start)
code=code[:start]+"requests=[('fault_Q_to_U1701','/FAULT_N','Q1701.3','U1701.5'),('fault_Q_to_D302','/FAULT_N','Q1701.3','D302.1')]"+code[end:]
code=code.replace("rev+'-power-aware-search'+suffix", "rev+'-other-fault-search'+suffix")
code=code.replace(".1,['B.Cu','F.Cu','In2.Cu','In3.Cu']", ".05,['B.Cu','F.Cu','In2.Cu','In3.Cu']")
code=code.replace('),600000)', '),2000000)')
exec(compile(code,str(__file__),'exec'))
