"""Read-only directional screening at the four current CAM neck endpoints.

This checks only an initial 45-degree, R7 arc. It cannot certify a completed
route. It locates why the old upper transition family fails before changing
that family or the independently reviewed lower C6 candidate.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/upper_departure_review';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
N=HERE/'remaining_routes/left_tall_balanced';n=read(N/'neck_screen.json')
u=read(HERE/'cam_upper_screen.json')
for report in [n,u]:
    assert report['status']=='PASS'
    for name,h in report['sources'].items():assert sha(ROOT/name)==h,name
    for name,h in report.get('inputs',{}).items():
        p=(ROOT/name if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE/name)
        assert sha(p)==h,name
assert sha(N/'neck_candidates.npz')==n['curve_sha256']
assert sha(HERE/'cam_upper_candidates.npz')==u['curve_sha256']
neck=np.load(N/'neck_candidates.npz');upper=np.load(HERE/'cam_upper_candidates.npz')
up={(pin,pitch):prepared(upper[f'slot{pin-1}_pitch{pitch}'],.3302,.0003)
    for pin,pitch in itertools.product(range(1,5),range(-20,26,5))}
native=ctx.targets;groups={name:s.group if s.group in ['yaw','pitch'] else 'body' for name,s in ctx.ss.items()}
targets={g:{name:t for name,t in native.items() if groups.get(name,'body')==g} for g in ['body','yaw','pitch']}
R=7.;aa=np.linspace(0,math.pi/4,281);err=R*(1-math.cos((aa[1]-aa[0])/2));UP=np.array([0.,0.,1.])
rows=[];curves={};checks=0
for pin,slot in {1:9,2:8,3:7,4:10}.items():
    start=neck[f'z149.0_dip0.6_wire{slot}_y0'][-1]
    for angle in range(0,360,5):
        a=math.radians(angle);d=np.array([math.cos(a),math.sin(a),0.])
        p=start+R*(1-np.cos(aa))[:,None]*d+R*np.sin(aa)[:,None]*UP
        item=prepared(p,.3302,err);bad=None
        for (other,pitch),other_item in up.items():
            r=pair_threshold(item,other_item);checks+=1
            if r['status']!='PASS':bad=dict(kind='upper_loop',other_pin=other,pitch=pitch,**r);break
        if not bad:
            for group,t in targets.items():
                ctx.targets=t
                for yaw,pitch in itertools.product(range(-60,61,10) if group=='body' else [0],range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                    hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=err);checks+=1
                    if hit:bad=dict(kind='native',group=group,yaw=yaw,pitch=pitch,**hit);break
                if bad:break
        key=f'pin{pin}_heading{angle}';curves[key]=p
        rows.append(dict(id=key,pin=pin,slot=slot,heading_deg=angle,status='BLOCKED' if bad else 'PASS',failure=bad))
    print('UPPER_DEPARTURE_PIN',pin,[r['heading_deg'] for r in rows if r['pin']==pin and r['status']=='PASS'],flush=True)
ctx.targets=native;ctx.assert_unchanged()
np.savez_compressed(OUT/'arcs.npz',**curves)
inputs=[N/'neck_screen.json',N/'neck_candidates.npz',HERE/'cam_upper_screen.json',HERE/'cam_upper_candidates.npz',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
report=dict(status='PASS',scope='Diagnostic execution only: a45deg R7 initial departure, not a completed route or mutual four-arc packing',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},rows=rows,
    arc_radius_mm=R,arc_sweep_deg=45.,arc_chord_error_mm=err,wire_OD_mm=.6604,required_gap_mm=.3,
    curve_sha256=sha(OUT/'arcs.npz'),checks=checks,main_changed=False,C6_approval='PENDING',
    full_harness='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',manufacturing_release=False,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'departure_review.json').write_text(json.dumps(report,indent=2)+'\n')
print('UPPER_DEPARTURE_DONE',report['elapsed_s'],flush=True)
