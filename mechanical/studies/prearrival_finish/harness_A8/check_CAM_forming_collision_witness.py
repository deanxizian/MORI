"""Find a solid interior witness for the rejected direct forming path."""
from pathlib import Path
CW_SCRIPT=Path(__file__).resolve();CW_ROOT=CW_SCRIPT.parent
CW_HELPER=CW_ROOT/'screen_CAM_wire_forming.py';__file__=str(CW_HELPER)
exec(compile(CW_HELPER.read_text().split('\nfm_reference,_,_=',1)[0],str(CW_HELPER),'exec'),globals())
__file__=str(CW_SCRIPT)
cw_paths=np.load(FM_OUT/'curves.npz');cw_p=cw_paths['f0.825_slot0']
cw_target=next(r for r in fm_targets if r[0]=='Yaw_Reaction_Link')
name,_,solid,lo,hi,tree=cw_target;cw_inside=None
for i in np.flatnonzero(np.all(cw_p>lo+.02,axis=1)&np.all(cw_p<hi-.02,axis=1)):
    ball=manifold.Manifold.sphere(.01,16).translate(cw_p[i].tolist())
    fraction=float((solid^ball).volume()/ball.volume())
    if fraction>.99:
        cw_inside={'point_index':int(i),'center_mm':cw_p[i].tolist(),'sphere_radius_mm':.01,
                   'sphere_inside_fraction':fraction,'distance_to_surface_mm':float(tree.find_nearest(Vector(cw_p[i]))[3])}
        break
cw_report={'status':'PASS' if cw_inside else 'NOT_TESTED','scope':'Witness audit: PASS confirms collision of rejected direct path, not an accepted assembly',
 'rejected_path_status':'FAIL' if cw_inside else 'BLOCKED','fraction':.825,'slot':0,'object':name,
 'inside_witness':cw_inside,'source_main_sha256':source_hash,'script_sha256':sha(CW_SCRIPT),'helper_sha256':sha(CW_HELPER),
 'source_curves_sha256':sha(FM_OUT/'curves.npz'),'main_applied':False,'whole_harness':'BLOCKED'}
(FM_OUT/'collision_witness.json').write_text(json.dumps(cw_report,ensure_ascii=False,indent=2)+'\n')
print('FORMING_COLLISION_WITNESS',cw_report,flush=True)
