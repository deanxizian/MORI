"""Search the two remaining old links on R163F's changed copper.
Both proposals are independent. Native power/reference/old-link checks remain
mandatory; a bounded miss is not proof that the board is unroutable.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R161_power_aware_search.py').read_text()
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('uv_output','/13 {slash} Head_Fault_Delay/HEAD_UV_N','U1301.1','Q1301.2'),('bias_enable','/HEAD_UV_ENABLE','R1311.2','Q1701.1')]"+s[end:]
old="out=b/(rev+'-power-aware-search'+suffix)";assert s.count(old)==1;s=s.replace(old,"out=b/('R164-initial-search'+suffix)")
exec(compile(s,'R164_current_geometry_preserved_power_method','exec'))
