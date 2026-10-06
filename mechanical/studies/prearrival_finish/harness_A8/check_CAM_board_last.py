"""Independent assembly study: seat cradle, then mate and install CAM.

Only the CAM board and its cable housing move. A prescribed head loop narrows
as the plug is raised; no additional body-side wire reserve or wire stretch
is assumed. This is a nominal geometric study, not assembly qualification.
"""
from pathlib import Path
BL_SCRIPT=Path(__file__).resolve();BL_ROOT=BL_SCRIPT.parent
BL_HELPER=BL_ROOT/'check_CAM_wired_cradle_insertion.py';__file__=str(BL_HELPER)
exec(compile(BL_HELPER.read_text().split('\nwi_rows=[];',1)[0],str(BL_HELPER),'exec'),globals())
__file__=str(BL_SCRIPT)
BL_OUT=BL_ROOT/'cam_board_last';BL_OUT.mkdir(exist_ok=True)
bl_board={n:m for n,m in wi_moving.items() if n in {'CAM_Mainboard','CAM_without_own_UART','CAM_UART_4P'} or n.startswith('Onboard_MIC_')}
bl_deferred={n:m for n,m in wi_moving.items() if n.startswith('CAM_Mount_Screw_')}
bl_fixture={n:m for n,m in (wi_fixed|wi_moving).items() if n not in bl_board and n not in bl_deferred and n!='CAM_catalogue_housing'}
bl_plug=wi_moving['CAM_catalogue_housing']
bl_targets=[pw_obstacle(n,'board' if n in bl_board else 'plug' if n=='CAM_catalogue_housing' else 'fixed',m)
    for n,m in (bl_fixture|bl_board|{'CAM_catalogue_housing':bl_plug}).items()]
bl_height0=wi_core(0.)[1]['height_mm']
bl_reference_tail_length=sum(np.linalg.norm(np.diff(PW_OLD_TAILS[0],axis=0),axis=1))

def bl_curves(h,dy):
    shrink=(h-dy)/(1.+math.pi/2.)
    end_y=float(wi_b[1]-shrink)
    rb=7.5;rt=wi_rt-shrink/2.;height=bl_height0
    assert rt>=REQUIRED_R
    col=end_y+.5+rb;zt=wi_zero_turn;x=float(xx[0])
    a=np.array([x,-1.5,230.]);top=a+[0.,0.,height]
    th=np.linspace(math.pi,0.,math.ceil(math.pi*rt/.02)+1)
    upper=np.c_[np.full_like(th,x),-1.5+rt+rt*np.cos(th),230.+height+rt*np.sin(th)]
    th=np.linspace(0.,-math.pi/2.,math.ceil(math.pi*rb/2/.02)+1)
    lower=np.c_[np.full_like(th,x),col-rb+rb*np.cos(th),zt+rb*np.sin(th)]
    end=np.array([x,end_y,wi_b[2]])
    core=np.vstack([wi_line(a,top,.02)[:-1],upper[:-1],wi_line(upper[-1],lower[0],.02)[:-1],lower[:-1],wi_line(lower[-1],end,.02)])
    core_length=2.*height+math.pi*rt+230.-zt+math.pi*rb/2.+.5
    straight=5.+h;arc=math.pi*rb/2.;extension=end_y-(slots[0,1]+dy+rb)
    assert extension>0 and arc+extension>16.
    stops=sorted(set([0.,straight,straight+arc,straight+16.,straight+arc+extension]))
    s=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/.02))+1)[:-1] for a,b in zip(stops,stops[1:])]),stops[-1]]
    th=np.clip(s-straight,0.,arc)/rb;u=np.clip((s-straight)/16.,0.,1.)
    tail=np.c_[1.8875*(10*u**3-15*u**4+6*u**5),rb*(1.-np.cos(th))+np.maximum(0.,s-straight-arc),-np.minimum(s,straight)-rb*np.sin(th)]
    tails=[tail+p+[0.,dy,h] for p in slots]
    for i,t in enumerate(tails):assert np.linalg.norm(t[-1]-(core[-1]+[xx[i]-xx[0],0,0]))<1e-8
    tail_delta=h-dy-shrink
    assert abs(core_length-wi_L+tail_delta)<1e-9
    acceleration=1/rb+(10*math.sqrt(3)/3)*1.8875/16.**2
    core_error=.02**2/(8.*min(rb,rt));tail_err=acceleration*.02**2/8.
    rad_tail=1./math.sqrt(1./rb**2+((10*math.sqrt(3)/3)*1.8875/16.**2)**2)
    return core,tails,{'plug_lift_mm':h,'plug_forward_mm':dy,'loop_width_reduction_mm':shrink,
        'core_length_mm':core_length,'tail_length_change_mm':tail_delta,
        'analytical_total_length_change_mm':core_length-wi_L+tail_delta,
        'minimum_radius_bound_mm':min(rb,rt,rad_tail),'core_error_mm':core_error,'tail_error_mm':tail_err}

def bl_geometry(board_shift,plug_shift):
    poses={n:m.translate(board_shift) for n,m in bl_board.items()}
    poses['CAM_catalogue_housing']=bl_plug.translate(plug_shift)
    for n,m in poses.items():
        for key,target in bl_fixture.items():
            if not overlap_boxes(m,target,.001):continue
            v=max(0.,float((m^target).volume()))
            if v>1e-5:return {'status':'BLOCKED','object':n,'obstacle':key,'intersection_mm3':v}
    for key,m in bl_board.items():
        if key=='CAM_UART_4P':continue
        v=max(0.,float((poses['CAM_catalogue_housing']^poses[key]).volume()))
        if v>1e-5:return {'status':'BLOCKED','object':'CAM_catalogue_housing','obstacle':key,'intersection_mm3':v}
    return {'status':'PASS'}

