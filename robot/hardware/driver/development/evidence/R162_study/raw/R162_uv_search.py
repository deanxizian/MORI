"""Search the remaining UV links against the current FAULT-restored board.
The two results are independent; no joint compatibility is inferred.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R161_power_aware_search.py').read_text()
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('uv_output','/13 {slash} Head_Fault_Delay/HEAD_UV_N','U1301.1','Q1301.2'),('uv_divider','Net-(U1301-INA+_{slash}_UV)','R1302.1','U1301.3')]"+s[end:]
exec(compile(s,'R162_power_aware_uv_preserved_method','exec'))
