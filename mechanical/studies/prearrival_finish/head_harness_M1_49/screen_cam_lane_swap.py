"""Swap CAM1/2 mechanical neck lanes without changing either logical endpoint.

All nine root stems and all other neck wires remain obstacles. The four CAM
body routes alone are varied; no structure or endpoint is moved.
"""
from pathlib import Path
import sys,json,math,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/cam_lane_swap';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from curvature_paths import paths
from curve_clearance import prepared
from bounded_curve_checks import pair_threshold
ctx=Context();started=time.time();Z=142.;step=.06;UP=np.array([0.,0.,1.])
lane_path=HERE/'remaining_routes/higher_entry/neck_screen.json';lane_report=json.loads(lane_path.read_text())
lane=next(r for r in lane_report['results'] if r['z0_mm']==Z);assert lane['status']=='PASS'
for f,h in {**lane_report['sources'],**lane_report['inputs']}.items():assert sha(PROJECT/f)==h,f
neck_file=HERE/'remaining_routes/higher_entry/neck_candidates.npz';neck=np.load(neck_file)
assert sha(neck_file)==lane_report['curve_sha256']
angles=lane['angles_deg'];functions=[]
for port,prefix,pins,slots,radius,OD in [
    ('power_J9','P_J9',[1,2,3],[0,1,2,6],6.5,1.1684),
    ('power_J18','P_J18',[1,2],[3,4,5],6.5,1.1684),
    ('motion_J5','CAM',[1,2,3,4],None,7.,.6604)]:
    for pin in pins:
        functions.append(dict(endpoint=prefix+'_'+str(pin),port=port,pin=pin,
            p=ctx.port_pins[port]['pins'][str(pin)],axis=ctx.port_pins[port]['axis'],
            slots=slots or [{1:7,2:10,3:9,4:8}[pin]],R=radius,OD=OD))
def line(a,b):return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
roots={f['endpoint']:prepared(line(f['p'],f['p']+5*UP),f['OD']/2,0.) for f in functions}
locals_={i:prepared(neck[f'z{Z}_wire{i}_y0'],.5842 if i<7 else .3302,lane['chord_error_mm']) for i in range(11)}
fail=collections.Counter();witness={};pools={};curves={};trials=0;peer_checks=0
def count(hit):fail[hit['object']]+=1;witness.setdefault(hit['object'],hit)
def peers(p,error,OD,near):
    global peer_checks
    item=prepared(p,OD/2,error)
    for name,b in near.items():
        result=pair_threshold(item,b);peer_checks+=1
        if result['status']!='PASS':return dict(object=name,**result)
    return None
def exit_section(q,h,top,R,tt):
    bottom=q-R*h-R*UP;drop=top-bottom[2]
    if drop<=0:return None
    angle=math.acos(1-drop/(2*R)) if drop<2*R else math.pi/2
    aa=np.linspace(0,angle,math.ceil(R*angle/step)+1)
    c=bottom-2*R*math.sin(angle)*h+drop*UP
    a=c+R*np.sin(aa)[:,None]*h-R*(1-np.cos(aa))[:,None]*UP
    v=line(a[-1],a[-1]-max(0.,drop-2*R)*UP);back=aa[::-1]
    b=v[-1]+R*(math.sin(angle)-np.sin(back))[:,None]*h-R*(np.cos(back)-math.cos(angle))[:,None]*UP
    last=bottom+R*np.sin(tt)[:,None]*h+R*(1-np.cos(tt))[:,None]*UP
    assert np.linalg.norm(b[-1]-bottom)<1e-8
    return np.vstack([a,v[1:],b[1:],last[1:]]),2*R*angle+max(0.,drop-2*R)+R*math.pi/2
