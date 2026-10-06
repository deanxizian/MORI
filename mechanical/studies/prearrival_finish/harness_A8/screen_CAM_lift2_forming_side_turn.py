"""Try rotating the temporary free-wire bend sideways, without extra cuts.

Each curve rotates rigidly about its own unchanged vertical root; its first
4.3mm, its length and its final endpoint stay fixed. This is finite screening
only; the original in-plane velocity bound must NOT certify this new motion.
"""
from pathlib import Path
ST_SCRIPT=Path(__file__).resolve();ST_ROOT=ST_SCRIPT.parent
ST_HELPER=ST_ROOT/'screen_CAM_lift2_forming_apex.py';__file__=str(ST_HELPER)
exec(compile(ST_HELPER.read_text().split('\nap_order=',1)[0],str(ST_HELPER),'exec'),globals())
__file__=str(ST_SCRIPT)
ST_OUT=L2_OUT/'side_turn';ST_OUT.mkdir(exist_ok=True);st_started=time.time()
st_curve_original=fc_curve;st_frame_original=ft_frame;st_angle_max=0.


def st_rotation(f):
    t=np.clip((f-.55)/.4,0.,1.);angle=math.radians(st_angle_max)*math.sin(math.pi*t)**2
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]]),math.degrees(angle)


def fc_curve(f):
    p,u,e=st_curve_original(f);rot,_=st_rotation(f);pivot=np.array([xx[0],-1.5,230.])
    return (p-pivot)@rot.T+pivot,u,e


def ft_frame(f,rear):
    original,_=st_frame_original(f,rear);rot=st_rotation(f)[0]@original
    return rot,np.column_stack([rot,rear+rot[:,2]*ft_dims[2]/2.])


st_order=list(dict.fromkeys([.8,.775,.825,.75,.85,.725,.7,.875,.9,.95,1.,0.]+[float(x) for x in np.linspace(0.,1.,41)]))
st_trials=[];st_selected=None;st_saved={}
for amp,angle in [(6.,0.),(7.5,0.),(8.25,0.),(9.,-8.),(9.,8.),(9.,-16.),(9.,16.),(9.,-24.),(9.,24.)]:
    fc_amplitude=amp;st_angle_max=angle;rows=[];saved={}
    for f in st_order:
        p,u,error=fc_curve(f);hit=fc_test(f,f)
        packing,sm=ap_pack(p,error) if hit is None else ({'status':'NOT_TESTED'},[])
        row={'fraction':f,'side_angle_deg':st_rotation(f)[1],'solids_failure':hit,'wire_packing':packing,
            'status':'PASS' if hit is None and packing['status']=='PASS' else 'BLOCKED'}
        rows.append(row)
        print('SIDE_TURN_SCREEN',amp,angle,f,row['status'],hit,packing.get('checks',[None])[-1],flush=True)
        if row['status']!='PASS':break
        for slot in range(4):saved[f'f{f:.6f}_slot{slot}']=p+[xx[slot]-xx[0],0.,0.]
    good=len(rows)==len(st_order) and all(r['status']=='PASS' for r in rows)
    st_trials.append({'amplitude_mm':amp,'maximum_side_angle_deg':angle,'status':'PASS' if good else 'BLOCKED','rows':rows})
    if good:st_selected={'amplitude_mm':amp,'maximum_side_angle_deg':angle};st_saved=saved;break
if st_saved:np.savez_compressed(ST_OUT/'curves.npz',**st_saved)
report={'status':'PASS' if st_selected else 'BLOCKED','scope':'Finite temporary lateral forming path against stage solids and upstream wires',
    'source_main_sha256':source_hash,'script_sha256':sha(ST_SCRIPT),'helper_sha256':sha(ST_HELPER),
    'source_in_plane_trial_sha256':sha(AP_OUT/'screen.json'),'selected':st_selected,'trials':st_trials,'planned_fractions':st_order,
    'curves_sha256':sha(ST_OUT/'curves.npz') if st_saved else None,
    'rotation_rule':'Rotate each free curve about its own fixed vertical root; alpha=max_angle*sin(pi*clamp((f-.55)/.4,0,1))^2.',
    'wire_OD_mm':OD,'wire_and_contact_to_structure_margin_mm':.3,'constant_length':'PASS_ANALYTICAL_RIGID_ROTATION',
    'continuous_motion':'NOT_TESTED','prior_in_plane_velocity_bound_applicable':False,
    'contact_handling_margin':'BLOCKED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-st_started}
(ST_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('SIDE_TURN_REVISION_DONE',report['status'],st_selected,flush=True)
