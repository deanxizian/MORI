"""Current-source fan-in options from adopted neck datums to CAM loop anchors."""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from upper_curve_geometry import make
ctx=Context();start_time=time.time()
read=lambda name:json.loads((HERE/name).read_text())
current=read('current_source_verification.json');upper=read('cam_upper_screen.json')
assert current['status']==upper['status']=='PASS'
for report in [current,upper]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
body=read('body_layered_four_screen.json')
neck=np.load(HERE/'body_layered_four_candidates.npz');loops=np.load(HERE/'cam_upper_candidates.npz')
assert sha(HERE/'body_layered_four_candidates.npz')==body['curve_sha256']
assert sha(HERE/'cam_upper_candidates.npz')==upper['curve_sha256']
original=ctx.targets
groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
results=[];arrays={};checks=0
alternative=np.load(HERE/'front_neck_candidates.npz')
front=read('front_route_screen.json')
assert not front['neck_hits'] and all(r['status']=='PASS' for r in front['neck_pair_checks'])
assert sha(HERE/'front_neck_candidates.npz')==front['curve_files']['front_neck_candidates.npz']
for pin in [1]:
    a=alternative['wire10_y0'][-1];anchor=loops[f'slot{pin-1}_pitch0'][0]
    accepted=[];failed=[]
    options=itertools.product([None,[-12.7,-8.],[-14.,-8.],[-15.,-4.],[-13.,2.],[-12.,10.]],
        [7.,8.,9.,10.,12.,14.],[0.,2.,4.],[0.,3.,6.,9.,12.,15.,16.5,18.,19.5])
    for waypoint,radius,trim,lead in options:
        b=anchor+[0.,0.,trim]
        q=make(a,b,radius,lead,waypoint)
        if q is None:continue
        p,L,err=q
        ctx.targets=original;hit=ctx.clear(p,chord_error=err,radius=.6604/2);checks+=1
        case=dict(pin=pin,radius_mm=radius,lead_mm=lead,anchor_trim_mm=trim,waypoint_xy_mm=waypoint)
        if hit:failed.append(dict(case,**hit));continue
        for group,t in targets.items():
            ctx.targets=t
            for yaw in (range(-60,61,10) if group=='body' else [0]):
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                    pts=p@tr[:3,:3].T+tr[:3,3]
                    hit=ctx.clear(pts,chord_error=err,radius=.6604/2);checks+=1
                    if hit:hit=dict(hit,group=group,yaw=yaw,pitch=pitch);break
                if hit:break
            if hit:break
        if hit:failed.append(dict(case,**hit));continue
        key=f'pin{pin}_candidate{len(accepted)}';arrays[key]=p
        accepted.append(dict(case,id=key,length_mm=L,chord_error_mm=err,start_mm=a.tolist(),end_mm=b.tolist()))
        print('UPPER_FAN_OPTION',pin,len(accepted),case,flush=True)
        if len(accepted)>=12:break
    results.append(dict(pin=pin,status='PASS' if accepted else 'BLOCKED',candidates=accepted,failures=failed))
    print('UPPER_FAN_PIN',pin,len(accepted),'rejected',len(failed),flush=True)
ctx.targets=original;ctx.assert_unchanged()
np.savez_compressed(HERE/'upper_fan_front_pin1_candidates.npz',**arrays)
report=dict(status='PASS' if all(r['candidates'] for r in results) else 'BLOCKED',sources=ctx.sources,
    source_blend_sha256=ctx.source_hash,rows=results,checks=checks,
    inputs={name:sha(HERE/name) for name in ['current_source_verification.json','cam_upper_screen.json','cam_upper_candidates.npz','body_layered_four_screen.json','body_layered_four_candidates.npz','upper_curve_geometry.py','front_neck_candidates.npz','front_route_screen.json']},
    curve_sha256=sha(HERE/'upper_fan_front_pin1_candidates.npz'),script_sha256=sha(Path(__file__)),
    scope='Individual tangent circular fan-in options versus all current solids; trims only the first straight0/2/4mm of the existing loop',
    radius_lower_bound_mm=7.,required_surface_gap_mm=.3,wire_OD_mm=.6604,
    wire_wire='NOT_TESTED',anchors='NOT_TESTED',full_harness='BLOCKED',main_changed=False,
    supplier_cut_lengths_released=False,elapsed_s=time.time()-start_time)
(HERE/'upper_fan_front_pin1_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('UPPER_FAN_DONE',report['status'],checks,flush=True)
