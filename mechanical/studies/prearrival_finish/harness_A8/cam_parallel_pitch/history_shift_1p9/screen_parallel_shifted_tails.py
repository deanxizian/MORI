"""Four identical CAM tails with a gentle lateral shift into the servo gap.

Catalogue/photo allocation only. All wires retain the initial 5 mm straight
departure, use the same analytic path translated by their original X pitch,
and finish along +Y. No main solids or hardware sources are modified.
"""
from pathlib import Path
SHIFT_SCRIPT=Path(__file__).resolve();SHIFT_ROOT=SHIFT_SCRIPT.parent
SHIFT_HELPER=SHIFT_ROOT/'plan_cam_pitch_flex.py';__file__=str(SHIFT_HELPER)
exec(compile(SHIFT_HELPER.read_text().split('\nall_rows=[];saved={}',1)[0],str(SHIFT_HELPER),'exec'),globals())
__file__=str(SHIFT_SCRIPT)
OUT=SHIFT_ROOT/'cam_parallel_pitch';OUT.mkdir(exist_ok=True)

def shifted_tails(radius,shift,shift_length,end_y):
    arc_length=math.pi*radius/2
    extension=end_y-(slots[0,1]+radius)
    assert extension>0 and shift_length<arc_length+extension
    stops=sorted(set([0.,5.,5.+arc_length,5.+shift_length,5.+arc_length+extension]))
    s=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/.04))+1)[:-1] for a,b in zip(stops,stops[1:])]),stops[-1]]
    u=np.clip(s-5.,0.,arc_length);theta=u/radius
    v=np.zeros((len(s),3));v[:,1]=radius*(1-np.cos(theta))+np.maximum(0.,s-5.-arc_length)
    v[:,2]=-np.minimum(s,5.)-radius*np.sin(theta)
    t=np.clip((s-5.)/shift_length,0.,1.)
    v[:,0]=shift*(10*t**3-15*t**4+6*t**5)
    dx=shift/shift_length*(30*t*t-60*t**3+30*t**4)
    ddx=shift/(shift_length**2)*(60*t-180*t*t+120*t**3)
    vel=np.c_[dx,np.sin(theta),-np.cos(theta)]
    acc=np.c_[ddx,np.cos(theta)/radius,np.sin(theta)/radius]
    acc[(s<5.)|(s>5.+arc_length),1:]=0.
    speed=np.linalg.norm(vel,axis=1);cross=np.linalg.norm(np.cross(vel,acc),axis=1)
    radii=np.divide(speed**3,cross,out=np.full_like(speed,np.inf),where=cross>1e-12)
    # Bound of ||r''(s)|| and interpolation error on every span, including
    # the quintic offset. All second-derivative discontinuities are knots.
    acceleration_bound=1/radius+(10*math.sqrt(3)/3)*abs(shift)/(shift_length**2)
    error=acceleration_bound*.04**2/8
    return [v+e for e in slots],[error]*4,float(radii.min()),s,v

trials=[];selected=None
for radius,sl in itertools.product([7.2,7.5,8.,8.5],[16.,17.,18.]):
    paths,errors,rad,parameters,offset=shifted_tails(radius,1.9,sl,12.)
    hit={'reason':'sampled_curvature','radius_mm':rad} if rad<REQUIRED_R else check_paths(paths,errors,True)
    gap=None
    if hit is None:
        gap=pair_gap(paths,errors)
        if gap<.3:hit={'reason':'four_wire_gap','gap_bound_mm':gap}
    row={'radius_mm':radius,'shift_x_mm':1.9,'shift_length_mm':sl,'end_y_mm':12.,
         'minimum_sampled_radius_mm':rad,'curve_error_bound_mm':errors[0],
         'status':'PASS' if hit is None else 'BLOCKED','hit':hit,'pair_surface_gap_bound_mm':gap}
    trials.append(row)
    print('SHIFTED_TAIL',radius,sl,row['status'],hit,flush=True)
    if hit is None:
        selected={**row,'endpoints_mm':[p[-1].tolist() for p in paths]}
        np.savez_compressed(OUT/'shifted_tails.npz',**{f'slot{i}':p for i,p in enumerate(paths)},arc_parameter_mm=parameters)
        break
result={'status':'PASS' if selected else 'BLOCKED','selected':selected,'trials':trials,
        'source_main_sha256':source_hash,'script_sha256':sha(SHIFT_SCRIPT),'helper_sha256':sha(SHIFT_HELPER),
        'wire_OD_mm':OD,'required_surface_gap_mm':.3,'required_radius_mm':REQUIRED_R,
        'actual_mating_and_photo_uncertainty':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False}
(OUT/'shifted_tail_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
