"""Screen RLIMIT positions with its exact proposed B-face leads retired.

The purpose is to open an INA+ transfer site presently bounded by R1701's
body/pads. Only the candidate-generated LIMIT and R1701 GND leads are omitted
from this placement screen; native original vias/rules and all other geometry
stay. All actual 3 mm LIMIT placement criteria and native validation still apply.
"""
from pathlib import Path
b=Path('robot/.state/c3-completion/trials')
src=(b/'R175_r6_pose_screen.py').read_text()
src=src.replace("'R175-r6-poses.json'", "'R175-rlimit-poses.json'")
src=src.replace("ref='R1706'", "ref='R1701'").replace("'U1701.1'", "'U1701.3'")
src=src.replace('range(352,413)','range(352,433)').replace('range(56,113)','range(40,113)')
needle="excluded={uid(p) for p in f.Pads()};env={}"
replacement=needle+'''
plan=json.loads((b/'R175A-plan.json').read_text());omitted=[]
for ix in [4,5]:
 r=plan['routes'][ix]
 for a,z in zip(r['points_mm'],r['points_mm'][1:]):
  found=[t for t in c.segments if t.GetNetname()==r['net'] and c.board.GetLayerName(t.GetLayer())==r['layer'] and abs(t.GetWidth()/1e6-r['width_mm'])<1e-9 and {xy(t.GetStart()),xy(t.GetEnd())}=={tuple(a),tuple(z)}]
  assert len(found)==1,(ix,a,z,len(found));omitted.append(uid(found[0]))
excluded.update(omitted)
'''
assert src.count(needle)==1;src=src.replace(needle,replacement)
src=src.replace("if t.GetLayer()==lid]))", "if t.GetLayer()==lid and uid(t) not in excluded]))")
src=src.replace("reference=ref,target_pad=", "reference=ref,omitted_generated_tracks=omitted,target_pad=")
exec(compile(src,str(__file__),'exec'))