def bl_source(p,error,kind,slot,board_shift,plug_shift):
    for name,group,m,lo,hi,tree in bl_targets:
        local=p-np.array(board_shift) if group=='board' else p-np.array(plug_shift) if group=='plug' else p
        keep=np.ones(len(p),bool)
        if kind=='core' and name in ['Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band']:
            keep&=~((abs(local[:,0]-xx[slot])<1e-5)&(abs(local[:,1]+1.5)<1e-5)&(local[:,2]<=234.3+1e-5)&(local[:,2]>=229.9-1e-5))
        if kind=='tail' and name in ['CAM_catalogue_housing','CAM_UART_4P','Pitch_Cradle','CAM_connector_tie_head','CAM_connector_tie_band']:
            keep&=~((abs(local[:,0]-slots[slot,0])<1e-5)&(abs(local[:,1]-slots[slot,1])<1e-5)&(local[:,2]>=slots[slot,2]-5.-1e-5)&(local[:,2]<=slots[slot,2]+1e-5))
        # Removing an intentional contact span can leave two disconnected
        # curves. Do not turn the gap into a fictitious long line segment.
        indices=np.flatnonzero(keep)
        spans=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1)
        for ids in spans:
            if not len(ids):continue
            hit=check_one(local[ids],error,lo,hi,m,tree)
            if hit:return {'kind':kind,'slot':slot,'obstacle':name,**hit}
    return None

def bl_case(h,dy,board_h=None,board_dy=None):
    if board_h is None:board_h=h
    if board_dy is None:board_dy=dy
    bs=[0.,board_dy,board_h];ps=[0.,dy,h]
    row={'board_shift_mm':bs,'plug_shift_mm':ps,'rigid':bl_geometry(bs,ps)}
    if row['rigid']['status']!='PASS':return row|{'status':'BLOCKED','failure':{'kind':'rigid',**row['rigid']}},{}
    core,tails,meta=bl_curves(h,dy);row['curve']=meta;failure=None;samples={};saved={};gap=math.inf
    for i in range(4):
        c=core+[xx[i]-xx[0],0.,0.];t=tails[i]
        for kind,p,e in [('core',c,meta['core_error_mm']),('tail',t,meta['tail_error_mm'])]:
            failure=bl_source(p,e,kind,i,bs,ps)
            if failure:break
        if failure:break
        joined=np.vstack([c,t[-2::-1]]);sm=fine(joined,.01);e=max(meta['core_error_mm'],meta['tail_error_mm'])
        pk=pw_pack(sm,e,i,0)
        if pk['status']!='PASS':failure={'kind':'packing','slot':i,**pk};break
        gap=min(gap,pk['minimum_fan_body_gap_bound_mm']);samples[i]=(sm,e);saved[f'slot{i}']=joined
    if not failure:
        for a,b in itertools.combinations(range(4),2):
            sa,ea=samples[a];sb,eb=samples[b];r=pair(sa,sb,ea,eb);gap=min(gap,r['gap_bound_mm'])
            if r['status']!='PASS':failure={'kind':'mutual','slots':[a,b],**r};break
    return row|{'status':'PASS' if not failure else 'BLOCKED','failure':failure,'wire_gap_bound_mm':gap if math.isfinite(gap) else None},saved

if __name__=='__main__':
    rows=[];curves={};started=time.time()
    cases=[('seating',h,0.,h,0.) for h in [0.,6.,3.,1.,2.,4.,5.]]
    cases += [('mating',h,0.,6.,0.) for h in [0.,1.,2.,3.,3.5,4.,4.5,5.,5.5]]
    for stage,h,dy,bh,by in cases:
        row,saved=bl_case(h,dy,bh,by);row['stage']=stage;rows.append(row)
        for key,p in saved.items():curves[f'{stage}_plug{h:g}_board{bh:g}_{key}']=p
        print('BOARD_LAST',stage,h,bh,row['status'],row['failure'],round(time.time()-started,2),flush=True)
    np.savez_compressed(BL_OUT/'curves.npz',**curves)
    result={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED','rows':rows,
        'scope':'CAM board installed after cradle; prescribed constant-length head wires and finite rigid/wire samples only',
        'main_source_sha256':source_hash,'script_sha256':sha(BL_SCRIPT),'helper_sha256':sha(BL_HELPER),
        'board_objects':list(bl_board),'fixed_objects':list(bl_fixture),'deferred_screws':list(bl_deferred),
        'not_yet_fitted_pitch_parts':wi_excluded,'curves_sha256':sha(BL_OUT/'curves.npz'),
        'analytical_length_rule':'s=(h-dy)/(1+pi/2); CAM straight gains h, tail loses dy+s, upper semicircle loses pi*s/2. Combined length unchanged.',
        'constant_length':'PASS_ANALYTICAL','continuous_sweep':'NOT_TESTED','plug_mating_travel_allocation_mm':6.,
        'actual_insertion_depth':'BLOCKED_PENDING_EXACT_CONNECTOR',
        'actual_mating_force':'NOT_TESTED','prior_wire_feed_and_shape_formation':'NOT_TESTED',
        'CAM_mount_screw_tools':'NOT_TESTED','tie_threading_and_tightening':'NOT_TESTED',
        'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
    (BL_OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert sha(source)==source_hash
    print('BOARD_LAST_DONE',result['status'],flush=True)
