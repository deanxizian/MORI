"""Nominal CAM routed-length datums, deliberately not supplier cut lengths.

Read the current stored curves and source arithmetic. Keep the four geometry
slots separate from the unconfirmed CAM mating-cavity/pin view.
"""
from pathlib import Path
import csv,hashlib,json,math
import numpy as np

SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent;ROOT=A8.parents[3]
OUT=A8/'cam_connector_install';OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bodymeta=read(A8/'body_prefix_v2/body_to_yaw_motion.json')
lower=read(A8/'cam_pitch_port/lower_staging/coexistence_screen.json')
fanmeta=read(A8/'cam_fan_in/four_bend_transition/pool.json')
fanmath=read(A8/'cam_fan_in/four_bend_transition/math_bounds.json')
pack=read(A8/'cam_fan_in/four_bend_transition/packing.json')
loops=read(A8/'cam_fan_in/short_tail_v2/screen.json')
joins=read(A8/'cam_fan_in/joins.json')
curves=np.load(A8/'cam_pitch_port/lower_staging/body_partial_curves.npz')
old=np.load(A8/'body_prefix_v2/body_to_yaw_curves.npz')
fans=np.load(A8/'cam_fan_in/four_bend_transition/curves.npz')
cores=np.load(A8/'cam_fan_in/short_tail_v2/curves.npz')
tails=np.load(A8/'cam_fan_in/short_tail_v2/tails.npz')
ports=read(A8/'h06_ports.json')
assert all(r['status']=='PASS' for r in [bodymeta,lower,fanmeta,fanmath,pack,loops,joins])
assert lower['source_original_body_curves_sha256']==sha(A8/'body_prefix_v2/body_to_yaw_curves.npz')
assert lower['candidate_body_curves_sha256']==sha(A8/'cam_pitch_port/lower_staging/body_partial_curves.npz')
assert pack['source_curves_sha256']==sha(A8/'cam_fan_in/four_bend_transition/curves.npz')
assert ports['body']['source']['sha256']==sha(ROOT/ports['body']['source']['file'])
choice=pack['assignments'][0];core_length=loops['selected'][0]['exact_length_mm']
tail_interval=[joins['tail_length_lower_mm'],joins['tail_length_upper_mm']]
tail_length=sum(tail_interval)/2
polylen=lambda p:float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
def at_distance(p,s):
    lens=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.r_[0.,np.cumsum(lens)]
    i=min(len(lens)-1,int(np.searchsorted(cum,s,side='right')-1))
    assert i>=0 and cum[-1]>=s
    return p[i]+(p[i+1]-p[i])*(s-cum[i])/lens[i]
def pose(p,yaw,pitch=0):
    a,b=np.deg2rad([yaw,pitch]);ca,sa,cb,sb=np.cos(a),np.sin(a),np.cos(b),np.sin(b)
    R=np.array([[ca,-sa,0],[sa,ca,0],[0,0,1.]])@np.array([[1.,0,0],[0,cb,-sb],[0,sb,cb]])
    centre=np.array([0.,0.,222.]);return (p-centre)@R.T+centre

