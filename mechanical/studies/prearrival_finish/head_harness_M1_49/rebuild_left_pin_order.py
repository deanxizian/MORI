"""Rebuild left-window options in the opposite mechanical order, never swapping pins.

Reuse successful curve parameters as seeds, recompute every arc from the
correct PCB root, and recheck native obstacles. No old point cloud is shifted
to misrepresent a connector root.
"""
from pathlib import Path
import collections,json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/cam_left_front_prefix';LANE=HERE/'remaining_routes/cam_left_front_bank'
OUT=HERE/'remaining_routes/cam_left_pin_order';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from curvature_paths import paths
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();source=json.loads((BASE/'body_prefix_screen.json').read_text())
lane_report=json.loads((LANE/'neck_screen.json').read_text());lane=next(r for r in lane_report['results'] if r['status']=='PASS')
for report in [source,lane_report]:
    for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(BASE/'body_prefix_candidates.npz')==source['curve_sha256']
assert sha(LANE/'neck_candidates.npz')==lane_report['curve_sha256']
neck=np.load(LANE/'neck_candidates.npz');UP=np.array([0.,0.,1.]);step=.06
def line(a,b):return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
roots={}
for f in source['functions']:
    p=ctx.port_pins[f['port']]['pins'][str(f['pin'])]
    roots[f['endpoint']]=prepared(line(p,p+5*UP),f['OD']/2,0.)
local={i:prepared(neck[f'z142.0_dip0.6_wire{i}_y0'],lane_report['OD_mm'][i]/2,lane['chord_error_mm']) for i in range(11)}
def end_curve(q,h,top,R,tt):
    bottom=q-R*h-R*UP;drop=top-bottom[2];assert drop>0
    angle=math.acos(1-drop/(2*R)) if drop<2*R else math.pi/2
    aa=np.linspace(0,angle,math.ceil(R*angle/step)+1)
    c=bottom-2*R*math.sin(angle)*h+drop*UP
    a=c+R*np.sin(aa)[:,None]*h-R*(1-np.cos(aa))[:,None]*UP
    v=line(a[-1],a[-1]-max(0.,drop-2*R)*UP);back=aa[::-1]
    b=v[-1]+R*(math.sin(angle)-np.sin(back))[:,None]*h-R*(np.cos(back)-math.cos(angle))[:,None]*UP
    last=bottom+R*np.sin(tt)[:,None]*h+R*(1-np.cos(tt))[:,None]*UP
    assert np.linalg.norm(b[-1]-bottom)<1e-8
    return np.vstack([a,v[1:],b[1:],last[1:]]),2*R*angle+max(0.,drop-2*R)+R*math.pi/2
curves={};pools=collections.defaultdict(list);failures=collections.Counter();witness={};seen=set();checks=0
for seed in [r for rr in source['pools'].values() for r in rr]:
    pin=3-seed['pin'];endpoint=f'CAM_{pin}';slot=seed['slot'];R=seed['minimum_centerline_radius_mm']
    identity=(pin,slot,seed['lead_mm'],seed['entry_deg'],seed['exit_deg'],seed['planar_radius_mm'],seed['family'])
    if identity in seen:continue
    seen.add(identity)
    p=ctx.port_pins['motion_J5']['pins'][str(pin)];a=p+seed['lead_mm']*UP
    eh=np.array([math.cos(math.radians(seed['entry_deg'])),math.sin(math.radians(seed['entry_deg'])),0.])
    xh=np.array([math.cos(math.radians(seed['exit_deg'])),math.sin(math.radians(seed['exit_deg'])),0.])
    tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
    stem=line(p,a);entry=a+R*(1-np.cos(tt))[:,None]*eh+R*np.sin(tt)[:,None]*UP
    q=neck[f'z142.0_dip0.6_wire{slot}_y0'][0];end,end_length=end_curve(q,xh,entry[-1,2],R,tt)
    plan=next((v for v in paths(entry[-1,:2],eh[:2],end[0,:2],xh[:2],seed['planar_radius_mm'],step) if v['family']==seed['family']),None)
    if plan is None:continue
    middle=np.c_[plan['points_xy_mm'],np.full(len(plan['points_xy_mm']),entry[-1,2])]
    error=max(R*(1-math.cos(step/(2*R))),plan['chord_error_mm'])
    points=np.vstack([stem,entry[1:],middle[1:],end[1:]])
    hit=ctx.clear(stem,ignore=['Plug_motion_J5'],radius=.3302) or ctx.clear(points[len(stem)-1:],chord_error=error,radius=.3302);checks+=1
    if not hit:
        item=prepared(points,.3302,error)
        for name,target in {**{'root_'+k:v for k,v in roots.items() if k!=endpoint},**{'neck_'+str(k):v for k,v in local.items() if k!=slot}}.items():
            result=pair_threshold(item,target);checks+=1
            if result['status']!='PASS':hit=dict(object=name,**result);break
    if hit:failures[hit['object']]+=1;witness.setdefault(hit['object'],hit);continue
    key='leftorder_'+seed['id'];curves[key]=points
    row=dict(seed,id=key,pin=pin,endpoint=endpoint,port='motion_J5',
             analytic_length_mm=seed['lead_mm']+R*math.pi/2+plan['analytic_length_mm']+end_length,
             chord_error_mm=error,source_seed=seed['id'])
    pools[f'{endpoint}_slot{slot}'].append(row)
    if len(curves)%50==0:print('LEFT_ORDER_ACCEPTED',len(curves),len(seen),flush=True)
ctx.assert_unchanged();np.savez_compressed(OUT/'body_prefix_candidates.npz',**curves)
report=dict(status='PASS' if all(any(r['pin']==i for rr in pools.values() for r in rr) for i in [1,2]) else 'BLOCKED',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [BASE/'body_prefix_screen.json',BASE/'body_prefix_candidates.npz',LANE/'neck_screen.json',LANE/'neck_candidates.npz',HERE/'curve_clearance.py',HERE/'bounded_curve_checks.py']},
    functions=source['functions'],pools=dict(pools),angles_deg=lane['angles_deg'],z0_mm=142.,checks=checks,
    fail_counts=dict(failures),first_witness=witness,curve_sha256=sha(OUT/'body_prefix_candidates.npz'),
    scope='Individual left-window alternatives with reversed mechanical ordering; PCB root and final logical pin identities retained',
    full_harness='BLOCKED',wire_selection='BLOCKED',main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'body_prefix_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('LEFT_ORDER_DONE',report['status'],len(curves),report['elapsed_s'],flush=True)
