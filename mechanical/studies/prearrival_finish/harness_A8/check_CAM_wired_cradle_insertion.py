"""Connect the previously separate rigid-cradle and four-wire assembly checks.

Prescribe one constant-length service-loop family while the CAM/cradle module
is lowered from the animation's 42 mm bench offset. The family is kinematic,
not a natural cable-shape or force model. No main files are changed.
"""
from pathlib import Path
WI_SCRIPT=Path(__file__).resolve();WI_ROOT=WI_SCRIPT.parent
WI_HELPER=WI_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(WI_HELPER)
exec(compile(WI_HELPER.read_text().split('\npw_rows=[];',1)[0],str(WI_HELPER),'exec'),globals())
__file__=str(WI_SCRIPT)
WI_OUT=WI_ROOT/'cam_wired_cradle';WI_OUT.mkdir(exist_ok=True)
WI_ANCHOR=WI_ROOT/'cam_pitch_anchor/connector_anchor'
wi_anchor=pw_readsolid(WI_ANCHOR/'Pitch_Cradle.npz')
wi_head=pw_readsolid(WI_ANCHOR/'z212.0_head.npz');wi_band=pw_readsolid(WI_ANCHOR/'z212.0_band.npz')
wi_moving_ids={'Pitch_Cradle','CAM_Mainboard','CAM_without_own_UART','CAM_catalogue_housing','CAM_UART_4P'}
wi_moving_ids|={n for n in ss if n.startswith(('CAM_Mount_','Onboard_MIC_','Head_Cradle_Insert_'))}
wi_moving={n:m for n,g,m,*_ in ob if n in wi_moving_ids}
wi_moving['Pitch_Cradle']=wi_anchor
wi_moving.update(CAM_connector_tie_head=wi_head,CAM_connector_tie_band=wi_band)
assert 'CAM_without_own_UART' in wi_moving, 'The full board minus its separately modeled UART must move too'
wi_fixed={n:m for n,g,m,*_ in ob if g!='pitch' and n not in wi_moving}
wi_excluded=[n for n,g,m,*_ in ob if g=='pitch' and n not in wi_moving]
wi_targets=[pw_obstacle(n,'moving' if n in wi_moving else 'fixed',m) for n,m in (wi_fixed|wi_moving).items()]
wi_xs=xx.copy();wi_L=float(chosen['exact_length_mm'])
wi_mat=np.asarray(rigidtr(0,0));wi_b=PW_OLD_TAILS[0][-1].copy()
wi_y=-1.5;wi_z=230.;wi_rb=7.5;wi_end=.5
wi_column=wi_b[1]+wi_end+wi_rb;wi_rt=(wi_column-wi_y)/2
wi_zero_turn=wi_b[2]+wi_rb

def wi_line(a,b,step=.025):
    return np.linspace(a,b,max(1,int(math.ceil(np.linalg.norm(np.asarray(b)-a)/step)))+1)

def wi_core(lift):
    zturn=wi_zero_turn+lift
    base=math.pi*wi_rt+wi_z-zturn+wi_rb*math.pi/2+wi_end
    height=(wi_L-base)/2.;span=wi_z+height-zturn
    assert height>=5.-1e-6 and span>.5
    x=float(xx[0]);a=np.array([x,wi_y,wi_z]);top=a+[0.,0.,height]
    t=np.linspace(math.pi,0,max(2,math.ceil(math.pi*wi_rt/.025)+1))
    upper=np.c_[np.full_like(t,x),wi_y+wi_rt+wi_rt*np.cos(t),wi_z+height+wi_rt*np.sin(t)]
    q=np.linspace(0.,-math.pi/2,max(2,math.ceil(math.pi*wi_rb/2/.025)+1))
    lower=np.c_[np.full_like(q,x),wi_column-wi_rb+wi_rb*np.cos(q),zturn+wi_rb*np.sin(q)]
    end=wi_b+[0.,0.,lift];end[0]=x
    p=np.vstack([wi_line(a,top)[:-1],upper[:-1],wi_line(upper[-1],lower[0])[:-1],lower[:-1],wi_line(lower[-1],end)])
    err=max(wi_rt,wi_rb)*(1-math.cos(.025/(2*min(wi_rt,wi_rb))))
    return p,{'lift_mm':lift,'height_mm':height,'column_span_mm':span,'exact_core_length_mm':base+2*height,'curve_error_mm':err}

def wi_geometry(lift):
    rows=[]
    for n,m in wi_moving.items():
        placed=m.translate([0.,0.,lift])
        for key,target in wi_fixed.items():
            if not overlap_boxes(placed,target,.001):continue
            vol=max(0.,float((placed^target).volume()))
            if vol>1e-5:rows.append({'moving':n,'obstacle':key,'intersection_mm3':vol})
    return {'status':'BLOCKED' if rows else 'PASS','hits':rows}