rows=[];pose_rows=[];csv_vertices=[]
for slot in range(4):
    pin=slot+1;label=f'H06-G{pin}'
    br=[r for r in bodymeta['rows'] if r['pin']==pin]
    assert max(r['analytic_partial_length_mm'] for r in br)-min(r['analytic_partial_length_mm'] for r in br)<1e-9
    # Reconfirm that the changed source is only the final straight shortened
    # by 13 mm; do not reuse an old length on a moved or warped curve.
    for r in lower['subset_proof']:
        if not r['array'].startswith(f'pin{pin}_'):continue
        a,b=old[r['array']],curves[r['array']];n=r['unchanged_prefix_points']
        assert np.array_equal(a[:n],b[:n])
        assert abs(polylen(a)-polylen(b)-13.)<1e-8
    body_length=br[0]['analytic_partial_length_mm']-13.
    fm=next(r for r in fanmath['rows'] if r['pin']==pin and r['candidate']==choice[slot])
    fan=fanmeta['rows'][slot]['candidates'][choice[slot]]
    fan_length=fan['length_mm'];total=body_length+fan_length+core_length+tail_length
    body0=curves[f'pin{pin}_yaw0'];f=fans[f'pin{pin}_candidate{choice[slot]}'];c=cores[f'candidate0_slot{slot}_pitch0'];t=tails[f'slot{slot}']
    assert np.linalg.norm(body0[0]-ports['body']['pins'][str(pin)])<1e-6
    yc=at_distance(c,2.);camera_to_grip=float(t[0,2]-212.)
    cc=at_distance(t,camera_to_grip)
    assert np.linalg.norm(yc-np.array([c[0,0],-1.5,232.]))<1e-8
    assert np.linalg.norm(cc-np.array([t[0,0],t[0,1],212.]))<1e-8
    marks=[('body_exit',0.,body0[0],'body','allocated housing wire-exit face'),
           ('yaw_upper_staging',body_length,body0[-1],'yaw','mathematical seam, not a physical clamp'),
           ('yaw_clamp_centre',body_length+fan_length+2.,yc,'yaw','candidate tie centre'),
           ('CAM_clamp_centre',total-camera_to_grip,cc,'pitch','candidate tie centre'),
           ('CAM_exit',total,t[0],'pitch','photo/catalogue allocated wire exit')]
    row={'geometry_slot':label,'body_pin_reference':f'Motion J5.{pin}',
         'CAM_pin_assignment':'BLOCKED; geometry slot does not establish the real mating cavity',
         'body_prefix_model_mm':body_length,'yaw_transition_model_mm':fan_length,
         'pitch_core_model_mm':core_length,'CAM_tail_model_mm':tail_length,
         'total_routed_model_mm':total,
         'fan_tail_numerical_interval_contribution_mm':[fm['length_lower_mm']+tail_interval[0],fm['length_upper_mm']+tail_interval[1]],
         'numeric_interval_note':'Curve-integration precision only, not product or manufacturing tolerance',
         'between_candidate_clamp_centres_model_mm':core_length-2.+tail_length-camera_to_grip,
         'CAM_exit_to_clamp_centre_model_mm':camera_to_grip,
         'datums':[{'name':n,'distance_from_body_exit_model_mm':s,'zero_pose_xyz_mm':p.tolist(),'rigid_group':g,'basis':basis} for n,s,p,g,basis in marks],
         'cut_length_mm':None,'cut_length_status':'BLOCKED',
         'cut_length_equation':'L_cut = L_routed + signed_body_terminal_end_correction + signed_CAM_terminal_end_correction; all corrections and production tolerance unresolved'}
    rows.append(row)
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            pieces=[curves[f'pin{pin}_yaw{yaw}'],pose(f,yaw),pose(cores[f'candidate0_slot{slot}_pitch{pitch}'],yaw),pose(t[::-1],yaw,pitch)]
            endpoint_errors=[float(np.linalg.norm(a[-1]-b[0])) for a,b in zip(pieces,pieces[1:])]
            assert max(endpoint_errors)<3e-5
            model_poly_length=sum(polylen(p) for p in pieces)
            assert abs(model_poly_length-total)<.003
            pose_rows.append({'geometry_slot':label,'yaw_deg':yaw,'pitch_deg':pitch,'polyline_length_mm':model_poly_length,'difference_from_source_model_mm':model_poly_length-total,'maximum_seam_error_mm':max(endpoint_errors)})
    pieces=[body0,f,c,t[::-1]];path=np.vstack([p[:-1] for p in pieces[:-1]]+[pieces[-1]])
    along=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    for i,(s,p) in enumerate(zip(along,path)):csv_vertices.append([label,i,round(float(s),6),*[round(float(x),6) for x in p]])
with (OUT/'route_reference_only.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['geometry_slot','vertex','polyline_s_mm_NOT_CUT_LENGTH','x_mm','y_mm','z_mm']);w.writerows(csv_vertices)
with (OUT/'length_datums_REFERENCE_ONLY.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['geometry_slot','body_pin_reference','routed_model_mm_NOT_CUT_LENGTH','body_to_yaw_clamp_mm','between_clamps_mm','CAM_clamp_to_exit_mm','cut_length_mm','release'])
    for r in rows:w.writerow([r['geometry_slot'],r['body_pin_reference'],f"{r['total_routed_model_mm']:.3f}",f"{r['datums'][2]['distance_from_body_exit_model_mm']:.3f}",f"{r['between_candidate_clamp_centres_model_mm']:.3f}",f"{r['CAM_exit_to_clamp_centre_model_mm']:.3f}",'','BLOCKED'])
sources=[A8/x for x in ['body_prefix_v2/body_to_yaw_motion.json','body_prefix_v2/body_to_yaw_curves.npz','cam_pitch_port/lower_staging/body_partial_curves.npz','cam_pitch_port/lower_staging/coexistence_screen.json','cam_fan_in/four_bend_transition/pool.json','cam_fan_in/four_bend_transition/packing.json','cam_fan_in/four_bend_transition/math_bounds.json','cam_fan_in/four_bend_transition/curves.npz','cam_fan_in/short_tail_v2/screen.json','cam_fan_in/short_tail_v2/curves.npz','cam_fan_in/short_tail_v2/tails.npz','cam_fan_in/joins.json','h06_ports.json']]
report={'status':'PASS','scope':'Source-backed nominal routed length and anchor datums, not supplier manufacture or installed-flex evidence',
    'source_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),'script_sha256':sha(SCRIPT),'sources':{str(p.relative_to(ROOT)):sha(p) for p in sources},
    'units':'mm','origin':'MORI frame, +X right +Y forward +Z up; head mechanical zero',
    'rows':rows,'pose_rows':pose_rows,'pose_wire_instances':len(pose_rows),
    'maximum_polyline_source_length_difference_mm':max(abs(r['difference_from_source_model_mm']) for r in pose_rows),
    'manufacturing_tolerances':'NOT_TESTED','cut_lengths_released':False,'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
    'outputs':{p.name:sha(p) for p in [OUT/'route_reference_only.csv',OUT/'length_datums_REFERENCE_ONLY.csv']}}
(OUT/'route_datums.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CAM_ROUTE_DATUMS',len(pose_rows),[(r['geometry_slot'],round(r['total_routed_model_mm'],3)) for r in rows],flush=True)
