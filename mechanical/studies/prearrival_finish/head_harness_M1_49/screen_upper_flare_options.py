"""Independent CAM route study: flare four neck curves away from old pitch loops.

Hardware and all prints remain unchanged. The other seven local wires use
their exact previous coordinates. A local PASS would still need lower-prefix
and upper-transition joining, anchors and assembly validation.
"""
from pathlib import Path
import itertools,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes/upper_flare_review';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from validate import rigidtr
from route_family import family,rotate
from curve_clearance import prepared,pair
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
N=HERE/'remaining_routes/left_tall_balanced';n=read(N/'neck_screen.json');ur=read(HERE/'cam_upper_screen.json')
for report in [n,ur]:
    assert report['status']=='PASS'
    for name,h in report['sources'].items():assert sha(ROOT/name)==h,name
    for name,h in report.get('inputs',{}).items():
        root=ROOT if name.startswith(('mechanical/','config/','hardware/','contracts/')) else HERE
        assert sha(root/name)==h,name
assert sha(N/'neck_candidates.npz')==n['curve_sha256']
assert sha(HERE/'cam_upper_candidates.npz')==ur['curve_sha256']
base=np.load(N/'neck_candidates.npz');loops=np.load(HERE/'cam_upper_candidates.npz')
source_row=next(r for r in n['results'] if r['status']=='PASS');angles=source_row['angles_deg'];ods=n['OD_mm']
native=ctx.targets;groups={name:s.group if s.group in ['yaw','pitch'] else 'body' for name,s in ctx.ss.items()}
targets={g:{name:t for name,t in native.items() if groups.get(name,'body')==g} for g in ['body','yaw','pitch']}
results=[];arrays={};upper={(pin,pitch):prepared(loops[f'slot{pin-1}_pitch{pitch}'],.3302,.0003) for pin,pitch in itertools.product(range(1,5),range(-20,26,5))}
for case,r1,bend in [('r17_R30',17.,30.),('r18_5_R20',18.5,20.)]:
    rows=family(z0=149.,r1=r1,flare_start=173.,flare_radius=bend,dip=.6,samples=7201)
    error=max(r['chord_error_mm'] for r in rows);curves={};hits=[];checks=0
    for slot in range(11):
        for row in rows:
            yaw=row['yaw_deg'];key=f'wire{slot}_y{yaw}'
            if slot<7:curves[key]=base[f'z149.0_dip0.6_{key}'];continue
            p=rotate(row['points'],angles[slot]);a=p[0].copy();a[2]=142.
            curves[key]=np.vstack([np.linspace(a,p[0],235),p[1:]])
            assert np.linalg.norm(curves[key][0]-base[f'z149.0_dip0.6_{key}'][0])<1e-9
            for group,t in targets.items():
                ctx.targets=t
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    hit=ctx.clear(curves[key]@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=error);checks+=1
                    if hit:hits.append(dict(slot=slot,yaw=yaw,pitch=pitch,group=group,**hit))
        print('FLARE_NATIVE',case,slot,len(hits),flush=True)
    pair_rows=[];upper_rows=[];departure_rows=[]
    if not hits:
        for yaw in range(-60,61,10):
            items={i:prepared(curves[f'wire{i}_y{yaw}'],ods[i]/2,error if i>=7 else source_row['chord_error_mm']) for i in range(11)}
            for a,b in itertools.combinations(items,2):pair_rows.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
            inv=np.linalg.inv(np.asarray(rigidtr(yaw,0)))
            for slot in range(7,11):
                p=curves[f'wire{slot}_y{yaw}'];q=p@inv[:3,:3].T+inv[:3,3];item=prepared(q,.3302,error)
                for (pin,pitch),u in upper.items():
                    r=pair_threshold(item,u)
                    if r['status']!='PASS':upper_rows.append(dict(slot=slot,yaw=yaw,pin=pin,pitch=pitch,**r))
        # Directional evidence only; accepted arcs are not completed fan routes.
        for pin,slot in {1:9,2:8,3:7,4:10}.items():
            start=curves[f'wire{slot}_y0'][-1];aa=np.linspace(0,math.pi/4,281);err=7*(1-math.cos((aa[1]-aa[0])/2))
            for angle in range(0,360,10):
                a=math.radians(angle);direction=np.array([math.cos(a),math.sin(a),0.]);up=np.array([0.,0.,1.])
                p=start+7*(1-np.cos(aa))[:,None]*direction+7*np.sin(aa)[:,None]*up;item=prepared(p,.3302,err);bad=None
                for (other,pitch),u in upper.items():
                    r=pair_threshold(item,u)
                    if r['status']!='PASS':bad=dict(kind='upper_loop',pin=other,pitch=pitch,**r);break
                if not bad:
                    for group,t in targets.items():
                        ctx.targets=t
                        for yaw,pitch in itertools.product(range(-60,61,10) if group=='body' else [0],range(-20,26,5) if group=='pitch' else [0]):
                            tr=np.asarray(rigidtr(yaw,0)) if group=='body' else np.eye(4) if group=='yaw' else np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                            h=ctx.clear(p@tr[:3,:3].T+tr[:3,3],radius=.3302,chord_error=err)
                            if h:bad=dict(kind='native',group=group,yaw=yaw,pitch=pitch,**h);break
                        if bad:break
                departure_rows.append(dict(pin=pin,heading_deg=angle,status='BLOCKED' if bad else 'PASS',failure=bad))
        print('FLARE_DEPARTURES',case,{pin:[r['heading_deg'] for r in departure_rows if r['pin']==pin and r['status']=='PASS'] for pin in range(1,5)},flush=True)
    ok=not hits and len(pair_rows)==715 and all(r['status']=='PASS' for r in pair_rows) and not upper_rows and min(r['minimum_sampled_bend_mm'] for r in rows)>=7
    result=dict(id=case,status='PASS' if ok else 'BLOCKED',upper_radius_mm=r1,flare_circle_radius_mm=bend,
        hits=hits,native_checks=checks,pair_checks=pair_rows,upper_loop_conflicts=upper_rows,departure_options=departure_rows,
        minimum_sampled_bend_mm=min(r['minimum_sampled_bend_mm'] for r in rows),chord_error_mm=error,
        dynamic_length_mm=[r['length_mm'] for r in rows],join_start_unchanged=True,scope='Only four modified local curves plus unchanged seven and existing CAM upper loop interactions')
    results.append(result);arrays.update({case+'_'+key:p for key,p in curves.items()});print('FLARE_CASE',case,result['status'],flush=True)
ctx.targets=native;ctx.assert_unchanged();np.savez_compressed(OUT/'curves.npz',**arrays)
inputs=[N/'neck_screen.json',N/'neck_candidates.npz',HERE/'cam_upper_screen.json',HERE/'cam_upper_candidates.npz',HERE/'route_family.py',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']
report=dict(status='PASS' if any(r['status']=='PASS' for r in results) else 'BLOCKED',sources=ctx.sources,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},results=results,curve_sha256=sha(OUT/'curves.npz'),
    full_endpoint_routing='BLOCKED',lower_prefix_joint='NOT_TESTED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    main_changed=False,C6_approval='PENDING',manufacturing_release=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'flare_screen.json').write_text(json.dumps(report,indent=2)+'\n');print('UPPER_FLARE_DONE',report['status'],report['elapsed_s'],flush=True)
