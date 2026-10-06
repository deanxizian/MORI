"""Keep all upper X transitions aligned while seating the four root wires.

The first candidate compensated different fan growth below those transitions,
which displaced the bends relative to each other. Absorb length only in the
existing seven-millimetre terminal straight instead. The source geometry is
unchanged. A tolerance-padded Boolean partition avoids classifying float32
bed remnants as separate non-contact structure; this does not remove solid.
"""
from pathlib import Path
RX_SCRIPT=Path(__file__).resolve();RX_ROOT=RX_SCRIPT.parent
RX_HELPER=RX_ROOT/'plan_CAM_root_seating.py';__file__=str(RX_HELPER)
exec(compile(RX_HELPER.read_text().split('\nrs_rows=[];',1)[0],str(RX_HELPER),'exec'),globals())
__file__=str(RX_SCRIPT)
RX_OUT=RS_OUT/'aligned_tails';RX_OUT.mkdir(exist_ok=True)
rx_started=time.time()
rx_partition_pad=.0001
rs_root_box=box([float(xx.min()-1.2)-rx_partition_pad,-4.5-rx_partition_pad,230.6-rx_partition_pad],
    [float(xx.max()+1.2)+rx_partition_pad,-1.75+rx_partition_pad,233.6+rx_partition_pad])
rs_bed=rs_yoke^rs_root_box;rs_rest=rs_yoke-rs_root_box
rx_diff=max(0.,float((rs_yoke-(rs_bed+rs_rest)).volume()))+max(0.,float(((rs_bed+rs_rest)-rs_yoke).volume()))
assert rx_diff<1e-7 and rs_bed.volume()>1.
rs_targets=[t for t in fm_targets if t[0] not in rs_omitted|{'Pitch_Yoke'}]
rs_targets += [pw_obstacle('Pitch_Yoke_without_root_bed','fixed',rs_rest),pw_obstacle('Root_contact_bed_only','fixed',rs_bed)]


def rs_curves(offset):
    curves=[];info=[];dz=rs_height(offset)
    for slot in range(4):
        fan,L,error,bound=rs_fan(slot,offset);difference=L-rs_initial[slot][1]
        free,original_u,free_error,_=oe_static[slot,0.]
        straight_start=free[-1].copy();straight_start[2]-=7.
        assert np.linalg.norm(np.array([np.interp(straight_start[2],free[:,2],free[:,k]) for k in range(3)])-straight_start)<1e-8
        lower=free[free[:,2]<straight_start[2]-1e-9]
        end=free[-1].copy();end[2]-=difference
        assert 7.-difference>2.
        straight=np.linspace(straight_start,end,max(2,int(math.ceil((7.-difference)/rs_step))+1))
        upper=np.vstack([lower,straight])+np.array([0.,offset,dz])
        assert np.linalg.norm(fan[-1]-upper[0])<1e-8
        q=np.vstack([fan[:-1],upper]);e=max(error,free_error*2)
        bound.update(slot=slot,fan_length_mm=L,fan_length_change_mm=difference,
            terminal_straight_remaining_mm=7.-difference,whole_length_change_mm=L-rs_initial[slot][1]-difference,
            length_compensation_bound_mm=(bound['length_upper_mm']-bound['length_lower_mm'])+
                (rs_initial[slot][3]['length_upper_mm']-rs_initial[slot][3]['length_lower_mm']),
            root_mm=fan[-1].tolist(),free_end_mm=q[-1].tolist(),curve_error_bound_mm=e)
        curves.append(q);info.append(bound)
    return curves,info


def rx_exact_crimp(curves,info):
    for slot,q in enumerate(curves):
        boundary=q[-1].copy();boundary[2]-=2.
        # Every curve is monotone Z during this local seating family.
        assert np.min(np.diff(q[:,2]))>=-1e-9
        local=np.vstack([q[q[:,2]<boundary[2]-1e-10],boundary])
        _,tr=ft_frame(0.,q[-1]);target=pw_obstacle('own_bare_contact','moving',ft_box.transform(tr))
        hit=fc_wire_check(local,info[slot]['curve_error_bound_mm'],np.zeros(len(local)),target,0.)
        if hit:return dict(status='BLOCKED',kind='exact_own_crimp_boundary',slot=slot,detail=hit)
    return dict(status='PASS',own_crimp_exclusion_mm=2.,boundary_points_inserted=True)


rx_rows=[];rx_saved={}
for offset in [float(x) for x in np.linspace(1.5,0.,21)]:
    outcome,curves,info=rs_check(offset)
    crimp=rx_exact_crimp(curves,info)
    if outcome['status']=='PASS' and crimp['status']!='PASS':outcome=crimp
    rx_rows.append(dict(offset_y_mm=offset,temporary_root_raise_mm=rs_height(offset),
        result=outcome,exact_crimp_check=crimp,curves=info))
    if any(abs(offset-x)<1e-8 for x in [0.,.75,1.5]):
        for slot,p in enumerate(curves):rx_saved[f'offset{offset:g}_slot{slot}']=p
    print('ALIGNED_ROOT_POSITION',offset,outcome['status'],outcome.get('kind'),outcome.get('slot'),outcome.get('detail'),flush=True)
np.savez_compressed(RX_OUT/'curves.npz',**rx_saved)
status='PASS' if all(r['result']['status']=='PASS' for r in rx_rows) else 'BLOCKED'
report=dict(status=status,scope='Twenty-one finite positions of all four complete upper leads seating laterally before fitting the root tie',
    source_main_sha256=source_hash,script_sha256=sha(RX_SCRIPT),helper_sha256=sha(RX_HELPER),
    source_previous_candidate_sha256=sha(RS_OUT/'finite_screen.json'),
    source_fan_pool_sha256=sha(rs_pool_file),source_forming_sha256=sha(TC_OUT/'negative_complete/screen.json'),
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    ordinary_wire_margin_mm=.3,functional_root_bed_margin_mm=0.,bed_partition_padding_mm=rx_partition_pad,
    bed_split_difference_mm3=rx_diff,bed_split_scope='Exact Boolean partition of unchanged source solid; padding covers float32 bed-plane roundoff',
    root_frontward_offset_range_mm=[1.5,0.],wire_OD_mm=OD,required_radius_mm=rs_need,
    rows=rx_rows,curves_sha256=sha(RX_OUT/'curves.npz'),
    constant_length_method='Keep the entire upper X transition aligned; compensate bounded fan arclength change only in the existing 7-mm terminal straight',
    continuous_motion='NOT_TESTED',terminal_bypass_to_start='NOT_TESTED',tie_threading_and_tightening='NOT_TESTED',
    actual_contact_cad='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-rx_started)
(RX_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ALIGNED_ROOT_DONE',status,len(rx_rows),round(time.time()-rx_started,2),flush=True)
