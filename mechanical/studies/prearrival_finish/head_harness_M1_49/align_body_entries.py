"""Rebuild the retained body candidates at the mutually spaced neck entrances.

This checks individual options; no electrical assignment or simultaneous
four-wire body layout is adopted by this script.
"""
from pathlib import Path
import sys,json,math,time,collections
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from curvature_paths import paths
ctx=Context();start=time.time()
old=json.loads((HERE/'body_spatial_screen.json').read_text())
local=json.loads((HERE/'spaced_entry_screen.json').read_text())
packing=json.loads((HERE/'spaced_local_packing.json').read_text())
assert old['status']==local['status']==packing['status']=='PASS'
for report in [old,local,packing]:
    for p,h in report['sources'].items():assert sha(PROJECT/p)==h,p
native=np.load(HERE/'body_spatial_candidates.npz')
assert sha(HERE/'body_spatial_candidates.npz')==old['curve_sha256']
angles=local['results'][0]['angles_deg'];Z=local['results'][0]['body_entry_z_mm']
neck=np.load(HERE/'spaced_entry_candidates.npz')
R=7.;step=.06;arrays={};rows={};failed=[]
pins={int(k):v for k,v in ctx.port_pins['motion_J5']['pins'].items()}
def segment(a,b):return np.linspace(a,b,max(2,math.ceil(np.linalg.norm(b-a)/step)+1))
def make(row,azimuth):
    p=pins[row['pin']];a=p+[0,0,row['lead_mm']]
    top=a[2]+R;drop=top-(Z-R);alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
    tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1);qq=np.linspace(0,alpha,math.ceil(R*alpha/step)+1)
    e=math.radians(row['entry_deg']);eh=np.array([math.cos(e),math.sin(e),0.])
    x=math.radians(row['exit_deg']);xh=np.array([math.cos(x),math.sin(x),0.])
    t=math.radians(azimuth);q=np.array([10.6*math.cos(t),10.6*math.sin(t),Z])
    stem=segment(p,a)
    entry=a+R*(1-np.cos(tt[:,None]))*eh+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*np.sin(tt)]
    b=q-R*xh-[0,0,R];c=b-run*xh+[0,0,drop]
    first=c+R*np.sin(qq[:,None])*xh-np.c_[np.zeros(len(qq)),np.zeros(len(qq)),R*(1-np.cos(qq))]
    qr=qq[::-1]
    second=first[-1]+R*(math.sin(alpha)-np.sin(qr[:,None]))*xh-np.c_[np.zeros(len(qr)),np.zeros(len(qr)),R*(np.cos(qr)-math.cos(alpha))]
    final=b+R*np.sin(tt[:,None])*xh+np.c_[np.zeros(len(tt)),np.zeros(len(tt)),R*(1-np.cos(tt))]
    end=np.vstack([first,second[1:],final[1:]])
    options=[r for r in paths(entry[-1,:2],eh[:2],c[:2],xh[:2],row['planar_radius_mm'],step) if r['family']==row['family']]
    if not options:return None
    assert len(options)==1
    plan=options[0];xy=plan['points_xy_mm'];middle=np.c_[xy,np.full(len(xy),top)]
    full=np.vstack([stem,entry[1:],middle[1:],end[1:]])
    return full,len(stem),row['lead_mm']+R*math.pi+2*R*alpha+plan['analytic_length_mm'],max(plan['chord_error_mm'],R*(1-math.cos(step/R/2)))
for key,pool in old['pools'].items():
    accepted=[]
    for row in pool:
        old_result=make(row,old['angles_deg'][row['slot']])
        assert old_result and old_result[0].shape==native[row['id']].shape
        assert np.max(np.abs(old_result[0]-native[row['id']]))<1e-8
        candidate=make(row,angles[row['slot']])
        if candidate is None:failed.append(dict(id=row['id'],reason='finite tangent family unavailable'));continue
        p,n,L,error=candidate
        assert np.linalg.norm(p[-1]-neck[f'case0_wire{row["slot"]}_y0'][0])<1e-8
        hit=ctx.clear(p[:n],ignore=['Plug_motion_J5'],chord_error=error,radius=.6604/2)
        if not hit:hit=ctx.clear(p[n-1:],chord_error=error,radius=.6604/2)
        if hit:failed.append(dict(id=row['id'],**hit));continue
        arrays[row['id']]=p
        accepted.append(dict(row,body_entry_angle_deg=angles[row['slot']],length_mm=L,chord_error_mm=error,source_reconstruction_error_mm=float(np.max(np.abs(old_result[0]-native[row['id']])))))
    rows[key]=sorted(accepted,key=lambda r:r['length_mm'])
    print('ALIGNED_POOL',key,len(accepted),flush=True)
ctx.assert_unchanged();np.savez_compressed(HERE/'body_aligned_candidates.npz',**arrays)
result=dict(status='PASS' if all(rows.values()) else 'BLOCKED',scope='Individual CAM body-prefix options aligned to the checked11-wire entrance set; not simultaneous body routing',sources=ctx.sources,pools=rows,failed=failed,angles_deg=angles,body_entry_z_mm=Z,OD_mm=.6604,curve_sha256=sha(HERE/'body_aligned_candidates.npz'),inputs={p.name:sha(p) for p in [HERE/'body_spatial_screen.json',HERE/'spaced_entry_screen.json',HERE/'spaced_local_packing.json']},script_sha256=sha(Path(__file__)),main_changed=False,body_wire_packing='NOT_TESTED',body_motion='NOT_TESTED',full_endpoint_routing='BLOCKED',wired_assembly='NOT_TESTED',supplier_cut_lengths_released=False,elapsed_s=time.time()-start)
(HERE/'body_aligned_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('ALIGNED_BODY_DONE',result['status'],len(arrays),'rejected',len(failed),flush=True)
