"""Reserve the actual 0.48 mm In3 supply path that R164F/G cut.
This adds a planning obstacle only. It does not change copper, qualify current
capacity, or replace native refill and all 50 power-width regressions.
"""
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
s=(b/'R162_power_spine.py').read_text().split('"""',2)[2]
replacements={
    "out=b/'R162-power-spine.json'":"out=b/'R165-power-spine.json'",
    "b/'R162C/MORI_Interface_C3.kicad_pcb'":"b/'R165C/MORI_Interface_C3.kicad_pcb'",
    "'In2.Cu'":"'In3.Cu'",
    "xs=np.arange(50,69.501,grid);ys=np.arange(24,34.501,grid)":"xs=np.arange(40,64.001,grid);ys=np.arange(17,34.501,grid)",
    "start=(int(round((31-24)/grid)),int(round((54.4-50)/grid)))":"start=(int(round((24.05-17)/grid)),int(round((52.8-40)/grid)))",
    "end=(int(round((26.15-24)/grid)),int(round((69.15-50)/grid)))":"end=(int(round((31-17)/grid)),int(round((54.4-40)/grid)))",
}
for old,new in replacements.items():
    assert old in s,old
    s=s.replace(old,new)
exec(compile(s,'R165_In3_supply_reservation','exec'))
