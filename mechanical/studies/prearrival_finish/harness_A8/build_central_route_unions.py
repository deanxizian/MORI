"""Unedited finite-pose source unions for fixed body/yaw endpoint approaches."""
from pathlib import Path
SCRIPT=Path(__file__).resolve();HELPER=SCRIPT.parent.parent/'head_harness/check_outer_neck_probes.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('# Endpoints are named')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
records=[]
for frame,lo,hi in [('body',np.array([-36.,-36.,132.]),np.array([36.,36.,162.])),
                    ('yaw',np.array([-36.,-36.,178.]),np.array([36.,36.,207.]))]:
    box=manifold.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())
    instances=[];sources=[]
    for name,s in ss.items():
        if frame=='body':
            poses=([(y,p) for y in range(-60,61,10) for p in range(-20,26,5)] if s.group=='pitch'
                   else [(y,0) for y in range(-60,61,10)] if s.group=='yaw' else [(0,0)])
        else:
            poses=([(0,p) for p in range(-20,26,5)] if s.group=='pitch' else [(0,0)] if s.group=='yaw'
                   else [(y,0) for y in range(-60,61,10)])
        for yaw,pitch in poses:
            if frame=='body' and s.group in ['yaw','pitch']:
                transform=np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))
            elif frame=='yaw' and s.group=='pitch':transform=np.asarray(rigidtr(0,pitch))
            elif frame=='yaw' and s.group not in ['yaw','pitch']:transform=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
            else:transform=np.eye(4)
            m=s.m.transform(transform[:3,:]);bb=np.asarray(m.bounding_box())
            if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):continue
            clipped=m^box
            if clipped.volume()<=1e-8:continue
            instances.append(clipped);sources.append(dict(object=name,yaw_deg=yaw,pitch_deg=pitch,group=s.group))
    print('A8_ROUTE_UNION_BEGIN',frame,len(instances),flush=True)
    union=manifold.Manifold.batch_boolean(instances,manifold.OpType.Add)
    assert union.status()==manifold.Error.NoError
    mesh=union.to_mesh64();p=OUT/f'central_{frame}_obstacle_union.npz'
    np.savez_compressed(p,vertices_mm=np.asarray(mesh.vert_properties[:,:3]),triangles=np.asarray(mesh.tri_verts))
    records.append(dict(frame=frame,mesh=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        box_bounds_mm=[lo.tolist(),hi.tolist()],source_instances=sources,
        vertex_count=len(mesh.vert_properties),triangle_count=len(mesh.tri_verts)))
    print('A8_ROUTE_UNION_SAVED',frame,len(mesh.tri_verts),round(time.time()-start,2),flush=True)
out=dict(status='PASS',scope='Finite source solid unions only, no modified or added physical parts',
    source_blend_sha256=before,frames=records,main_geometry_changed=False,continuous_motion='NOT_TESTED')
(OUT/'central_route_unions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
