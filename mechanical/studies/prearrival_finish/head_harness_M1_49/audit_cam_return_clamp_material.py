"""Ensure the proposed fixed return clamp grips the same material at every pose."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
ctx=Context();started=time.time();C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
cr=json.loads((C/'review.json').read_text());jr=json.loads((J/'join_review.json').read_text());assert cr['status']==jr['status']=='PASS'
for r in [cr,jr]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(J/'candidate_curves.npz')==jr['curve_sha256'];curves=np.load(J/'candidate_curves.npz');rows=[];summary=[]
for pin in range(1,5):
    x=-26.600000143051147-pin+1;values=[];body=[]
    for yaw,pitch in itertools.product(range(-60,61,10),range(-20,26,5)):
        q=curves[f'CAM_{pin}_y{yaw}_p{pitch}'];inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch)));p=q@inv[:3,:3].T+inv[:3,3]
        line=(np.abs(p[:,0]-x)<1e-5)&(np.abs(p[:,1]+20.800000190734863)<1e-5)
        ids=np.flatnonzero(line[:-1]&line[1:]&(p[:-1,2]>=215.)&(p[1:,2]<215.));assert len(ids)==1,(pin,yaw,pitch,len(ids))
        i=int(ids[0]);f=(215.-p[i,2])/(p[i+1,2]-p[i,2]);point=p[i]+f*(p[i+1]-p[i])
        ds=np.linalg.norm(np.diff(q,axis=0),axis=1);s=float(ds[:i].sum()+f*ds[i]);length=float(ds.sum());tail=length-s
        values.append(tail);body.append(s);rows.append(dict(pin=pin,yaw=yaw,pitch=pitch,clamp_pitch_point_mm=point.tolist(),from_body_mm=s,from_CAM_port_mm=tail))
    summary.append(dict(pin=pin,from_CAM_port_min_mm=min(values),from_CAM_port_max_mm=max(values),
                        from_CAM_material_range_mm=max(values)-min(values),from_body_material_range_mm=max(body)-min(body)))
ctx.assert_unchanged();inputs=[C/'review.json',J/'join_review.json',J/'candidate_curves.npz',REST/'material_stations.json']
r=dict(status='PASS' if max(max(x['from_CAM_material_range_mm'],x['from_body_material_range_mm']) for x in summary)<.01 else 'BLOCKED',
       scope='Geometric material station at the proposed fixed return clamp; no grip force or cable fatigue qualification',
       sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},head_poses=130,station_checks=len(rows),clamp_plane_pitch_z_mm=215.,summary=summary,rows=rows,
       yaw_guide_must_slide=True,physical_clamping='NOT_TESTED',main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(REST/'return_material_stations.json').write_text(json.dumps(r,indent=2)+'\n');print('RETURN_MATERIAL',r['status'],summary,flush=True)
