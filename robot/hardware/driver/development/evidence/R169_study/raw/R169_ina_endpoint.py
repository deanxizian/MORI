"""Read-only native FAULT endpoint reachability at U1701.5 from R168G."""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R166_endpoint_diagnostics.py').read_text()
code=code.replace("b/rev/'MORI_Interface_C3.kicad_pcb'", "Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')")
code=code.replace('Q1701.3','U1701.5')
exec(compile(code,str(__file__),'exec'))
