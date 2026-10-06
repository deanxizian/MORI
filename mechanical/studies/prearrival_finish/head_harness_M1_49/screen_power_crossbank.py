"""Unselected Alpha2622 reference screen for five body conductors; same22AWG.

The seven large neck strands are capacity samples, not selected SH/GH leads.
This screen binds only the five native J9/J18 functions. It does not invent
servo splitter, USB plug, speaker terminal geometry or supplier cut lengths.
"""
from pathlib import Path
import csv, json, math, sys, time, collections
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
OUT = HERE/'remaining_routes/thermothin2622_crossbank'
OUT.mkdir(exist_ok=True,parents=True)
sys.path.insert(0, str(PROJECT/'mechanical/scripts'))
sys.path.insert(0, str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context, np, sha
from curvature_paths import paths
sys.path.insert(0,str(HERE))
from curve_clearance import prepared,pair
ctx = Context(); started = time.time()
R = 7.; OD = 1.1684; step = .06; Z = 138.
angles = [11,22,33,125,144,163,0,49,135,153,42]
native = ctx.targets
cam=np.load(HERE/'front_lower_curves.npz')
near={k:prepared(cam[f'pin{k}_y0'],.3302,.0001) for k in range(1,5)}
peer_checks=0
def peers(p,error):
    global peer_checks
    a=prepared(p,OD/2,error)
    for pin,b in near.items():
        r=pair(a,b);peer_checks+=1
        if r['status']!='PASS':return dict(object='CAM_pin'+str(pin),**r)
    return None
inputs = [PROJECT/'hardware/v1_2/interfaces/harness_V1.2-H0.5-P5R7.csv',
    PROJECT/'hardware/v1_2/head_harness_evidence_20261003/head_interface_pinmap_revA.csv',
    PROJECT/'hardware/v1_2/prearrival_20261002/harness_detail.csv',
    PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A8_shortlead.json',
    HERE/'front_neck_candidates.npz', HERE/'front_lower_verification.json',
    HERE/'front_lower_curves.npz', HERE/'curve_clearance.py', HERE/'remaining_routes/sources/receipt.json', HERE/'remaining_routes/sources/alpha_2622_facts.json']
source_hashes = {str(p.relative_to(PROJECT)):sha(p) for p in inputs}
records = list(csv.DictReader(inputs[0].open(encoding='utf-8-sig')))
functions = []
for record in records:
    if record['harness_id'] not in ['P_J9','P_J18']:continue
    a=json.loads(record['from_']);b=json.loads(record['to'])
    port='power_'+a['connector'];pin=str(a['pin'])
    functions.append(dict(id=record['harness_id']+'_'+pin,port=port,pin=pin,
        function=a['signal'],target_function=b['signal'],target=b['board'],
        native_exit_mm=ctx.port_pins[port]['pins'][pin].tolist(),
        native_axis=ctx.port_pins[port]['axis'].tolist(),
        endpoint_basis='Native PCB pad projected to mating allocation; crimp exit unconfirmed',
        remote_cavity=None,neck_slot=None,
        crosses=['yaw'] if a['connector']=='J9' else ['yaw','pitch']))
assert len(functions)==5
spk=[dict(id='SPK_'+str(i),function=f'PA_OUTL{sign}',
    source='CAM J5 pin'+str(i),target='User-selected SP3040',
    source_physical_cavity=None,target_lead_exit_mm=None,
    crosses=['yaw','pitch'],neck_slot=None) for i,sign in [(1,'+'),(2,'-')]]
inventory=dict(status='PASS',scope='Seven functional conductors and known body endpoints only',
    sources={**ctx.sources,**source_hashes},functions=functions+spk,
    capacity_OD_mm=OD,planning_centerline_radius_mm=R,
    radius_basis='Unselected Alpha2622 catalogue22AWG OD1.0668..1.1684mm,5xOD bend reference5.842mm; use R7mm exceeding6.4262mm after radial allowance. Nickel-plated conductor and crimp/dynamic life still require qualification.',
    selected_wires=False,remote_ports='BLOCKED',main_changed=False,
    motor_groups='Both servo bodies are yaw; their interconnection is static relative to yaw',
    no_extra_GND_on_speaker=True,full_harness='BLOCKED')
(OUT/'functional_endpoints.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')

def line(a,b):
    return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
tt=np.linspace(0,math.pi/2,math.ceil(R*math.pi/2/step)+1)
up=np.array([0.,0.,1.]);err=R*(1-math.cos(step/R/2))
fail=collections.Counter();witness={};pools={};curves={};trials=0
entry_checks=0;exit_checks=0
def hitcount(hit):
    fail[hit['object']]+=1;witness.setdefault(hit['object'],hit)
def exit_section(q,h,top):
    bottom=q-R*h-R*up;drop=top-bottom[2]
    if drop<=0:return None
    alpha=math.acos(1-drop/(2*R)) if drop<2*R else math.pi/2
    aa=np.linspace(0,alpha,math.ceil(R*alpha/step)+1)
    c=bottom-2*R*math.sin(alpha)*h+drop*up
    first=c+R*np.sin(aa)[:,None]*h-R*(1-np.cos(aa))[:,None]*up
    vertical=line(first[-1],first[-1]-max(0.,drop-2*R)*up)
    back=aa[::-1]
    second=vertical[-1]+R*(math.sin(alpha)-np.sin(back))[:,None]*h-R*(np.cos(back)-math.cos(alpha))[:,None]*up
    final=bottom+R*np.sin(tt)[:,None]*h+R*(1-np.cos(tt))[:,None]*up
    assert np.linalg.norm(second[-1]-bottom)<1e-8
    return np.vstack([first,vertical[1:],second[1:],final[1:]]),2*R*alpha+max(0.,drop-2*R)+R*math.pi/2

for endpoint in [r for r in functions if r['id']=='P_J9_3']:
    p=np.array(endpoint['native_exit_mm']);port=endpoint['port'];ident=endpoint['id']
    assert np.allclose(endpoint['native_axis'],up)
    for lead in [5.]:
        a=p+lead*up;stem=line(p,a)
        hit=ctx.clear(stem,ignore=['Plug_'+port],radius=OD/2) or peers(stem,0.)
        if hit:hitcount(hit);continue
        top=a[2]+R;entries=[]
        for angle in range(0,360,15):
            h=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
            arc=a+R*(1-np.cos(tt))[:,None]*h+R*np.sin(tt)[:,None]*up
            hit=ctx.clear(arc,chord_error=err,radius=OD/2) or peers(arc,err);entry_checks+=1
            if hit:hitcount(hit)
            else:entries.append((angle,h,arc))
        for slot in [3,4,5]:
            angle=math.radians(angles[slot]);q=np.array([10.6*math.cos(angle),10.6*math.sin(angle),Z])
            exits=[];good=[]
            for az in range(0,360,10):
                h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
                section=exit_section(q,h,top)
                if section is None:continue
                curve,length=section
                hit=ctx.clear(curve,chord_error=err,radius=OD/2) or peers(curve,err);exit_checks+=1
                if hit:hitcount(hit)
                else:exits.append((az,h,curve,length))
            for ea,eh,entry in entries:
                if len(good)>=24:break
                for xa,xh,exit_curve,exit_length in exits:
                    if len(good)>=24:break
                    for radius in [7.,9.]:
                        if len(good)>=24:break
                        for plan in paths(entry[-1,:2],eh[:2],exit_curve[0,:2],xh[:2],radius,step):
                            if len(good)>=24:break
                            trials+=1
                            if plan['analytic_length_mm']>160:continue
                            xy=plan['points_xy_mm']
                            if np.max(np.linalg.norm(xy,axis=1))>75:continue
                            middle=np.c_[xy,np.full(len(xy),top)]
                            hit=ctx.clear(middle,chord_error=plan['chord_error_mm'],radius=OD/2) or peers(middle,plan['chord_error_mm'])
                            if hit:hitcount(hit);continue
                            full=np.vstack([stem,entry[1:],middle[1:],exit_curve[1:]])
                            good.append(dict(endpoint=ident,port=port,pin=endpoint['pin'],slot=slot,
                                lead_mm=lead,entry_deg=ea,exit_deg=xa,plane_z_mm=top,
                                minimum_centerline_radius_mm=R,planar_radius_mm=radius,
                                analytic_length_mm=lead+R*math.pi/2+plan['analytic_length_mm']+exit_length,
                                chord_error_mm=max(err,plan['chord_error_mm']),family=plan['family'],points=full))
            key=f'{ident}_slot{slot}_lead{lead:g}'
            selected=sorted(good,key=lambda r:r['analytic_length_mm'])[:12]
            for n,row in enumerate(selected):
                cid=key+f'_{n}';row['id']=cid;curves[cid]=row.pop('points')
            pools[key]=selected
            print('POWER_PREFIX_POOL',key,'entry',len(entries),'exit',len(exits),'found',len(good),'kept',len(selected),flush=True)
ctx.targets=native;ctx.assert_unchanged()
for p,h in source_hashes.items():assert sha(PROJECT/p)==h,p
np.savez_compressed(OUT/'body_prefix_candidates.npz',**curves)
report=dict(status='PASS' if curves else 'BLOCKED',scope='Finite R7/R9/R12 body-prefix pool against current native solids at zero pose only; unselected Alpha2622 reference',
    sources=ctx.sources,inputs=source_hashes,pools=pools,fail_counts=dict(fail),first_witness=witness,
    entry_checks=entry_checks,exit_checks=exit_checks,planar_trials=trials,peer_checks=peer_checks,
    curve_sha256=sha(OUT/'body_prefix_candidates.npz'),script_sha256=sha(Path(__file__)),
    OD_mm=OD,radius_mm=R,gap_mm=.3,neck_entry_z_mm=Z,
    pool_scope='Bounded first24 valid options per pin/slot/lead, keep12 shortest from this finite pool; not global optimization',
    all_routes_impossible=False,wire_selection='BLOCKED',motion='NOT_TESTED',wire_wire='NOT_TESTED',
    full_endpoints='BLOCKED',supplier_cut_lengths_released=False,main_changed=False,elapsed_s=time.time()-started)
(OUT/'body_prefix_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('POWER_PREFIX_DONE',report['status'],len(curves),'seconds',report['elapsed_s'],flush=True)
