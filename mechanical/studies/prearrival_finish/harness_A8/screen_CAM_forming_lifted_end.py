"""Form at the already modeled +6mm CAM lead state before board insertion.

This is an assembly-path alternative only, not a change to installed routing,
wire length, robot geometry or the user-approved hardware datums.
"""
from pathlib import Path
FL_SCRIPT=Path(__file__).resolve();FL_ROOT=FL_SCRIPT.parent
FL_HELPER=FL_ROOT/'check_CAM_forming_terminals.py';__file__=str(FL_HELPER)
exec(compile(FL_HELPER.read_text().split('\nfor fraction in np.linspace',1)[0],str(FL_HELPER),'exec'),globals())
__file__=str(FL_SCRIPT)
FL_OUT=FM_OUT/'lifted_end';FL_OUT.mkdir(exist_ok=True);fl_started=time.time()
fl_installed_lengths=fr_lengths.copy();fl_installed_core=fm_core_length;fl_installed_tail=fm_tail_parameter
fl_h=6.;fl_shrink=fl_h/(1.+math.pi/2.);fl_rt=wi_rt-fl_shrink/2.
fr_lengths[1]=math.pi*fl_rt;fr_lengths[5]-=fl_shrink;fr_lengths[7]+=fl_h
fm_core_length=sum(fr_lengths[:5]);fm_tail_parameter=sum(fr_lengths[5:7]);fm_lengths[:]=fr_lengths
assert abs(sum(fr_lengths)-sum(fl_installed_lengths))<1e-10
fl_end=sum(fr_lengths);fl_seat=(fl_end-5.-fl_h,fl_end-fl_h)
fl_targets=[t for t in fm_targets if t[0]!='Pitch_Cradle']
fl_bed=pw_readsolid(WI_ANCHOR/'z212.0_bed.npz');fl_cradle=next(t[2] for t in fm_targets if t[0]=='Pitch_Cradle')
fl_targets+=[pw_obstacle('Pitch_Cradle_without_CAM_bed','fixed',fl_cradle-fl_bed),pw_obstacle('CAM_bed_only','fixed',fl_cradle^fl_bed)]


def fl_check(base,parameter,error,slot):
    points=base+[xx[slot]-xx[0],0.,0.]
    for target in fl_targets:
        name,group,m,lo,hi,tree=target
        if name in {'Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band'}:pieces=[(parameter>=4.3,.3)]
        elif name=='CAM_bed_only':
            # The +6mm final wire has the same exact physical seating span;
            # its material coordinate lies6mm behind the terminal departure.
            pieces=[(parameter<=fl_seat[0]+1e-9,.3),((parameter>=fl_seat[0]-1e-9)&(parameter<=fl_seat[1]+1e-9),0.),(parameter>=fl_seat[1]-1e-9,.3)]
        else:pieces=[(np.ones(len(parameter),bool),.3)]
        for mask,margin in pieces:
            q=points[mask]
            if len(q)<2:continue
            # check_one includes0.3; subtract it only for the declared seat
            # physical-radius check, never omit a wire span.
            hit=check_one(q,error+margin-.3,lo,hi,m,tree)
            if hit:return {'slot':slot,'object':name,'margin_mm':margin,**hit}
    return None


fl_trials=[];fl_saved={}
for amplitude in [9.,6.,12.]:
    rows=[];saved={}
    for fraction in sorted(set(np.linspace(0.,1.,41).tolist()+np.linspace(.97,1.,31).tolist())):
        base,parameter,error,extra=fr_curve(float(fraction),amplitude)
        # Insert both contact boundaries into the chord representation; each
        # adjoining segment is then covered. Account for interpolation error.
        with_boundaries=np.sort(np.unique(np.r_[parameter,fl_seat]))
        base=np.column_stack([np.interp(with_boundaries,parameter,base[:,i]) for i in range(3)])
        parameter=with_boundaries;error*=2.
        wirehit=None;contacts=[]
        for slot in range(4):
            p=base+[xx[slot]-xx[0],0.,0.];saved[f'f{fraction:.3f}_slot{slot}']=p
            wirehit=fl_check(base,parameter,error,slot)
            _,tr=ft_frame(fraction,p[-1]);contacts.append(ft_source(ft_box.transform(tr)))
            if wirehit:break
        rows.append({'fraction':float(fraction),'apex_extra_mm':extra,'wire_failure':wirehit,'contacts':contacts,
            'status':'PASS' if not wirehit and len(contacts)==4 and all(c['status']=='PASS' for c in contacts) else 'BLOCKED'})
    good=all(r['status']=='PASS' for r in rows)
    fl_trials.append({'amplitude_mm':amplitude,'status':'PASS' if good else 'BLOCKED','rows':rows})
    print('LIFTED_END',amplitude,fl_trials[-1]['status'],[(r['fraction'],r['wire_failure'],[c for c in r['contacts'] if c['status']!='PASS']) for r in rows if r['status']!='PASS'][:12],flush=True)
    if good:fl_saved=saved;break
if fl_saved:np.savez_compressed(FL_OUT/'curves.npz',**fl_saved)
base,_,_,_=fr_curve(1.,fl_trials[-1]['amplitude_mm']);bc,bt,bmeta=bl_curves(fl_h,0.)
endpoint_error=float(np.linalg.norm(base[-1]-bt[0][0]));assert endpoint_error<1e-8
rigid=[]
for board_z in np.linspace(fl_h+6.,fl_h,25):
    result=bl_geometry([0.,0.,float(board_z)],[0.,0.,fl_h]);rigid.append({'board_lift_mm':float(board_z),**result})
report={'status':'PASS' if fl_saved and all(r['status']=='PASS' for r in rigid) else 'BLOCKED',
 'scope':f'Finite lifted-terminal forming positions and board descending{fl_h+6.:g}to{fl_h:g}mm; not continuous or full assembly proof',
 'source_main_sha256':source_hash,'script_sha256':sha(FL_SCRIPT),'helper_sha256':sha(FL_HELPER),
 'source_failed_continuous_sha256':sha(FM_OUT/'continuous/screen.json'),'trials':fl_trials,
 'selected_amplitude_mm':fl_trials[-1]['amplitude_mm'] if fl_saved else None,'final_plug_lift_mm':fl_h,
 'final_endpoint_error_mm':endpoint_error,'segment_lengths_mm':fr_lengths,'core_parameter_mm':fm_core_length,'tail_parameter_mm':fm_tail_parameter,
 'upper_radius_mm':fl_rt,'seat_material_interval_mm':list(fl_seat),'total_planar_length_change_mm':sum(fr_lengths)-sum(fl_installed_lengths),
 'mating_rigid_samples':rigid,'continuous_forming':'NOT_TESTED','continuous_mating':'NOT_TESTED',
 'wire_packing':'NOT_TESTED','terminal_insertion_into_housing':'NOT_TESTED','initial_feed_to_upright_state':'NOT_TESTED',
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fl_started}
(FL_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LIFTED_END_DONE',report['status'],report['selected_amplitude_mm'],flush=True)
