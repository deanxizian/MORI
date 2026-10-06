"""Temporarily move the connected CAM supply pair, without moving its roots.

This is a static staging screen up to the existing open upper endpoints. Full
USB plug/leads, material-length compensation and restoration are not implied.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints'
OUT=REST/'power_staging';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
from upper_pack_geometry import refined
from curve_self_partition import self_clear
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
curvefile=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(curvefile)
inputs=[curvefile,BASE/'cam_side_fans/c6_join/join_review.json',REST/'power_cover_dependency/review.json',
        HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py',HERE/'curve_self_partition.py',HERE/'upper_pack_geometry.py']
for rpath in [inputs[1],inputs[2]]:
    r=read(rpath)
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
original=ctx.targets;ctx.targets=dict(original)
for name,file in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
                  ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz')]:
    inputs.append(file);a=np.load(file);ctx.targets[name]=ctx.target(manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64))))
other_names=[*[f'CAM_{i}' for i in range(1,5)],'P_J9_1','P_J9_2','P_J9_3','SPK_reservation_3','SPK_reservation_6']
others={name:prepared(refined(curves[name+'_y0'+('_p0' if name.startswith('CAM_') else '')],.01),
    .3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842,.0003) for name in other_names}
smooth=lambda t:6*np.clip(t,0,1)**5-15*np.clip(t,0,1)**4+10*np.clip(t,0,1)**3
arrays={};rows=[]
polylen=lambda p:float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
for degrees in [22.,26.,30.]:
    angle=math.radians(degrees);parts={};details=[]
    for name in ['P_J18_1','P_J18_2']:
        source=curves[name+'_y0'];r=np.linalg.norm(source[:,:2],axis=1)
        weight=smooth((source[:,2]-126)/16)*smooth((30-r)/18);theta=angle*weight
        p=source.copy();p[:,0]=source[:,0]*np.cos(theta)-source[:,1]*np.sin(theta);p[:,1]=source[:,0]*np.sin(theta)+source[:,1]*np.cos(theta)
        assert np.linalg.norm(p[0]-source[0])<1e-12
        # Conservative map Lipschitz and Hessian bounds propagate the source
        # chord error and bound deviation of mapped vertex chords.
        grad=1.875/16+1.875/18
        hess=5.774/16**2+5.774/18**2+2*(1.875/16)*(1.875/18)+(1.875/18)/12
        lipschitz=1+30.1*angle*grad
        second=2*angle*grad+30.1*(angle*hess+angle**2*grad**2)
        ds=float(np.linalg.norm(np.diff(source,axis=0),axis=1).max())
        error=lipschitz*.0003+second*ds*ds/8
        p=refined(p,.01);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];i=int(np.searchsorted(s,5.))
        stem=ctx.clear(p[:i+1],radius=.5842,chord_error=error,ignore=['Plug_power_J18'])
        tail=ctx.clear(p[i:],radius=.5842,chord_error=error)
        part=prepared(p,.5842,error);parts[name]=part;pairs=[]
        if not stem and not tail:
            for other,item in others.items():
                result=pair_threshold(part,item)
                if result['status']!='PASS':pairs.append(dict(other=other,**result))
        sr=self_clear(part) if not stem and not tail and not pairs else dict(status='NOT_TESTED')
        a=np.diff(p,axis=0);cross=np.linalg.norm(np.cross(a[:-1],a[1:]),axis=1);good=cross>1e-10
        radius=np.linalg.norm(a[:-1],axis=1)*np.linalg.norm(a[1:],axis=1)*np.linalg.norm(a[:-1]+a[1:],axis=1)/np.maximum(2*cross,1e-30)
        minradius=float(radius[good].min()) if np.any(good) else None
        row=dict(wire=name,status='BLOCKED' if stem or tail or pairs or sr['status']=='BLOCKED' else 'PASS',
                 root_fixed=True,stem=stem,tail=tail,wire_pairs=pairs,self_review=sr,
                 mapped_curve_error_bound_mm=error,map_lipschitz_bound=lipschitz,map_second_derivative_bound=second,
                 minimum_three_point_radius_mm=minradius,reference_length_mm=polylen(source),staging_length_mm=polylen(p),
                 length_change_mm=polylen(p)-polylen(source),open_upper_endpoint_mm=p[-1].tolist())
        details.append(row);arrays[f'deg{degrees:g}_{name}']=p
    mutual=pair_threshold(parts['P_J18_1'],parts['P_J18_2'])
    row=dict(degrees=degrees,status='PASS' if all(x['status']=='PASS' for x in details) and mutual['status']=='PASS' else 'BLOCKED',wires=details,mutual=mutual)
    rows.append(row);print('CAM_POWER_STAGING',json.dumps(row),flush=True)
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'curves.npz',**arrays)
r=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',scope='Static temporary lower supply-wire poses with original J18 roots; no complete leads/plug or material-length control',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,retained_other_upper_wires=other_names,
    deformation='Smooth angular offset; zero outside r30, full below r12; Z126..142 transition; original open upper endpoints move temporarily',
    source_curve_error_assumption_mm=.0003,curve_sha256=sha(OUT/'curves.npz'),
    contact_passage_with_new_supply_poses='NOT_TESTED',restoration_motion='NOT_TESTED',whole_wire_length_control='NOT_TESTED',
    actual_CAM_USB_lead='BLOCKED',full_harness='BLOCKED',main_changed=False,approved=False,C6_main_applied=False,
    Yaw_Reaction_Link_present=True,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('CAM_POWER_STAGING_DONE',r['status'],r['elapsed_s'],flush=True)
