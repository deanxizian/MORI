"""Screen sourced SH contact envelopes and an optional pre-inserted housing.

This records nominal catalogue geometry, not an exact post-crimp profile.
The main assembly and all earlier screen results are left unchanged.
"""
from pathlib import Path
FT_SCRIPT=Path(__file__).resolve();FT_ROOT=FT_SCRIPT.parent
FT_HELPER=FT_ROOT/'screen_CAM_wire_forming_raised.py';__file__=str(FT_HELPER)
exec(compile(FT_HELPER.read_text().split('\nfor amplitude in [',1)[0],str(FT_HELPER),'exec'),globals())
__file__=str(FT_SCRIPT)
FT_OUT=FM_OUT/'terminals';FT_OUT.mkdir(exist_ok=True)
ft_started=time.time();ft_dims=np.array([.8,1.35,3.9]);ft_box=manifold.Manifold.cube(ft_dims,center=True)
ft_final=fr_curve(1.,9.)[0][-1];ft_rows=[];ft_housing_rows=[];ft_poses={}


def ft_frame(fraction,rear):
    angle=2*math.pi*fraction;c=math.cos(angle);s=math.sin(angle)
    rot=np.array([[1.,0.,0.],[0.,c,s],[0.,-s,c]])
    return rot,np.column_stack([rot,rear+rot[:,2]*ft_dims[2]/2.])


def ft_source(shape):
    bounds=np.array(shape.bounding_box());nearest={'gap_mm':2.};hits=[]
    for name,group,m,lo,hi,tree in fm_targets:
        if np.any(bounds[:3]>hi+2.) or np.any(bounds[3:]<lo-2.):continue
        volume=max(0.,float((shape^m).volume()))
        if volume>1e-7:hits.append({'object':name,'intersection_mm3':volume})
        gap=float(shape.min_gap(m,2.))
        if gap<nearest['gap_mm']:nearest={'gap_mm':gap,'object':name}
    return {'status':'PASS' if not hits and nearest['gap_mm']>=.3-1e-6 else 'BLOCKED',
            'hits':hits,'nearest_within_2mm':nearest,'nominal_clearance_mm':.3}


for fraction in np.linspace(0.,1.,41):
    fraction=float(fraction);base,parameter,error,extra=fr_curve(fraction,9.)
    row={'fraction':fraction,'contacts':[]};contact_solids=[]
    for slot in range(4):
        rear=base[-1]+[xx[slot]-xx[0],0.,0.];rot,tr=ft_frame(fraction,rear)
        solid=ft_box.transform(tr);contact_solids.append(solid)
        result=ft_source(solid);row['contacts'].append({'slot':slot,**result})
        ft_poses[f'f{fraction:.3f}_slot{slot}']=tr
    row['status']='PASS' if all(r['status']=='PASS' for r in row['contacts']) else 'BLOCKED'
    row['nominal_neighbour_contact_gap_mm']=1.-ft_dims[0]
    row['neighbour_contact_nonintersection']='PASS'
    row['neighbour_contact_0_3mm_margin']='BLOCKED'
    ft_rows.append(row)
    # Same installed catalogue housing, rotated about the wire exit. This
    # separate operation would insert the loose contacts into their housing
    # above the neck BEFORE forming. Terminal insertion itself is not proven.
    rot,_=ft_frame(fraction,base[-1]);tr=np.column_stack([rot,base[-1]-rot@ft_final])
    housing=bl_plug.transform(tr);result=ft_source(housing)
    ft_housing_rows.append({'fraction':fraction,**result})
    ft_poses[f'housing_f{fraction:.3f}']=tr
    print('FORMING_CONTACTS',round(fraction,3),row['status'],'housing',result['status'],flush=True)

np.savez_compressed(FT_OUT/'poses.npz',**ft_poses)
report={'status':'PASS' if all(r['status']=='PASS' for r in ft_rows) else 'BLOCKED',
 'scope':'41-position nominal SSH-003T-P0.2-H contact-to-stage-solid screen, not complete forming approval',
 'source_main_sha256':source_hash,'script_sha256':sha(FT_SCRIPT),'helper_sha256':sha(FT_HELPER),
 'source_raised_screen_sha256':sha(FR_OUT/'screen.json'),'poses_sha256':sha(FT_OUT/'poses.npz'),
 'contact_source_url':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf',
 'contact_source_pdf_sha256':'ea3071ca5ee5a6069eba534fa39a10f34c9fb742ee42135a69ab4156bfa0f5de',
 'contact_nominal_box_mm':ft_dims.tolist(),
 'contact_shape_evidence':'ASSUMED conservative rectangular reconstruction of VENDOR_DOCUMENTED catalogue spans; actual crimped profile and tolerances unknown',
 'contact_rear_rule':'Rear box plane at wire endpoint; long axis follows final wire tangent; narrow 0.8 mm span along X',
 'contact_rows':ft_rows,'nominal_contact_contact_gap_mm':1.-ft_dims[0],
 'contact_contact_nonintersection':'PASS_ANALYTICAL','contact_contact_0_3mm_margin':'BLOCKED',
 'contact_to_wire_packing':'NOT_TESTED','continuous_contact_motion':'NOT_TESTED',
 'preinserted_housing_candidate':{'status':'PASS' if all(r['status']=='PASS' for r in ft_housing_rows) else 'BLOCKED',
    'rows':ft_housing_rows,'catalogue_housing_only':True,'terminal_to_housing_insertion':'NOT_TESTED',
    'continuous_housing_motion':'NOT_TESTED','actual_CAM_mating_connector':'BLOCKED_PENDING_IDENTIFICATION'},
 'source_solids_considered':len(fm_targets),'uninstalled_CAM_board':True,
 'untightened_tie_final_solids_omitted':sorted(fm_deferred),'uninstalled_other_pitch_parts':wi_excluded,
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-ft_started}
(FT_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_TERMINALS_DONE',report['status'],report['preinserted_housing_candidate']['status'],flush=True)
