"""Recheck explicit old tool/tail solids against new current candidates and routes."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'tool_angles_extended'
OUT.mkdir(parents=True,exist_ok=True);OLD=HERE.parent/'cam_retention_M1_48'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
con=read(REST/'return_clamp_v3/review.json');guide=read(REST/'sliding_guide_v4/review.json');routes=read(BASE/'cam_side_fans/c6_join/join_review.json')
for r in [con,guide,routes]:
    assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
old=read(OLD/'tools_and_tail.json');excluded=set(old['not_yet_installed']);assert all(n in ctx.ss for n in excluded)
def stored(p):
    a=np.load(p);return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
targets={n:t['m'] for n,t in ctx.targets.items() if n not in excluded}
paths=[REST/'return_clamp_v3/review.json',REST/'sliding_guide_v4/review.json',BASE/'cam_side_fans/c6_join/join_review.json',OLD/'tools_and_tail.json']
for n,folder,fname in [('Pitch_Cradle','return_clamp_v3','Pitch_Cradle_candidate'),('Pitch_Yoke','sliding_guide_v4','Pitch_Yoke_candidate'),('connector_band','return_clamp_v3','band'),('connector_head','return_clamp_v3','head')]:
    p=REST/folder/(fname+'.npz');paths.append(p);targets[n]=stored(p)
npz=BASE/'cam_side_fans/c6_join/candidate_curves.npz';assert sha(npz)==routes['curve_sha256'];paths.append(npz);allcurves=np.load(npz)
curves={n:allcurves[f'{n}_y0'+('_p0' if n.startswith('CAM_') else '')] for n in ['CAM_1','CAM_2','CAM_3','CAM_4','P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']}
def check(m):
    bb=np.asarray(m.bounding_box());hits=[];contacts=[]
    for n,t in targets.items():
        tb=np.asarray(t.bounding_box())
        if not (np.all(bb[:3]<=tb[3:]+.301) and np.all(bb[3:]+.301>=tb[:3])):continue
        v=float((m^t).volume());d=float(m.min_gap(t,.301)) if abs(v)<1e-7 else 0.
        row=dict(target=n,overlap_mm3=v,gap_mm=d)
        if n in ['connector_band','connector_head']:
            contacts.append(row)
            if abs(v)>1e-5:hits.append(row)
        elif abs(v)>1e-6 or d<.3-1e-5:hits.append(row)
    tg=ctx.target(m);wire_hits=[]
    for n,p in curves.items():
        radius=.3302 if n.startswith('CAM_') else .4445 if n.startswith('SPK_') else .5842
        ds=np.linalg.norm(np.diff(p,axis=0),axis=1);bound=radius+.3+np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2+.0004
        ids=np.flatnonzero(np.all(p>=tg['lo']-bound[:,None],axis=1)&np.all(p<=tg['hi']+bound[:,None],axis=1))
        for i in ids:
            d=float(tg['tree'].find_nearest(Vector(p[i]))[3])
            if d<bound[i]:wire_hits.append(dict(wire=n,point_mm=p[i].tolist(),distance_mm=d,required_mm=float(bound[i])));break
    return dict(status='PASS' if not hits and not wire_hits else 'BLOCKED',native_hits=hits,wire_hits=wire_hits,intended_tie_operation=contacts)
previous=read(REST/'tool_access/review.json');assert previous['results'][1]['status']=='PASS'
paths.append(REST/'tool_access/review.json')
p=OLD/'connector_0_cutter_sweep.npz';paths.append(p)
pivot=np.array([-15.900000143051148,-18.910000190734863,210.65])+[-17.97,0.,3.]
base=stored(p).translate([-17.97,0.,3.]);results=[]
for angle in [15.,30.,45.,60.,75.,90.,120.,150.,180.,-120.,-150.]:
    m=base.translate((-pivot).tolist()).rotate([0.,angle,0.]).translate(pivot.tolist())
    rr=check(m);rr.update(angle_about_tail_y_deg=angle,pivot_mm=pivot.tolist());results.append(rr)
    a=m.to_mesh64();fname=f'cutter_{angle:g}.npz';np.savez_compressed(OUT/fname,vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
    print('CURRENT_CUTTER_ANGLE',angle,rr['status'],rr['native_hits'][:1],rr['wire_hits'][:1],flush=True)
ctx.assert_unchanged()
r=dict(status='PASS' if any(x['status']=='PASS' for x in results) else 'BLOCKED',
       scope='Finite roll angles around the unchanged tie-tail axis; same conservative tool sweep, current solids and eleven paths',sources=ctx.sources,
       inputs={str(p.relative_to(ROOT)):sha(p) for p in paths},not_yet_installed=sorted(excluded),results=results,
       output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},assumed_ribbon_bending=True,actual_tightening_and_cutting='NOT_TESTED',full_wired_assembly='NOT_TESTED',
       main_changed=False,approved=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('CURRENT_RESTRAINT_TOOLS_DONE',r['status'],flush=True)
