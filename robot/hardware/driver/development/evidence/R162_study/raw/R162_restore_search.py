"""Reuse the preserved power-aware search only for still-unfinished links.
Every proposal remains independent and requires native joint validation.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R161_power_aware_search.py').read_text()
start=s.index('requests=[');end=s.index('\nrows=[]',start)
s=s[:start]+"requests=[('fault_restore','/FAULT_N','U1301.6','U1501.1'),('uv_output','/13 {slash} Head_Fault_Delay/HEAD_UV_N','U1301.1','Q1301.2'),('uv_divider','Net-(U1301-INA+_{slash}_UV)','R1302.1','U1301.3')]"+s[end:]
exec(compile(s,'R162_power_aware_preserved_method','exec'))
