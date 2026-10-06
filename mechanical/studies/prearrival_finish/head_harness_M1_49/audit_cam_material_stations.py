"""Distinguish material-fixed endpoint restraints from a sliding intermediate guide."""
from pathlib import Path
import json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes';OUT=BASE/'cam_restraints'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
F=BASE/'cam_side_fans';J=F/'c6_join';N=BASE/'neck_side_tail_gentle'
fr=read(F/'fan_screen.json');jr=read(J/'join_review.json');nr=read(N/'join_screen.json')
for r in [fr,jr,nr]:
    assert r['status']=='PASS'
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(F/'fan_candidates.npz')==fr['fan_curve_sha256'] and sha(J/'candidate_curves.npz')==jr['curve_sha256']
assert sha(N/'neck_curves.npz')==nr['neck_curve_sha256']
n=np.load(N/'neck_curves.npz');curves=np.load(J/'candidate_curves.npz');mapping={1:9,2:8,3:7,4:10};rows=[]
for spec in fr['selected']:
    pin=spec['pin'];slot=mapping[pin];positions=[]
    for yaw in range(-60,61,10):
        neck=n[f'wire{slot}_y{yaw}'];Ln=float(np.linalg.norm(np.diff(neck,axis=0),axis=1).sum())
        for pitch in range(-20,26,5):
            p=curves[f'CAM_{pin}_y{yaw}_p{pitch}'];L=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
            # Differences suffice; the invariant body-prefix length adds the same constant.
            positions.append(dict(yaw_deg=yaw,pitch_deg=pitch,total_length_mm=L,
                                  neck_start_to_yaw_guide_mm=Ln+spec['exact_length_mm'],
                                  body_start_to_CAM_clamp_mm=L-2.5,CAM_clamp_to_port_mm=2.5))
    span=lambda key:max(x[key] for x in positions)-min(x[key] for x in positions)
    rows.append(dict(pin=pin,body_and_CAM_restraint_material_consistency='PASS' if span('body_start_to_CAM_clamp_mm')<.01 else 'BLOCKED',
                     intermediate_fixed_clamp='BLOCKED' if span('neck_start_to_yaw_guide_mm')>=.01 else 'PASS',
                     required_intermediate_slide_stroke_mm=span('neck_start_to_yaw_guide_mm'),
                     total_length_variation_mm=span('total_length_mm'),CAM_clamp_material_position_variation_mm=span('body_start_to_CAM_clamp_mm'),positions=positions))
ctx.assert_unchanged()
inputs=[F/'fan_screen.json',F/'fan_candidates.npz',J/'join_review.json',J/'candidate_curves.npz',N/'join_screen.json',N/'neck_curves.npz']
r=dict(status='PASS',scope='Completed material-coordinate audit; PASS is not clamp or guide release.',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    intermediate_fixed_clamp='BLOCKED',required_design='Body and CAM end restraints; intermediate yaw guide must permit the recorded axial sliding or routing must be redesigned for separately constant segments.',
    guide_clearance_and_wear='NOT_TESTED',body_restraint='NOT_TESTED',CAM_restraint='NOT_TESTED',main_changed=False,C6_main_applied=False,full_harness='BLOCKED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'material_stations.json').write_text(json.dumps(r,indent=2)+'\n');print('MATERIAL_STATIONS',[(x['pin'],x['required_intermediate_slide_stroke_mm']) for x in rows],flush=True)