def wi_source(p,error,lift,kind,slot):
    for name,group,m,lo,hi,tree in wi_targets:
        local=p-[0.,0.,lift] if group=='moving' else p
        keep=np.ones(len(p),bool)
        if kind=='core' and name in ['Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band']:
            grip=(abs(local[:,0]-xx[slot])<1e-5)&(abs(local[:,1]+1.5)<1e-5)&(local[:,2]<=234.3+1e-5)&(local[:,2]>=229.9-1e-5)
            keep&=~grip
        if kind=='tail' and name in ['CAM_catalogue_housing','CAM_UART_4P','Pitch_Cradle','CAM_connector_tie_head','CAM_connector_tie_band']:
            grip=(abs(local[:,0]-slots[slot,0])<1e-5)&(abs(local[:,1]-slots[slot,1])<1e-5)&(local[:,2]>=slots[slot,2]-5.-1e-5)&(local[:,2]<=slots[slot,2]+1e-5)
            keep&=~grip
        hit=check_one(local[keep],error,lo,hi,m,tree)
        if hit:return {'kind':kind,'slot':slot,'obstacle':name,**hit}
    return None

wi_rows=[];wi_curves={};wi_started=time.time()
wi_order=[float(x) for x in range(0,43,3)]
for wi_lift in wi_order:
    wi_row={'lift_mm':wi_lift,'geometry':wi_geometry(wi_lift)}
    if wi_row['geometry']['status']!='PASS':
        wi_row['status']='BLOCKED';wi_rows.append(wi_row);print('WIRED_CRADLE',wi_row,flush=True);continue
    wi_core0,wi_meta=wi_core(wi_lift);wi_failure=None;wi_samples={};wi_min=math.inf
    for wi_slot in range(4):
        wi_c=wi_core0+[xx[wi_slot]-xx[0],0.,0.]
        wi_t=PW_OLD_TAILS[wi_slot]+[0.,0.,wi_lift]
        assert np.linalg.norm(wi_c[-1]-wi_t[-1])<1e-7
        for kind,p,err in [('core',wi_c,wi_meta['curve_error_mm']),('tail',wi_t,tail_error)]:
            wi_failure=wi_source(p,err,wi_lift,kind,wi_slot)
            if wi_failure:break
        if wi_failure:break
        # The first 0.025 mm resampling left a conservative lower bound of
        # 0.29087 mm at the unchanged packed tail. Refine the numerical bound,
        # keeping the required 0.3 mm gap and the actual curves unchanged.
        wi_p=np.vstack([wi_c,wi_t[-2::-1]]);wi_sample=fine(wi_p,.01);wi_err=max(wi_meta['curve_error_mm'],tail_error)
        wi_pack=pw_pack(wi_sample,wi_err,wi_slot,0)
        if wi_pack['status']!='PASS':wi_failure={'kind':'packing','slot':wi_slot,**wi_pack};break
        wi_min=min(wi_min,wi_pack['minimum_fan_body_gap_bound_mm']);wi_samples[wi_slot]=(wi_sample,wi_err)
        wi_curves[f'lift{wi_lift}_slot{wi_slot}']=wi_p
    if not wi_failure:
        for a,b in itertools.combinations(range(4),2):
            aa,ea=wi_samples[a];bb,eb=wi_samples[b];check=pair(aa,bb,ea,eb);wi_min=min(wi_min,check['gap_bound_mm'])
            if check['status']!='PASS':wi_failure={'kind':'mutual_wire','slots':[a,b],**check};break
    wi_row.update(status='BLOCKED' if wi_failure else 'PASS',curves=wi_meta,failure=wi_failure,minimum_pack_gap_mm=wi_min if math.isfinite(wi_min) else None)
    wi_rows.append(wi_row);print('WIRED_CRADLE',wi_row,round(time.time()-wi_started,1),flush=True)
np.savez_compressed(WI_OUT/'curves.npz',**wi_curves)
wi_result={'status':'PASS' if len(wi_rows)==len(wi_order) and all(r['status']=='PASS' for r in wi_rows) else 'BLOCKED',
    'scope':'Candidate 42 mm upright CAM/cradle insertion with four prescribed constant-length core/tail wires; finite rigid/wire placements',
    'script_sha256':sha(WI_SCRIPT),'helper_sha256':sha(WI_HELPER),'source_main_sha256':source_hash,
    'source_anchor_sha256':sha(WI_ANCHOR/'Pitch_Cradle.npz'),'curves_sha256':sha(WI_OUT/'curves.npz'),
    'moving_ids':list(wi_moving),'fixture_ids':list(wi_fixed),'not_yet_installed_pitch_parts':wi_excluded,
    'rows':wi_rows,'planned_travel_mm':42.,'sample_step_mm':3.,'core_length_mm':wi_L,
    'wire_resampling_step_mm':.01,'required_wire_gap_mm':.3,
    'analytical_curve_rule':'With rigid CAM-side tail lifted by h, upper-loop straight height increases by h/2 and vertical column decreases by h/2; radius and total curve length stay constant.',
    'continuous_motion':'NOT_TESTED','formation_to_this_curve':'NOT_TESTED','tool_tie_initial_assembly':'NOT_TESTED',
    'full_wire_loose_storage':'NOT_TESTED','actual_head_transmission':'BLOCKED_PENDING_VENDOR',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-wi_started}
(WI_OUT/'screen.json').write_text(json.dumps(wi_result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('WIRED_CRADLE_DONE',wi_result['status'],len(wi_rows),flush=True)
