"""Wire-only temporary poses informed by the actual yoke wall/floor.

The connected body roots stay fixed. CAM signal wires are not installed at
this stage. These are partial, open-ended supply wires, not full leads.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'power_staging_contour'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
from curve_self_partition import self_clear
from upper_pack_geometry import refined
from mathutils import Vector
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
file=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(file)
inputs=[file,REST/'power_staging/review.json',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py',
        HERE/'curve_self_partition.py',HERE/'upper_pack_geometry.py']
r=read(inputs[1])
for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
original=ctx.targets;ctx.targets=dict(original)
for name,file in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),
                  ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
                  ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz')]:
    inputs.append(file);a=np.load(file)
    ctx.targets[name]=ctx.target(manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64))))
names=['P_J9_1','P_J9_2','P_J9_3','SPK_reservation_3','SPK_reservation_6']
others={n:prepared(refined(curves[n+'_y0'],.01),.4445 if n.startswith('SPK') else .5842,.0003) for n in names}
smooth=lambda t:6*np.clip(t,0,1)**5-15*np.clip(t,0,1)**4+10*np.clip(t,0,1)**3
polylen=lambda p:float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
arrays={};rows=[]
for degrees,forward,left in [(22.,1.,8.),(26.,1.,10.),(26.,1.5,10.),(30.,1.5,12.)]:
    key=f'a{degrees:g}_f{forward:g}_l{left:g}';parts={};details=[];angle=math.radians(degrees)
    for name in ['P_J18_1','P_J18_2']:
        source=curves[name+'_y0'];z=source[:,2];rad=np.linalg.norm(source[:,:2],axis=1)
        theta=angle*smooth((z-126)/16)*smooth((30-rad)/18)
        p=source.copy();p[:,0]=source[:,0]*np.cos(theta)-source[:,1]*np.sin(theta)
        p[:,1]=source[:,0]*np.sin(theta)+source[:,1]*np.cos(theta)
        # Actual first wall normal points predominantly forward. Keep away
        # from it, and return left before the solid upper servo-seat floor.
        f=forward if name=='P_J18_1' else 0.
        p[:,1]+=f*smooth((z-152)/10)*(1-smooth((z-176)/10))
        p[:,0]-=left*smooth((z-181)/14)
        assert np.linalg.norm(p[0]-source[0])<1e-12
        grad=1.875/16+1.875/18
        hess=5.774/16**2+5.774/18**2+2*(1.875/16)*(1.875/18)+(1.875/18)/12
        lipschitz=1+30.1*angle*grad+f*2*1.875/10+left*1.875/14
        second=2*angle*grad+30.1*(angle*hess+angle**2*grad**2)
        second+=f*(2*5.774/10**2+2*(1.875/10)**2)+left*5.774/14**2
        ds=float(np.linalg.norm(np.diff(source,axis=0),axis=1).max())
        error=lipschitz*.0003+second*ds*ds/8
        p=refined(p,.01);s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        i=int(np.searchsorted(s,5.));stem=ctx.clear(p[:i+1],radius=.5842,chord_error=error,ignore=['Plug_power_J18'])
        tail=ctx.clear(p[i:],radius=.5842,chord_error=error);part=prepared(p,.5842,error);parts[name]=part;pairs=[]
        if not stem and not tail:
            for other,item in others.items():
                result=pair_threshold(part,item)
                if result['status']!='PASS':pairs.append(dict(other=other,**result))
        sr=self_clear(part) if not stem and not tail and not pairs else dict(status='NOT_TESTED')
        detail=dict(wire=name,status='BLOCKED' if stem or tail or pairs or sr['status']=='BLOCKED' else 'PASS',
                    stem=stem,tail=tail,wire_pairs=pairs,self_review=sr,error_bound_mm=error,root_fixed=True,
                    length_mm=polylen(p),length_change_mm=polylen(p)-polylen(source),open_end_mm=p[-1].tolist())
        if tail and tail.get('point_mm'):
            point=np.asarray(tail['point_mm']);near,normal,_,dist=ctx.targets[tail['object']]['tree'].find_nearest(Vector(point))
            detail['nearest_surface']=dict(point_mm=list(near),normal=list(normal),distance_mm=dist)
        details.append(detail);arrays[key+'_'+name]=p
    mutual=pair_threshold(parts['P_J18_1'],parts['P_J18_2'])
    row=dict(key=key,degrees=degrees,forward_mm=forward,left_mm=left,wires=details,mutual=mutual,
             status='PASS' if all(x['status']=='PASS' for x in details) and mutual['status']=='PASS' else 'BLOCKED')
    rows.append(row);print('POWER_STAGING_CONTOUR_CASE',json.dumps(row),flush=True)
sections={str(z):{n:ctx.targets[n]['m'].slice(z).to_polygons() for n in ['Pitch_Yoke','Yaw_Reaction_Link','Yaw_Base']}
          for z in [148.,166.,190.,198.]}
(OUT/'sections.json').write_text(json.dumps(sections,default=lambda x:x.tolist())+'\n')
ctx.targets=original;ctx.assert_unchanged();np.savez_compressed(OUT/'curves.npz',**arrays)
review=dict(status='PASS' if any(r['status']=='PASS' for r in rows) else 'BLOCKED',
    scope='Static partial supply-wire staging; no CAM signal wires installed, other five upper wires retained',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    output_geometry={p.name:sha(p) for p in [OUT/'curves.npz',OUT/'sections.json']},
    no_print_changes=True,main_changed=False,approved=False,C6_main_applied=False,Yaw_Reaction_Link_present=True,
    contact_passage='NOT_TESTED',restoration='NOT_TESTED',actual_CAM_USB_leads='BLOCKED',full_harness='BLOCKED',
    material_length='NOT_TESTED: upper open ends move and partial lengths change',minimum_bend='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print('POWER_STAGING_CONTOUR_DONE',review['status'],review['elapsed_s'],flush=True)