preferred={1:(7.1,345,120),2:(7.1,330,110),3:(6.05,0,110),4:(5.,30,190)}
for f in [x for x in functions if x['port']=='motion_J5' and x['pin']<=2]:
    lead0,ea0,xa0=preferred[f['pin']]
    R=f['R'];OD=f['OD'];p=f['p'];assert np.allclose(f['axis'],UP)
    tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1);error=R*(1-math.cos(step/(2*R)))
    root_near={'root_'+k:v for k,v in roots.items() if k!=f['endpoint']}
    for lead in [5.,6.05,7.1]:
        a=p+lead*UP;stem=line(p,a);top=a[2]+R
        hit=ctx.clear(stem,ignore=['Plug_'+f['port']],radius=OD/2) or peers(stem,0.,OD,root_near)
        if hit:count(hit);continue
        for slot in f['slots']:
            near={**root_near,**{'neck_'+str(k):v for k,v in locals_.items() if k!=slot}}
            theta=math.radians(angles[slot]);q=np.array([10.6*math.cos(theta),10.6*math.sin(theta),Z])
            entries=[];exits=[];good=[]
            for az in range(0,360,5):
                h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
                arc=a+R*(1-np.cos(tt))[:,None]*h+R*np.sin(tt)[:,None]*UP
                hit=ctx.clear(arc,chord_error=error,radius=OD/2) or peers(arc,error,OD,near)
                if hit:count(hit)
                else:entries.append((az,h,arc))
                candidate=exit_section(q,h,top,R,tt)
                if candidate:
                    end,length=candidate
                    hit=ctx.clear(end,chord_error=error,radius=OD/2) or peers(end,error,OD,near)
                    if hit:count(hit)
                    else:exits.append((az,h,end,length))
            for ea,eh,entry in entries:
                for radius in [R,R+2,R+4]:
                    accepted=0
                    for xa,xh,end,exit_length in sorted(exits,key=lambda e:np.linalg.norm(e[2][0]-entry[-1])):
                        if accepted>=4:break
                        for plan in paths(entry[-1,:2],eh[:2],end[0,:2],xh[:2],radius,step):
                            if accepted>=4:break
                            trials+=1
                            if plan['analytic_length_mm']>160:continue
                            xy=plan['points_xy_mm']
                            if np.max(np.linalg.norm(xy,axis=1))>75:continue
                            middle=np.c_[xy,np.full(len(xy),top)]
                            hit=ctx.clear(middle,chord_error=plan['chord_error_mm'],radius=OD/2) or peers(middle,plan['chord_error_mm'],OD,near)
                            if hit:count(hit);continue
                            accepted+=1
                            points=np.vstack([stem,entry[1:],middle[1:],end[1:]])
                            good.append(dict(endpoint=f['endpoint'],port=f['port'],pin=f['pin'],slot=slot,lead_mm=lead,
                                entry_deg=ea,exit_deg=xa,minimum_centerline_radius_mm=R,planar_radius_mm=radius,OD_mm=OD,
                                plane_z_mm=top,analytic_length_mm=lead+R*math.pi/2+plan['analytic_length_mm']+exit_length,
                                chord_error_mm=max(error,plan['chord_error_mm']),family=plan['family'],points=points))
            # Retain varied headings and planar radii before adding close variants.
            good.sort(key=lambda r:r['analytic_length_mm']);chosen=[];seen=set()
            for r in good:
                key=(r['entry_deg'],r['exit_deg'],r['planar_radius_mm'],r['family'])
                if key not in seen:chosen.append(r);seen.add(key)
                if len(chosen)>=200:break
            key=f'{f["endpoint"]}_slot{slot}_lead{lead:g}'
            for i,r in enumerate(chosen):
                r['id']='swap_'+key+'_'+str(i);curves[r['id']]=r.pop('points')
            pools[key]=chosen
            print('CAM_SWAP_POOL',key,'entry',len(entries),'exit',len(exits),'found',len(good),'kept',len(chosen),flush=True)
ctx.assert_unchanged();np.savez_compressed(OUT/'body_prefix_candidates.npz',**curves)
identities=[f['endpoint'] for f in functions if f['port']=='motion_J5' and f['pin']<=2]
report=dict(status='PASS' if all(any(r['endpoint']==k for rs in pools.values() for r in rs) for k in identities) else 'BLOCKED',
    scope='CAM1/2 swapped mechanical lanes only; logical endpoints unchanged, all nine roots and other local neck wires retained as obstacles',sources=ctx.sources,
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [lane_path,neck_file,HERE/'bounded_curve_checks.py',HERE/'curve_clearance.py']},
    functions=[{k:(v.tolist() if hasattr(v,'tolist') else v) for k,v in f.items()} for f in functions],
    pools=pools,angles_deg=angles,z0_mm=Z,trials=trials,peer_checks=peer_checks,fail_counts=dict(fail),first_witness=witness,
    curve_sha256=sha(OUT/'body_prefix_candidates.npz'),script_sha256=sha(Path(__file__)),
    full_harness='BLOCKED',wire_selection='BLOCKED',main_changed=False,elapsed_s=time.time()-started)
(OUT/'body_prefix_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAM_SWAP_POOL_DONE',report['status'],len(curves),flush=True)
