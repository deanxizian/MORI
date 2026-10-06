"""Continuous packing of the unchanged CAM board-last wire family.

The connector and board move by the same h-family during two different
assembly legs. No wire lengths, diameters or mechanical parts are changed.
Use exact subset/separation arguments where possible, and Lipschitz bounds
on the remaining core and material-point motion, not pose samples alone.
"""
from pathlib import Path
CP_SCRIPT=Path(__file__).resolve();CP_ROOT=CP_SCRIPT.parent
CP_HELPER=CP_ROOT/'check_CAM_board_last.py';__file__=str(CP_HELPER)
exec(compile(CP_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(CP_HELPER),'exec'),globals())
__file__=str(CP_SCRIPT)
CP_OUT=CP_ROOT/'cam_board_last';cp_started=time.time()
cp_source=json.loads((CP_OUT/'screen.json').read_text());assert cp_source['status']=='PASS'
cp_D=1+math.pi/2.;cp_shape_speed=1/cp_D
cp0,cp_tails0,cp_meta0=bl_curves(0.,0.)
cp6,cp_tails6,cp_meta6=bl_curves(6.,0.)
cp_top=np.array([xx[0],-1.5,230.+bl_height0])
cp_top_i=int(np.argmin(np.linalg.norm(cp0-cp_top,axis=1)))
assert np.linalg.norm(cp0[cp_top_i]-cp_top)<1e-8
cp_static=[];cp_intervals=[];cp_unproved=[];cp_tests=0
cp_max_tails={};cp_fixed_cores={}


def cp_against_prefixes(sample,error,slot,own_join=False):
    checks=[]
    for other in range(4):
        if other==slot and own_join:
            r=own_prefix_check(sample,pw_fans[other],error,pw_fan_errors[other])
        else:
            r=pair(sample,pw_fans[other],error,pw_fan_errors[other])
        checks.append({'target':'fan','slot':other,**r})
        if r['status']!='PASS':return {'status':'BLOCKED','checks':checks}
    for yaw in range(-60,61,10):
        mat=np.asarray(rigidtr(yaw,0))
        moved=(sample[0]@mat[:3,:3].T+mat[:3,3],sample[1],None,sample[3])
        for pin in range(1,5):
            r=pair(moved,body_samples[pin,yaw],error,body_error)
            checks.append({'target':'body_prefix','pin':pin,'yaw_deg':yaw,**r})
            if r['status']!='PASS':return {'status':'BLOCKED','checks':checks}
    return {'status':'PASS','checks':checks}


for slot in range(4):
    fixed=fine(cp0[:cp_top_i+1]+[xx[slot]-xx[0],0,0],.01)
    cp_fixed_cores[slot]=fixed
    r=cp_against_prefixes(fixed,0.,slot,True)
    cp_static.append({'piece':'fixed_core','slot':slot,**r})
    # This longer envelope is NOT a cutting length or an extra wire reserve:
    # its first straight reaches h=6, and its last straight reaches h=0.
    # Every actual tail for0<=h<=6 is a contiguous subset of it.
    maximum=np.vstack([wi_line(cp_tails0[slot][0]+[0,0,6.],cp_tails0[slot][0],.01)[:-1],cp_tails0[slot]])
    sm=fine(maximum,.01);cp_max_tails[slot]=(sm,cp_meta0['tail_error_mm'])
    r=cp_against_prefixes(sm,cp_meta0['tail_error_mm'],slot)
    cp_static.append({'piece':'maximum_tail_union','slot':slot,**r})
    print('CONTINUOUS_PACK_STATIC',slot,r['status'],round(time.time()-cp_started,2),flush=True)
for a,b in itertools.combinations(range(4),2):
    sa,ea=cp_max_tails[a];sb,eb=cp_max_tails[b]
    cp_static.append({'piece':'tail_pair_union','slots':[a,b],**pair(sa,sb,ea,eb)})

# Each core stays at its own constant X. The tail's nonconstant-X part
# finishes16mm after its first straight; its Y maximum is below every core.
# Afterwards each tail shares its own core's X, so other wires have>=1mm
# centerline separation independently of h and of the nearest parameters.
cp_lateral_y=float(slots[0,1]+7.5+(16.-math.pi*7.5/2.))
cp_lateral_separation=-1.5-cp_lateral_y
cp_pitch=float(np.min(np.diff(xx)));assert cp_pitch>.999999
cp_axis_gap=cp_pitch-OD
cp_axis_checks=[
    {'pair':'different_core_to_core','status':'PASS' if cp_axis_gap>=.3 else 'BLOCKED','surface_gap_bound_mm':cp_axis_gap},
    {'pair':'core_to_other_tail_after_lateral_transition','status':'PASS' if cp_axis_gap>=.3 else 'BLOCKED','surface_gap_bound_mm':cp_axis_gap},
    {'pair':'core_to_any_tail_root_or_lateral_transition','status':'PASS' if cp_lateral_separation-OD>=.3 else 'BLOCKED',
     'maximum_lateral_transition_y_mm':cp_lateral_y,'surface_gap_bound_mm':cp_lateral_separation-OD},
]
assert all(abs((xx[i]-slots[i,0])-1.8875)<1e-7 for i in range(4))
assert min(cp0[:,1].min(),cp6[:,1].min())>=-1.5000001

