"""Reserve In3 for UV nets excluded by the unchanged In2 native allow-list.
Search FAULT on its permitted In2 and outer layers, with the same reference,
body, hole, ground-transition and power penalties as the prior search.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R161_power_aware_search.py').read_text()
old="['B.Cu','F.Cu','In2.Cu','In3.Cu']";assert s.count(old)==1
s=s.replace(old,"['B.Cu','F.Cu','In2.Cu']")
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('fault_restore','/FAULT_N','U1301.6','U1501.1')]"+s[end:]
exec(compile(s,'R162_fault_In2_preserved_method','exec'))
