"""Sample actual loft side-surface thickness and full-print shell distances.

Finite surface sampling is reported as such, not a certified global minimum.
The bore/outer loft caps are excluded from the side-wall nearest search.
"""
from pathlib import Path
import sys,json,math,time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,np,manifold,sha,Vector,BVHTree
from validate import rigidtr
ctx=Context();start=time.time();build=json.loads((HERE/'C5_build.json').read_text())
assert ctx.source_hash==build['source_main_sha256']
def load(n):
    d=np.load(HERE/('C5_'+n+'.npz'));return d['vertices_mm'],d['triangles'],manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
iv,fi,inner=load('neck_inner');ov,fo,outer=load('neck_outer')
def side(v,f):
    pts=v[f];spans=np.ptp(pts[:,:,2],axis=1)
    return f[spans>1e-6]
fi=side(iv,fi);fo=side(ov,fo)
it=BVHTree.FromPolygons(iv,fi.tolist(),all_triangles=True);ot=BVHTree.FromPolygons(ov,fo.tolist(),all_triangles=True)
samples=[]
for source,target,v,f in [('inner_to_outer',ot,iv,fi),('outer_to_inner',it,ov,fo)]:
    pts=np.vstack([v[np.unique(f)],np.mean(v[f],axis=1)])
    pts=pts[(pts[:,2]>=157.0)&(pts[:,2]<=173.1)]
    rows=[]
    for p in pts:
        nearest=target.find_nearest(Vector(p))
        rows.append(dict(point_mm=p.tolist(),opposite_point_mm=list(nearest[0]),distance_mm=float(nearest[3])))
    samples.append(dict(direction=source,samples=len(rows),minimum=min(rows,key=lambda x:x['distance_mm'])))

parts={n:load(n)[2] for n in ['Yaw_Base','Yaw_Anti_Lift_Keeper','Pitch_Yoke']}
clearance=[]
for name in ['Head_Front','Head_Rear']:
    for pitch in range(-20,26,5):
        shell=ctx.ss[name].m.transform(np.asarray(rigidtr(0,pitch))[:3,:])
        gap=float(parts['Pitch_Yoke'].min_gap(shell,5.))
        row=dict(part='Pitch_Yoke',shell=name,yaw_deg=0,pitch_deg=pitch,gap_mm=gap)
        if gap<.3:
            contact=parts['Pitch_Yoke']^shell
            row.update(raw_overlap_mm3=float(contact.volume()),intersection_bounds_mm=list(contact.bounding_box()))
        clearance.append(row)
        for yaw in range(-60,61,10):
            posed=ctx.ss[name].m.transform(np.asarray(rigidtr(yaw,pitch))[:3,:])
            for part in ['Yaw_Base','Yaw_Anti_Lift_Keeper']:
                gap=float(parts[part].min_gap(posed,5.))
                clearance.append(dict(part=part,shell=name,yaw_deg=yaw,pitch_deg=pitch,gap_mm=gap))
ctx.assert_unchanged()
out=dict(status='PASS' if min(r['gap_mm'] for r in clearance)>=.3 else 'BLOCKED',
    scope='Finite side-surface samples and required0.3mm nominal print/head-shell gap',
    source_main_sha256=ctx.source_hash,build_sha256=sha(HERE/'C5_build.json'),script_sha256=sha(__file__),
    neck_side_thickness_samples=samples,head_shell_gap_rows=clearance,
    minimum_nominal_head_shell_gap=min(clearance,key=lambda x:x['gap_mm']),
    nominal_normal_wall_reserve_mm=2.2,qualified_minimum_wall=None,
    all_printed_parts_wall_check='NOT_TESTED',strength='NOT_TESTED',main_applied=False,
    limits=['Nearest distances sample loft vertices and triangle centroids, excluding endcaps; not a global wall-thickness proof.',
        'The loft is unioned with supporting native geometry at its ends; these samples describe the generated side wall.',
        'Distances are nominal facet geometry; noPA12 shrinkage, tolerance stack or physical load qualification.'],elapsed_s=time.time()-start)
(HERE/'C5_material.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('C5_MATERIAL',out['status'],out['minimum_nominal_head_shell_gap'],[(r['direction'],r['minimum']['distance_mm']) for r in samples],flush=True)
