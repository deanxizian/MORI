"""Prioritize short bypass/input paths and compare existing-via alternatives.

v2's same-face-first return was over 15 mm and obstructed later loops. Preserve
that rejected proposal, compare a multilayer path even when a same-face path
exists, and route the RLIMIT return after the local input/bypass constraints.
Original rules and native acceptance requirements remain unchanged.
"""
from pathlib import Path
src=Path('robot/.state/c3-completion/trials/R174_restore_loops.py').read_text()
src=src.replace('import ast,json,sys,time','import ast,json,math,sys,time')
src=src.replace("rev+'-restore-loops'","rev+'-restore-loops-v3'")
src=src.replace("tasks=[('ina_bypass_gnd','C1701.2','U1701.8'),('rlimit_direct_gnd','R1701.1','U1701.8'),('ina_limit','R1701.2','U1701.3'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1'),", "tasks=[('ina_bypass_gnd','C1701.2','U1701.8'),('ina_bypass_vs','C1701.1','U1701.9'),('ina_input_minus','R1707.2','U1701.2'),('ina_input_plus','R1706.2','U1701.1'),('ina_limit','R1701.2','U1701.3'),('rlimit_direct_gnd','R1701.1','U1701.8'),")
src=src.replace(" if result is None or result['status']!='PROPOSAL':", " same_face_result=result\n if True:")
src=src.replace(' reused=[]', " if same_face_result and same_face_result['status']=='PROPOSAL':\n  if result['status']!='PROPOSAL' or same_face_result['length_mm']<=result['length_mm']+.5*len(result['vias']):result=same_face_result\n reused=[]")
exec(compile(src,'R174_restore_loops_v3.py','exec'))
