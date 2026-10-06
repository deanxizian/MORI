"""Strain relief on the unchanged straight departure close to CAM J11.

The analytic loop/tail seam is not a physical joint: use a real anchor near
the connector, while the remaining length stays a prescribed flexible path.
This screens nominal solids only, with no production or adoption claim.
"""
from pathlib import Path
CA_SCRIPT=Path(__file__).resolve();CA_ROOT=CA_SCRIPT.parent
CA_HELPER=CA_ROOT/'screen_CAM_pitch_anchor_warp.py';__file__=str(CA_HELPER)
exec(compile(CA_HELPER.read_text().split('\npw_rows=[];',1)[0],str(CA_HELPER),'exec'),globals())
__file__=str(CA_SCRIPT);CA_OUT=CA_ROOT/'cam_pitch_anchor/connector_anchor';CA_OUT.mkdir(exist_ok=True)
ca_band=pw_readsolid(CA_ROOT/'cam_tie_install/oriented_band.npz')
ca_head=pw_readsolid(CA_ROOT/'cam_tie_install/oriented_head.npz')
ca_xs=slots[:,0];ca_y=float(slots[0,1]);ca_rows=[]
ca_cradle=next(r for r in ob if r[0]=='Pitch_Cradle')
for ca_z in [211.5,211.8,212.]:
    ca_transform=np.array([[-1,0,0,float(ca_xs.mean()+xx.mean())],[0,1,0,ca_y+1.5],[0,0,1,ca_z-232.]])
    ca_bt=ca_band.transform(ca_transform);ca_ht=ca_head.transform(ca_transform)
    ca_bed=box([float(ca_xs.min()-1.2),ca_y-3.,ca_z-1.7],[float(ca_xs.max()+1.2),ca_y-.25,ca_z+1.7])
    ca_cut=manifold.Manifold.batch_boolean([manifold.Manifold.cylinder(4.4,.35,circular_segments=64).translate([float(x),ca_y,ca_z-2.2]) for x in ca_xs],manifold.OpType.Add)
    ca_bed=ca_bed-ca_cut
    ca_root_probe=[float(ca_xs.mean()),ca_y-3.,ca_z+1.7]
    pt,no,face,dist=ca_cradle[5].find_nearest(Vector(ca_root_probe))
    ca_row={'grip_centre_z_mm':ca_z,'bed_source':pw_support_source(ca_bed),'tie_source':pw_support_source(ca_bt+ca_ht),
       'nearest_cradle_mm':list(pt),'nearest_distance_mm':float(dist),'surface_normal':list(no),
       'band_volume_mm3':float(ca_bt.volume()),'band_components':len(ca_bt.decompose()),
       'bed_tie_intersection_mm3':float(((ca_bt+ca_ht)^ca_bed).volume())}
    ca_row['status']='PASS' if ca_row['bed_source']['status']==ca_row['tie_source']['status']=='PASS' and ca_row['bed_tie_intersection_mm3']<1e-5 else 'BLOCKED'
    for n,m in [('bed',ca_bed),('band',ca_bt),('head',ca_ht)]:cache(CA_OUT/f'z{ca_z}_{n}.npz',m)
    ca_rows.append(ca_row);print('CONNECTOR_ANCHOR',ca_row,flush=True)
ca_report={'status':'PASS' if any(r['status']=='PASS' for r in ca_rows) else 'BLOCKED',
 'scope':'Nominal connector-adjacent straight clamp and tie versus source solids; root, other wires and assembly pending',
 'source_main_sha256':source_hash,'script_sha256':sha(CA_SCRIPT),'helper_sha256':sha(CA_HELPER),'rows':ca_rows,
 'preserved_curve_definition':'All accepted source curves unchanged; source first5mm remains connector straight; downstream path only a prescribed flexible shape',
 'main_applied':False,'whole_harness':'BLOCKED','wire_fit':'NOT_TESTED','attachment':'NOT_TESTED','physical_grip':'NOT_TESTED'}
(CA_OUT/'screen.json').write_text(json.dumps(ca_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CONNECTOR_ANCHOR_DONE',ca_report['status'],flush=True)
