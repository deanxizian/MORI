"""Same unchanged wire straight, but put the retaining bed below the wires."""
from pathlib import Path
CB_SCRIPT=Path(__file__).resolve();CB_ROOT=CB_SCRIPT.parent
CB_HELPER=CB_ROOT/'screen_CAM_pitch_clamp_positions.py'
__file__=str(CB_HELPER)
code=CB_HELPER.read_text()
code=code.replace("CP_SCRIPT=Path(__file__).resolve();CP_ROOT=CP_SCRIPT.parent", "CP_SCRIPT=CB_SCRIPT;CP_ROOT=CB_ROOT")
code=code.replace("'cam_pitch_anchor/clamp_positions'", "'cam_pitch_anchor/clamp_below'")
code=code.replace('[0,0,1,cp_y-232.],[0,-1,0,cp_z-1.5]', '[0,0,-1,cp_y+232.],[0,1,0,cp_z+1.5]')
code=code.replace('cp_y-1.7,cp_z+.25],[cp_hi,cp_y+1.7,cp_z+3.', 'cp_y-1.7,cp_z-3.],[cp_hi,cp_y+1.7,cp_z-.25')
code=code.replace("'bed_tie_intersection_mm3']<1e-6", "'bed_tie_intersection_mm3']<1e-5")
exec(compile(code,str(CB_SCRIPT),'exec'),globals())
