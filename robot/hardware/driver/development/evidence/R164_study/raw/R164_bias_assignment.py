"""Read-only candidate for restoring the bias pair near its original right edge.
R1311 uses the free slot above the old R1311 position; R1312 takes that old
position. Original resistor values/nets and native guards stay authoritative.
"""
from pathlib import Path
s=Path('robot/.state/c3-completion/trials/R163_divider_assignment.py').read_text().split('"""',2)[2]
s=s.replace("out=b/'R163-divider-assignment.json'","out=b/'R164-bias-assignment.json'")
s=s.replace("b/'R162D/MORI_Interface_C3.kicad_pcb'","b/'R163F/MORI_Interface_C3.kicad_pcb'")
start=s.index('poses=[');end=s.index('\nmoving=',start)
s=s[:start]+"poses=[('R1311','B.Cu',[68.8,18.25],90),('R1312','B.Cu',[68.8,20.75],90)]"+s[end:]
exec(compile(s,'R164_preserved_native_placement_check','exec'))
