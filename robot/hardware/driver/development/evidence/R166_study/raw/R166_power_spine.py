"""Extract the actual R165M 0.48 mm In2 power corridor severed by R166A.

This is a planning reservation only. It does not add copper or relax any check.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
code=(b/'R162_power_spine.py').read_text()
changes={
 "out=b/'R162-power-spine.json'":"out=b/'R166-power-spine.json'",
 "c=Copper(str(b/'R162C/MORI_Interface_C3.kicad_pcb'))":"c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'",
 "grid=.05;xs=np.arange(50,69.501,grid);ys=np.arange(24,34.501,grid)":"grid=.025;xs=np.arange(54,69.501,grid);ys=np.arange(8,17.501,grid)",
 "start=(int(round((31-24)/grid)),int(round((54.4-50)/grid)))":"start=(int(round((13.525-8)/grid)),int(round((60.725-54)/grid)))",
 "end=(int(round((26.15-24)/grid)),int(round((69.15-50)/grid)))":"end=(int(round((12.7-8)/grid)),int(round((68.25-54)/grid)))"
}
for old,new in changes.items():
 assert code.count(old)==1,old
 code=code.replace(old,new)
exec(compile(code,str(__file__),'exec'))
