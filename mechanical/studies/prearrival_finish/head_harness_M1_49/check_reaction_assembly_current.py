"""Recheck two unresolved reaction-link approaches on M1.49 C5+K1 itself."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/reaction_current';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from interface_completion import axial

ctx=Context();started=time.time()
assert ctx.sources['mechanical/mori_v1_2.blend']=='89cb07f571367bf87b627c771998d0cc0c28b873be575afdb4002c9bcf5b499f'
bolt=ctx.ss['Yaw_Reaction_Clamp_Screw'];center=(bolt.lo+bolt.hi)/2
start=np.array([center[0],bolt.hi[1]+.05,center[2]])
tool=axial(1.25,30,start+[0,15,0],[0,1,0])
yoke=ctx.ss['Pitch_Yoke'].m;link=ctx.ss['Yaw_Reaction_Link'].m
specs=[('provisional_straight_tool',tool),('link_lift_2mm',link.translate((0,0,2)))]
rows=[]
for name,shape in specs:
    intersection=shape^yoke;volume=float(intersection.volume())
    rows.append(dict(id=name,status='FAIL' if volume>1e-6 else 'PASS',overlap_mm3=volume))
    for suffix,m in [('moving',shape),('intersection',intersection)]:
        a=m.to_mesh64();np.savez_compressed(OUT/(name+'_'+suffix+'.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
    print('REACTION_CURRENT',rows[-1],flush=True)
ctx.assert_unchanged()
r=dict(status='BLOCKED' if any(x['status']=='FAIL' for x in rows) else 'PASS',
    scope='Two explicitly defined approaches only; no C6 or guide substitution and no new reaction geometry',
    sources=ctx.sources,inputs={str((ROOT/'mechanical/scripts/interface_completion.py').relative_to(ROOT)):sha(ROOT/'mechanical/scripts/interface_completion.py')},
    rows=rows,tool=dict(radius_mm=1.25,length_mm=30,axis=[0,1,0],start_mm=start.tolist(),evidence='ASSUMED tool allocation, not selected supplier tool'),
    main_changed=False,approved=False,all_possible_entry_paths='NOT_TESTED',
    final_horn_and_shaft='BLOCKED',physical_fit='NOT_TESTED',full_harness='BLOCKED',
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('REACTION_CURRENT_DONE',r['status'],flush=True)