# At fixed material arclength measured from the stationary neck end, speed
# is bounded by1mm/mm. For upper semicircle r'=-1/(2D), the sum bound is
# |r'|(2+pi)=1. Lower arc combines horizontal1/D with tangential pi/(2D).
# Along the fixed tail, total upstream length changes by-h, giving unit
# tangential speed. It is NOT necessary to pretend the entire wire is rigid.
cp_material_speed=(2.+math.pi)/(2.*cp_D);assert abs(cp_material_speed-1.)<1e-12
cp_R=min(cp_meta0['minimum_radius_bound_mm'],cp_meta6['minimum_radius_bound_mm'])
cp_tail_slope=1.8875*1.875/16.
cp_max_arc_step=.02*math.sqrt(1+cp_tail_slope**2)
cp_max_length=150.
# Projection on the segment midpoint tangent gives
# arc-chord <= arc*(kappa*arc)^2/8. Summing gives this conservative bound.
cp_arclength_error=cp_max_length*(cp_max_arc_step/cp_R)**2/8.
assert cp_arclength_error<.001
cp_local_cutoff=1.95
assert 2.-.02-2*cp_arclength_error>cp_local_cutoff


def cp_self(sample,error):
    p,s,tree,step=sample;threshold=OD+.3+step+2*error+1e-4
    for i,q in enumerate(p):
        found=[(j,float(d)) for _,j,d in tree.find_range(Vector(q),threshold)
               if abs(float(s[j]-s[i]))>cp_local_cutoff]
        if found:
            j,d=min(found,key=lambda item:item[1])
            return {'status':'BLOCKED','sample_indices':[i,j],'distance_mm':d,'required_mm':threshold}
    return {'status':'PASS','tested_local_arclength_cutoff_mm':cp_local_cutoff}


def cp_check(a,b):
    mid=(a+b)/2.;half=(b-a)/2.;core,tails,meta=bl_curves(mid,0.)
    ti=int(np.argmin(np.linalg.norm(core-cp_top,axis=1)))
    assert np.linalg.norm(core[ti]-cp_top)<1e-8
    rows=[]
    for slot in range(4):
        c=core+[xx[slot]-xx[0],0,0]
        r=cp_against_prefixes(fine(c[ti:],.01),meta['core_error_mm']+cp_shape_speed*half,slot)
        rows.append({'kind':'flex_core_vs_fixed_fans_and_body','slot':slot,**r})
        if r['status']!='PASS':return {'status':'BLOCKED','checks':rows}
        whole=np.vstack([c,tails[slot][-2::-1]])
        sample=fine(whole,.01)
        assert sample[1][-1]+cp_arclength_error<cp_max_length
        error=max(meta['core_error_mm'],meta['tail_error_mm'])+cp_material_speed*half
        r=cp_self(sample,error);rows.append({'kind':'complete_wire_nonlocal_self','slot':slot,**r})
        if r['status']!='PASS':return {'status':'BLOCKED','checks':rows}
    return {'status':'PASS','checks':rows}


def cp_interval(a,b,depth=0):
    global cp_tests
    cp_tests+=1;r=cp_check(a,b)
    if r['status']!='PASS' and depth<9:
        m=(a+b)/2.;cp_interval(a,m,depth+1);cp_interval(m,b,depth+1)
    elif r['status']!='PASS':
        cp_unproved.append({'interval_mm':[a,b],**r})
    else:
        cp_intervals.append({'interval_mm':[a,b],**r})
        print('CONTINUOUS_PACK_INTERVAL',a,b,'PASS',round(time.time()-cp_started,2),flush=True)


if all(r['status']=='PASS' for r in cp_static+cp_axis_checks):
    cp_interval(0.,6.)
cp_all=sorted(cp_intervals+cp_unproved,key=lambda r:r['interval_mm'][0])
if cp_all:
    assert cp_all[0]['interval_mm'][0]==0 and cp_all[-1]['interval_mm'][1]==6
    assert all(a['interval_mm'][1]==b['interval_mm'][0] for a,b in zip(cp_all,cp_all[1:]))
cp_ok=bool(cp_all) and not cp_unproved and all(r['status']=='PASS' for r in cp_static+cp_axis_checks)
cp_report={
 'status':'PASS' if cp_ok else 'BLOCKED',
 'scope':'Continuous mutual/self clearance of the four CAM wires and fixed fan/body prefixes for the unchanged6mm CAM mating/seating family',
 'source_main_sha256':source_hash,'script_sha256':sha(CP_SCRIPT),'helper_sha256':sha(CP_HELPER),
 'source_screen_sha256':sha(CP_OUT/'screen.json'),
 'static_subset_checks':cp_static,'analytical_axis_separation':cp_axis_checks,
 'adaptive_intervals':cp_intervals,'unproved_intervals':cp_unproved,'interval_tests':cp_tests,
 'material_speed_bound_mm_per_mm':cp_material_speed,'core_shape_speed_bound_mm_per_mm':cp_shape_speed,
 'arclength_deficit_upper_bound_mm':cp_arclength_error,'maximum_actual_curve_length_bound_mm':cp_max_length,
 'self_contact_nonlocal_arclength_mm':2.,'numerical_self_cutoff_mm':cp_local_cutoff,
 'minimum_required_surface_gap_mm':.3,'wire_od_mm':OD,'minimum_bend_radius_mm':cp_R,
 'stages_covered':['plug_mates_to_board_held6mm_up','mated_board_lowers6mm'],
 'coordinate_scope':'The assembly family has pitch zero; additional body-prefix comparisons include thirteen stored yaw angles, not a full dynamic flex solution.',
 'curve_formation_and_terminal_feed':'NOT_TESTED','tie_threading_tightening':'NOT_TESTED',
 'complete_head_eleven_conductors':'BLOCKED','physical_force_friction_life':'NOT_TESTED',
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
 'elapsed_s':time.time()-cp_started,
}
(CP_OUT/'continuous_packing.json').write_text(json.dumps(cp_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_BOARD_CONTINUOUS_PACKING_DONE',cp_report['status'],len(cp_intervals),len(cp_unproved),flush=True)
