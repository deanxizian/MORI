"""Tangent circular-bend body prefixes on the unchanged M1.49 main.

Three-dimensional entry/exit bends join a horizontal CSC/CCC path. All copied
math is explicit; no legacy study initialization or candidate print is loaded.
Individual pools do not certify simultaneous wiring or wired assembly.
"""
from pathlib import Path
import sys,json,math,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from curvature_paths import paths
ctx=Context();start=time.time();R=7.;step=.06
angles=[10,24,38,125,145,165,0,49,135,155,179]
slots=[7,8,9,10];Z=138.;OD=.6604
port='motion_J5';ports=ctx.port_pins[port]['pins'];axis=ctx.port_pins[port]['axis']
ends={};fail=collections.Counter();witness={};pools={};arrays={};trials=0
def count(hit):
    fail[hit['object']]+=1;witness.setdefault(hit['object'],hit)
def segment(a,b):return np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)/step)+1))
for pin,p in ports.items():
    pin=int(pin);p=np.asarray(p)
    for lead in [5.]:
        a=p+axis*lead;stem=segment(p,a)
        hit=ctx.clear(stem,ignore=['Plug_'+port],radius=OD/2)
        if hit:count(hit);continue
        top=a[2]+R;drop=top-(Z-R)
        assert 0<drop<2*R
        alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
        tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
        qq=np.linspace(0,alpha,math.ceil(R*alpha/step)+1)
        err=R*(1-math.cos(step/R/2))
        entries=[]
        for az in range(0,360,15):
            h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
            curve=a+R*(1-np.cos(tt[:,None]))*h+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*np.sin(tt)]
            hit=ctx.clear(curve,chord_error=err,radius=OD/2)
            if hit:count(hit)
            else:entries.append((az,h,curve))
        for slot in slots:
            theta=math.radians(angles[slot]);q=np.array([10.6*math.cos(theta),10.6*math.sin(theta),Z])
            exits=[];pool=[]
            for az in range(0,360,10):
                h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
                b=q-R*h-[0,0,R];c=b-run*h+[0,0,drop]
                first=c+R*np.sin(qq[:,None])*h-np.c_[np.zeros(len(qq)),np.zeros(len(qq)),R*(1-np.cos(qq))]
                qr=qq[::-1]
                second=first[-1]+R*(math.sin(alpha)-np.sin(qr[:,None]))*h-np.c_[np.zeros(len(qr)),np.zeros(len(qr)),R*(np.cos(qr)-math.cos(alpha))]
                final=b+R*np.sin(tt[:,None])*h+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*(1-np.cos(tt))]
                curve=np.vstack([first,second[1:],final[1:]])
                assert np.linalg.norm(second[-1]-b)<1e-8 and np.linalg.norm(curve[-1]-q)<1e-8
                hit=ctx.clear(curve,chord_error=err,radius=OD/2)
                if hit:count(hit)
                else:exits.append((az,h,curve))
            print('SPATIAL_ENDPOINTS',pin,slot,len(entries),len(exits),flush=True)
            for eaz,eh,entry in entries:
                for xaz,xh,exit_curve in exits:
                    for radius in [7.,9.,12.]:
                        for plan in paths(entry[-1,:2],eh[:2],exit_curve[0,:2],xh[:2],radius,step):
                            trials+=1
                            if plan['analytic_length_mm']>170:continue
                            xy=plan['points_xy_mm']
                            if np.max(np.linalg.norm(xy,axis=1))>75:continue
                            middle=np.c_[xy,np.full(len(xy),top)]
                            hit=ctx.clear(middle,chord_error=plan['chord_error_mm'],radius=OD/2)
                            if hit:count(hit);continue
                            points=np.vstack([stem,entry[1:],middle[1:],exit_curve[1:]])
                            length=lead+R*math.pi+2*R*alpha+plan['analytic_length_mm']
                            pool.append(dict(pin=pin,slot=slot,lead_mm=lead,entry_deg=eaz,exit_deg=xaz,planar_radius_mm=radius,minimum_bend_mm=R,length_mm=length,chord_error_mm=max(err,plan['chord_error_mm']),family=plan['family'],points=points))
            key=f'pin{pin}_slot{slot}'
            chosen=sorted(pool,key=lambda r:r['length_mm'])[:12]
            for j,row in enumerate(chosen):
                cid=key+f'_{j}';arrays[cid]=row.pop('points');row['id']=cid
            pools[key]=chosen
            print('SPATIAL_BODY_POOL',key,len(pool),'kept',len(chosen),flush=True)
ctx.assert_unchanged()
np.savez_compressed(HERE/'body_spatial_candidates.npz',**arrays)
r=dict(status='PASS' if all(any(pools.get(f'pin{p}_slot{s}') for s in slots) for p in range(1,5)) else 'BLOCKED',scope='Individual CAM body-prefix candidates only',sources=ctx.sources,pools=pools,angles_deg=angles,body_entry_z_mm=Z,OD_mm=OD,trials=trials,fail_counts=dict(fail),first_witness=witness,main_changed=False,curve_sha256=sha(HERE/'body_spatial_candidates.npz'),script_sha256=sha(Path(__file__)),full_harness='BLOCKED',wire_packing='NOT_TESTED',wired_assembly='NOT_TESTED',elapsed_s=time.time()-start)
(HERE/'body_spatial_screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('SPATIAL_BODY_DONE',r['status'],len(arrays),dict(fail),flush=True)
