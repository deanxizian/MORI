"""Keep all accepted wires, screen alternative straight-segment clamp locations."""
from pathlib import Path
CP_SCRIPT=Path(__file__).resolve();CP_ROOT=CP_SCRIPT.parent
CP_HELPER=CP_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(CP_HELPER)
exec(compile(CP_HELPER.read_text().split('\npw_rows=[];',1)[0],str(CP_HELPER),'exec'),globals())
__file__=str(CP_SCRIPT);CP_OUT=CP_ROOT/'cam_pitch_anchor/clamp_positions';CP_OUT.mkdir(exist_ok=True)
cp_original_band=pw_readsolid(CP_ROOT/'cam_tie_install/oriented_band.npz')
cp_original_head=pw_readsolid(CP_ROOT/'cam_tie_install/oriented_head.npz')
cp_xcenter=float(xx.mean());cp_z=float(PW_OLD_TAILS[0][-1,2])
cp_band_rows=[]
for cp_y in [-7.,-4.,-1.,2.,5.,8.]:
    # Original tie plane XY at Z232; target XZ at Y=cp_y.
    # Reflect X to place the head toward the left, away from the yaw servo.
    cp_transform=np.array([[-1,0,0,2*cp_xcenter],[0,0,1,cp_y-232.],[0,-1,0,cp_z-1.5]])
    cp_band=cp_original_band.transform(cp_transform);cp_head=cp_original_head.transform(cp_transform)
    cp_lo=float(xx.min()-1.2);cp_hi=float(xx.max()+1.2)
    cp_bed=box([cp_lo,cp_y-1.7,cp_z+.25],[cp_hi,cp_y+1.7,cp_z+3.])
    cp_grooves=manifold.Manifold.batch_boolean([manifold.Manifold.cylinder(4.4,.35,circular_segments=64).rotate([90,0,0]).translate([float(x),cp_y+2.2,cp_z]) for x in xx],manifold.OpType.Add)
    cp_bed=cp_bed-cp_grooves
    cp_row={'grip_y_mm':cp_y,'bed_source':pw_support_source(cp_bed),'tie_source':pw_support_source(cp_band+cp_head),
            'bed_volume_mm3':float(cp_bed.volume()),'band_volume_mm3':float(cp_band.volume()),'band_components':len(cp_band.decompose()),
            'bed_tie_intersection_mm3':float(((cp_band+cp_head)^cp_bed).volume())}
    cp_row['status']='PASS' if cp_row['bed_source']['status']==cp_row['tie_source']['status']=='PASS' and cp_row['bed_tie_intersection_mm3']<1e-6 else 'BLOCKED'
    cp_band_rows.append(cp_row)
    for n,m in [('bed',cp_bed),('band',cp_band),('head',cp_head)]:cache(CP_OUT/f'y{cp_y}_{n}.npz',m)
    print('CLAMP_POSITION',cp_row,flush=True)
cp_report={'status':'PASS' if any(r['status']=='PASS' for r in cp_band_rows) else 'BLOCKED',
 'scope':'Alternative nominal bed/tie positions versus source solids only; no connection to frame or wire check yet',
 'source_main_sha256':source_hash,'script_sha256':sha(CP_SCRIPT),'helper_sha256':sha(CP_HELPER),'rows':cp_band_rows,
 'main_applied':False,'whole_harness':'BLOCKED','wire_fit':'NOT_TESTED','attachment':'NOT_TESTED','physical_grip':'NOT_TESTED'}
(CP_OUT/'screen.json').write_text(json.dumps(cp_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CLAMP_POSITIONS_DONE',cp_report['status'],flush=True)
