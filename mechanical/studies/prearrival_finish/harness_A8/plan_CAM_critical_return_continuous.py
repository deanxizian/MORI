"""Search the critical return first, with continuous edge acceptance.

Keeps the full-stage attempt and its deliberate interruption distinct. This
study only covers0.75..0.875 and cannot release the complete wire sequence.
"""
from pathlib import Path
KC_SCRIPT=Path(__file__).resolve();KC_ROOT=KC_SCRIPT.parent
KC_HELPER=KC_ROOT/'plan_CAM_last_wire_continuous.py'
code=KC_HELPER.read_text()
# Same reviewed displacement bounds and acceptance logic, changed scope.
code=code.replace("LC_SCRIPT=Path(__file__).resolve();LC_ROOT=LC_SCRIPT.parent", "LC_SCRIPT=KC_SCRIPT;LC_ROOT=KC_ROOT")
code=code.replace("LC_OUT=TC_OUT/'last_wire_continuous_search'", "LC_OUT=TC_OUT/'critical_return_continuous'")
code=code.replace("old={'fraction':1.,", "old={'fraction':.875,")
code=code.replace("for t in np.linspace(.975,0.,40):", "for t in np.linspace(.85,.75,5):")
code=code.replace("rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.", "rows[0]['interval'][0]==.75 and rows[-1]['interval'][1]==.875")
code=code.replace("'complete_last_wire_coverage':good", "'complete_local_coverage':good,'complete_last_wire_coverage':False")
code=code.replace("Only last wire, other three wires fixed in completed state; adaptive continuous edge search", "Only last-wire critical return0.75..0.875, other three wires fixed in completed state; adaptive continuous edge search")
exec(compile(code,str(KC_HELPER),'exec'),globals())
