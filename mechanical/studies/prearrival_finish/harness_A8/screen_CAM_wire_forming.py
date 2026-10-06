"""Screen constant-length folding from upright free leads to CAM loop.

No source geometry changes. The CAM board, display and shells are not yet
installed. The CAM tie is not tightened; its final closed ring is omitted
and must later receive a separately checked placement/tightening operation.
This is an initial path screen, not a complete harness assembly release.
"""
from pathlib import Path
FM_SCRIPT=Path(__file__).resolve();FM_ROOT=FM_SCRIPT.parent
FM_HELPER=FM_ROOT/'check_CAM_board_last.py';__file__=str(FM_HELPER)
exec(compile(FM_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(FM_HELPER),'exec'),globals())
__file__=str(FM_SCRIPT)
FM_OUT=FM_ROOT/'cam_wire_forming';FM_OUT.mkdir(exist_ok=True)
fm_begin=time.time();fm_step=.035
fm_deferred={'CAM_connector_tie_head','CAM_connector_tie_band'}
fm_targets=[pw_obstacle(n,'fixed',m) for n,m in bl_fixture.items() if n not in fm_deferred]
fm_core0,fm_tails0,fm_meta=bl_curves(0.,0.)
fm_R=7.5;fm_ext=float(wi_b[1]-(slots[0,1]+fm_R))
fm_lengths=[bl_height0,math.pi*wi_rt,230.+bl_height0-wi_zero_turn,math.pi*fm_R/2.,.5,fm_ext,math.pi*fm_R/2.,5.]
fm_angles=[0.,math.pi,0.,math.pi/2.,0.,0.,math.pi/2.,0.]
fm_core_length=sum(fm_lengths[:5]);fm_tail_parameter=fm_ext+math.pi*fm_R/2.
assert abs(fm_core_length-wi_L)<1e-9


def fm_curve(fraction):
    arrays=[];parameters=[];p=np.array([xx[0],-1.5,230.]);theta=0.;total=0.
    for length,turn in zip(fm_lengths,fm_angles):
        s=np.linspace(0.,length,max(1,math.ceil(length/fm_step))+1)
        k=fraction*turn/length
        if abs(k)<1e-12:
            y=s*math.sin(theta);z=s*math.cos(theta)
        else:
            y=(math.cos(theta)-np.cos(theta+k*s))/k
            z=(np.sin(theta+k*s)-math.sin(theta))/k
        q=p+np.c_[np.zeros(len(s)),y,z]
        arrays.append(q[:-1]);parameters.append(total+s[:-1]);p=q[-1];theta+=fraction*turn;total+=length
    base=np.vstack(arrays+[p[None,:]]);s=np.r_[np.concatenate(parameters),total]
    u=np.clip((fm_tail_parameter-(s-fm_core_length))/16.,0.,1.)
    base[:,0]=slots[0,0]+1.8875*(10*u**3-15*u**4+6*u**5)
    acceleration=fraction/min(wi_rt,fm_R)+(10*math.sqrt(3)/3)*1.8875/16.**2
    error=acceleration*fm_step**2/8.
    return base,s,error


fm_reference,_,_=fm_curve(1.)
assert np.linalg.norm(fm_reference[0]-fm_core0[0])<1e-8
assert np.linalg.norm(fm_reference[-1]-fm_tails0[0][0])<1e-8
fm_rows=[];fm_curves={}
for fraction in np.linspace(0.,1.,41):
    base,parameter,error=fm_curve(float(fraction));hits=[];wire_pairs=[]
    for slot in range(4):
        points=base+[xx[slot]-xx[0],0,0]
        fm_curves[f'f{fraction:.3f}_slot{slot}']=points
        for name,group,m,lo,hi,tree in fm_targets:
            keep=np.ones(len(points),bool)
            if name in {'Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band'}:
                keep&=~((parameter<=4.3+1e-5)&(abs(points[:,1]+1.5)<1e-5))
            # Keep only the established final seating-contact exception.
            # Intermediate contact with the support is deliberately reported.
            if fraction==1. and name=='Pitch_Cradle':
                keep&=~((abs(points[:,0]-slots[slot,0])<1e-5)&(abs(points[:,1]-slots[slot,1])<1e-5)
                    &(points[:,2]>=slots[slot,2]-5.-1e-5)&(points[:,2]<=slots[slot,2]+1e-5))
            ids=np.flatnonzero(keep)
            for span in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
                if len(span)<2:continue
                hit=check_one(points[span],error,lo,hi,m,tree)
                if hit:
                    hits.append({'slot':slot,'object':name,**hit});break
            if hits:break
        if hits:break
    fm_rows.append({'fraction':float(fraction),'status':'BLOCKED' if hits else 'PASS','hits':hits,
        'end_slot0_mm':base[-1].tolist(),'max_z_mm':float(base[:,2].max()),
        'curve_error_mm':error,'sampling_only':True})
    print('CAM_FORMING',round(float(fraction),3),fm_rows[-1]['status'],hits[:1],flush=True)
np.savez_compressed(FM_OUT/'curves.npz',**fm_curves)
fm_report={
 'status':'PASS' if all(r['status']=='PASS' for r in fm_rows) else 'BLOCKED',
 'scope':'41 configurations of simultaneous curvature scaling at constant material length; wire-to-stage-solid screen only',
 'source_main_sha256':source_hash,'script_sha256':sha(FM_SCRIPT),'helper_sha256':sha(FM_HELPER),
 'source_board_last_sha256':sha(FM_ROOT/'cam_board_last/screen.json'),'curves_sha256':sha(FM_OUT/'curves.npz'),
 'rows':fm_rows,'uninstalled_CAM_board':True,'untightened_tie_final_solids_omitted':sorted(fm_deferred),
 'uninstalled_other_pitch_parts':wi_excluded,'source_solids_considered':len(fm_targets),
 'shape_rule':'All installed planar tangent turns are scaled by f at unchanged segment arclength; X quintic stays fixed in that arclength coordinate.3D length is independent of f.',
 'minimum_bend_radius_bound_mm':fm_meta['minimum_radius_bound_mm'],
 'terminal_and_crimp_shapes':'NOT_TESTED','continuous_sweep':'NOT_TESTED','wire_packing':'NOT_TESTED',
 'initial_feed_to_upright_state':'NOT_TESTED','hand_operation':'NOT_TESTED','main_applied':False,
 'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fm_begin,
}
(FM_OUT/'screen.json').write_text(json.dumps(fm_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_WIRE_FORMING_DONE',fm_report['status'],flush=True)
