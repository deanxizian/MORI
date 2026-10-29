"""Native two-face delay-resistor positions near the rotated supervisor CT pin.

Use the unchanged 4 mm exploratory CT distance bound. This is not a new native
acceptance threshold and does not substitute for restored CT/3V3 routing.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_r6_pose_screen.py').read_text()
src=src.replace("'R175-r6-poses.json'", "'R175-rt-poses.json'")
src=src.replace("b/'R175A/MORI_Interface_C3.kicad_pcb'", "b/'R175G/MORI_Interface_C3.kicad_pcb'")
src=src.replace("ref='R1706'", "ref='R1310'").replace("'U1701.1'", "'U1302.4'")
src=src.replace("actual['2'][2]", "actual['1'][2]")
src=src.replace('d>3+1e-8','d>4+1e-8').replace("'critical_3mm'", "'exploratory_4mm'")
src=src.replace('range(352,413)','range(320,389)').replace('range(56,113)','range(80,149)')
src=src.replace("target_max_mm=3", "target_max_mm=4")
exec(compile(src,str(__file__),'exec'))
