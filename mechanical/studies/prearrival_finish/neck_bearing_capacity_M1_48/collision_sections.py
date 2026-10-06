"""Actual posed source/candidate sections; no source scene mutation."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,np,manifold,sha
from validate import rigidtr
ctx=Context();report=json.loads((HERE/'C2_verification.json').read_text())
assert report['source_main_sha256']==ctx.source_hash
def load(n):
    d=np.load(HERE/('C2_'+n+'.npz'))
    return manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
core=['Yaw_Base','Pitch_Yoke','Yaw_Anti_Lift_Keeper','Yaw_Bearing']
current={n:ctx.ss[n].m for n in core};candidate={n:load(n) for n in core}
# Section plane X=0, plot horizontalY/verticalZ, with actual head pitch.
tr=np.array([[0,1,0,0],[0,0,1,0],[-1,0,0,0]])
out={}
for pitch,shell in [(25,'Head_Rear'),(-20,'Head_Front')]:
    shell_m=ctx.ss[shell].m.transform(np.asarray(rigidtr(0,pitch))[:3,:])
    for tag,parts in [('current',current),('candidate',candidate)]:
        layers=dict(parts);layers[shell]=shell_m;layers['Yaw_Reaction_Link']=ctx.ss['Yaw_Reaction_Link'].m
        layers['collision']=(parts['Pitch_Yoke']+parts['Yaw_Anti_Lift_Keeper'])^shell_m
        out[f'{tag}_{pitch}']={n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}
        if tag=='candidate':
            print('COLLISION_SECTION',pitch,'mm3',layers['collision'].volume(),'bounds',layers['collision'].bounding_box(),flush=True)
ctx.assert_unchanged()
result=dict(source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),
    verification_sha256=sha(HERE/'C2_verification.json'),plane='X=0; horizontalY,verticalZ',sections=out,
    main_applied=False)
(HERE/'posed_sections.json').write_text(json.dumps(result)+'\n')
