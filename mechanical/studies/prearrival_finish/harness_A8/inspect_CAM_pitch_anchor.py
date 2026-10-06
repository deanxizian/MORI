"""Read-only nearest printed-surface survey for the CAM pitch-side anchor."""
from pathlib import Path
PA_SCRIPT=Path(__file__).resolve();PA_A8=PA_SCRIPT.parent
PA_HELPER=PA_A8/'screen_CAM_anchor_support.py';__file__=str(PA_HELPER)
exec(compile(PA_HELPER.read_text().split('\nhost=ss[',1)[0],str(PA_HELPER),'exec'),globals())
__file__=str(PA_SCRIPT)
PA_OUT=PA_A8/'cam_pitch_anchor';PA_OUT.mkdir(exist_ok=True)
tail_arrays=np.load(PA_A8/'cam_fan_in/short_tail_v2/tails.npz')
rows=[]
for label,point in [('loop_end',[-8.212500143,9.5,202.1000061]),
                    ('tail_straight',[-8.212500143,5.,202.1000061]),
                    ('connector_exit',[-10.100000143,-20.80000019,211.5])]:
    nearest=[]
    for name,group,m,lo,hi,tree in ob:
        if group!='pitch' or name not in ['Pitch_Cradle','Display_Frame','Head_Front','Head_Rear']:continue
        p,normal,idx,distance=tree.find_nearest(Vector(point))
        nearest.append({'object':name,'point_mm':list(p),'normal':list(normal),'distance_mm':distance,
                        'bounds_mm':list(m.bounding_box())})
    rows.append({'target':label,'point_mm':point,'nearest':sorted(nearest,key=lambda r:r['distance_mm'])})
report={'source_main_sha256':source_hash,'script_sha256':sha(PA_SCRIPT),'rows':rows,
        'source_tail_sha256':sha(PA_A8/'cam_fan_in/short_tail_v2/tails.npz'),
        'scope':'Nearest surfaces only, not viable load paths or anchor design','main_applied':False}
(PA_OUT/'surface_survey.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
assert sha(source)==source_hash
