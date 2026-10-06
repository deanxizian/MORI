"""Check local contact/tail/first reshaping sweeps against the other three wires.

All other wires are in their verified zero-yaw installed positions.  A PASS
allows any ordering of these four *local* feed operations, not body-tail
placement, crimping, or access by an assembler's hand.
"""
from pathlib import Path
ORDER_SCRIPT=Path(__file__).resolve();ORDER_DIR=ORDER_SCRIPT.parent
ORDER_HELPER=ORDER_DIR/'plan_h06_documented_mates.py';__file__=str(ORDER_HELPER)
exec(compile(ORDER_HELPER.read_text().split('\nports=json.loads',1)[0],str(ORDER_HELPER),'exec'),globals())
__file__=str(ORDER_SCRIPT);OUT=ORDER_DIR/'assembly_feed_v3';ORDER_START=time.time()
from mathutils.bvhtree import BVHTree
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pack=json.loads((ORDER_DIR/'body_prefix_v2/packing.json').read_text())
route_meta=json.loads((ORDER_DIR/'body_prefix_v2/body_to_yaw_motion.json').read_text())
curves=np.load(ORDER_DIR/'body_prefix_v2/body_to_yaw_curves.npz')
rows=[];inputs={}
for index,phase in enumerate([45,135,225,315]):
    meshes=[]
    for kind in ['contact','wire','relaxation']:
        path=OUT/f'{kind}_sweep_{index}.npz';data=np.load(path)
        inputs[str(path.relative_to(PROJECT))]=sha(path)
        meshes.append(manifold.Manifold(manifold.Mesh64(vert_properties=data['vertices_mm'],tri_verts=data['triangles'].astype(np.uint64))))
    sweep=manifold.Manifold.batch_boolean(meshes,manifold.OpType.Add)
    mm=sweep.to_mesh64();v=np.array(mm.vert_properties[:,:3]);f=np.array(mm.tri_verts)
    tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
    for selected in pack['selected']:
        if selected['azimuth_deg']==phase:continue
        pin=selected['pin'];points=curves[f'pin{pin}_yaw0']
        meta=next(r for r in route_meta['rows'] if r['pin']==pin and r['yaw_deg']==0)
        samples=[]
        for a,b in zip(points,points[1:]):samples.extend(np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.02))+1)[:-1])
        samples=np.vstack([samples,points[-1:]])
        distances=np.array([float(tree.find_nearest(Vector(p))[3]) for p in samples])
        i=int(distances.argmin());step=float(np.linalg.norm(np.diff(samples,axis=0),axis=1).max())
        bound=float(distances[i]-step/2-meta['curve_error_bound_mm']-OD/2-1e-4)
        # If this complete continuous curve stays outside the surface by the
        # bound, containment cannot change without crossing the surface.
        tiny=manifold.Manifold.sphere(.01,16).translate(samples[0].tolist())
        inside=(tiny^sweep).volume()>tiny.volume()/2
        row={'feed_phase_deg':phase,'other_pin':pin,'other_installed_phase_deg':selected['azimuth_deg'],
            'status':'PASS' if bound>=0 and not inside else 'BLOCKED',
            'outside_swept_clearance_envelope_bound_mm':bound,'curve_start_inside_sweep':bool(inside),
            'nearest_sample_mm':samples[i].tolist(),'sample_step_mm':step,
            'curve_chord_error_bound_mm':meta['curve_error_bound_mm']}
        rows.append(row)
result={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    'scope':'Local bare-contact/trailing-wire/affine-shift swept envelopes against the other three installed UART wires, at yaw/pitch zero',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(ORDER_SCRIPT),'source_helper_sha256':sha(ORDER_HELPER),
    'source_construction_sha256':sha(OUT/'candidate_screen.json'),'source_sweeps':inputs,
    'source_curves_sha256':sha(ORDER_DIR/'body_prefix_v2/body_to_yaw_curves.npz'),
    'source_packing_sha256':sha(ORDER_DIR/'body_prefix_v2/packing.json'),
    'rows':rows,'directed_pair_count':len(rows),'all_local_feed_orders_clear':all(r['status']=='PASS' for r in rows),
    'body_tail_placement':'NOT_TESTED','hand_and_tool_access':'NOT_TESTED',
    'other_seven_dynamic_conductors':'NOT_TESTED','main_applied':False,
    'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ORDER_START}
(OUT/'local_wire_order.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('J3_LOCAL_WIRE_ORDER',result['status'],min(r['outside_swept_clearance_envelope_bound_mm'] for r in rows),flush=True)
