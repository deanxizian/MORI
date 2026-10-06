#!/usr/bin/env python3
"""MORI V1.2 offline sensitivity model. NOT a motor rating or robot qualification.
Run with hardware/.venv-v1/bin/python. Reads mechanical results, never edits them.
"""
from pathlib import Path
import json, math, hashlib, csv
import numpy as np
from scipy.linalg import solve_continuous_are

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'hardware/v1_2/reports'; OUT.mkdir(exist_ok=True)
G=9.80665
geom=json.loads((ROOT/'config/geometry.json').read_text())
massfile=ROOT/'mechanical/reports/mass_budget.json'
items=json.loads(massfile.read_text())['density_and_component_mass_assumptions']
R=geom['wheel_diameter_mm']/2000
JOINT=np.array([0.,0.,geom['ground_clearance_mm']+geom['body_diameter_mm']-geom['body_top_cut_depth_mm']-geom['head_embedding_depth_mm']+geom['head_diameter_mm']/2])/1000
AXLE_Z=R

def parallel(m,c):
    return m*(np.dot(c,c)*np.eye(3)-np.outer(c,c))

def rotation(axis,angle):
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return np.array([[1,0,0],[0,c,-s],[0,s,c]]) if axis=='x' else np.array([[c,-s,0],[s,c,0],[0,0,1]])

def aggregate(records):
    m=sum(t[0] for t in records); c=sum(t[0]*t[1] for t in records)/m
    return m,c,sum(t[2]+parallel(t[0],t[1]-c) for t in records)

def build(scenario,pitch=0,yaw=0):
    # Mechanical records already include estimated components. Scale uncertain
    # material/other components, not the two vendor-documented actuator masses.
    sf={'light':.75,'nominal':1.,'heavy':1.35}[scenario]
    rec=[]; wheel=[]; head=[]; yaw_head=[]
    rot=rotation('z',yaw)@rotation('x',pitch)
    for a in items:
        m=a['mass_g']/1000; c=np.array(a['com_mm'])/1000
        I=np.array(a['raw_inertia_g_mm2'])*1e-9-parallel(m,c)
        if np.linalg.eigvalsh(I).min() < -1e-8: raise ValueError(('inertia not about world origin?',a['id']))
        fixed=a['id'] in ['Drive_Motor_L','Drive_Motor_R','Yaw_Servo','Pitch_Servo']
        scale=1. if fixed else sf
        m*=scale; I*=scale
        if a['group']=='pitch': c=JOINT+rot@(c-JOINT);I=rot@I@rot.T;head.append((m,c,I))
        elif a['group']=='yaw':
            rz=rotation('z',yaw);c=JOINT+rz@(c-JOINT);I=rz@I@rz.T
        if a['group'] in ['pitch','yaw']:yaw_head.append((m,c,I))
        target=wheel if a['group'].startswith('wheel_') else rec
        target.append((m,c,I))
    # Explicit design contingency for revised power board, wires and connectors;
    # not secretly counted as a measured component or replacing 190 g battery.
    extra={'light':.05,'nominal':.09,'heavy':.16}[scenario]
    rec.append((extra,np.array([0.,-.02,.125]),np.diag([1,1,1])*extra*.02**2/12))
    mb,cb,Ib=aggregate(rec);mw,cw,Iw=aggregate(wheel);mt,ct,It=aggregate(rec+wheel)
    # Wheel rotation is about +X; remove lateral position and use individual COMs.
    Jw=sum(t[2][0,0]+t[0]*((t[1][1])**2+(t[1][2]-AXLE_Z)**2) for t in wheel)
    hp=aggregate(head)
    pitch_axis=rotation('z',yaw)@np.array([1.,0.,0.])
    head_gravity_torque=np.cross(hp[1]-JOINT,np.array([0.,0.,-hp[0]*G]))
    head_joint_inertia=hp[2]+parallel(hp[0],hp[1]-JOINT)
    yh=aggregate(yaw_head)
    yaw_joint_inertia=yh[2]+parallel(yh[0],yh[1]-JOINT)
    yaw_gravity=[]
    for lean in [-10,0,10]:
        rb=rotation('x',-lean)
        torque=np.cross(rb@(yh[1]-JOINT),np.array([0.,0.,-yh[0]*G]))
        yaw_gravity.append(abs(float((rb@np.array([0.,0.,1.]))@torque)))
    p={'body_mass':mb,'total_mass':mt,'wheel_mass':mw,'l':cb[2]-AXLE_Z,
       'Jbody':Ib[0,0],'Jwheels':Jw,'center_m':ct.tolist(),'body_center_m':cb.tolist(),
       'inertia_COM_kg_m2':It.tolist(),'head_pitch_mass':hp[0],
       'head_pitch_gravity_Nm':abs(float(pitch_axis@head_gravity_torque)),
       'head_pitch_inertia_joint':float(pitch_axis@head_joint_inertia@pitch_axis),
       'head_yaw_mass':yh[0],'head_yaw_inertia_joint':float(yaw_joint_inertia[2,2]),
       'head_yaw_gravity_at_up_to_10deg_body_lean_Nm':max(yaw_gravity)}
    assert p['l']>0 and mb>0 and Jw>0
    return p

def plant(p,th=0):
    return np.array([[p['total_mass']+p['Jwheels']/R**2,p['body_mass']*p['l']*math.cos(th)],
      [p['body_mass']*p['l']*math.cos(th),p['Jbody']+p['body_mass']*p['l']**2]])

def gain(p):
    h=np.linalg.inv(plant(p));A=np.zeros((4,4));A[0,1]=A[2,3]=1
    A[[1,3],2]=h@np.array([0,p['body_mass']*G*p['l']])
    B=np.zeros((4,1)); B[[1,3],0]=h@np.array([1/R,-1])
    P=solve_continuous_are(A,B,np.diag([2,1,160,3]),np.array([[1.]]))
    K=(B.T@P)[0]
    assert max(np.linalg.eigvals(A-B@K[None,:]).real)<0
    return K

def simulate(p,limit,delay_ms,lag_ms,deadband,theta0,voltage=8.5):
    # LQR is only a reproducible diagnostic controller; do not copy gains to firmware.
    k=gain(p);dt=.001; state=np.array([0.,0.,math.radians(theta0),0.])
    fifo=[0.]*round(delay_ms/2);held=0.;tau=0.;data=[];saturated=0
    vmax=16.5*voltage/12*R # ASSUMED linear no-load scaling, not vendor low-voltage curve.
    reason=None
    for n in range(3000):
        if n%2==0:
            raw=-float(k@state)
            # ASSUMED linear torque/speed derating of a hypothesized continuous ceiling.
            available=2*limit*max(0.,1-abs(state[1])/vmax)
            saturated+=abs(raw)>available
            cmd=float(np.clip(raw,-available,available)); fifo.append(cmd);held=fifo.pop(0)
            held=math.copysign(max(0.,abs(held)-2*deadband),held)
        tau+=(held-tau)*min(1.,dt/(lag_ms/1000))
        def rhs(s):
            _,v,t,w=s
            f=p['body_mass']*p['l']*w*w*math.sin(t)-.08*math.tanh(v/.015)-.04*v
            a=np.linalg.solve(plant(p,t),[tau/R+f,p['body_mass']*G*p['l']*math.sin(t)-tau-.0002*w])
            return np.array([v,a[0],w,a[1]])
        a=rhs(state); b=rhs(state+.5*dt*a); state+=dt*b
        data.append([n*dt,*state,tau])
        if abs(state[2])>math.radians(30):reason='tilt_over_30deg';break
        if abs(state[1])>vmax:reason='speed_over_assumed_no_load';break
    d=np.array(data);tail=d[d[:,0]>2]
    passed=reason is None and len(tail)>0 and abs(tail[:,3]).max()<math.radians(2) and abs(tail[:,2]).max()<.1
    return dict(limit_Nm_per_wheel=limit,delay_ms=delay_ms,lag_ms=lag_ms,deadband_Nm_per_wheel=deadband,
      initial_tilt_deg=theta0,assumed_motor_voltage=voltage,criterion_met=bool(passed),stop_reason=reason,
      peak_tilt_deg=round(float(abs(d[:,3]).max()*180/math.pi),2),peak_speed_m_s=round(float(abs(d[:,2]).max()),3),
      saturation_fraction=round(saturated/((n//2)+1),3),travel_m=round(float(abs(d[:,1]).max()),3)),d

def main():
    poses=[(-20,-60),(0,0),(25,60)]
    scenarios={s:[dict(pitch_deg=p,yaw_deg=y,**build(s,p,y)) for p,y in poses] for s in ['light','nominal','heavy']}
    sims=[]; examples={}
    for s in scenarios:
        p=build(s)
        for lim in [.06,.12,.24]:
            for delay in [2,10,25]:
                for tilt in [5,10]:
                    a,d=simulate(p,lim,delay,6,.006,tilt);a['scenario']=s;sims.append(a)
                    if s=='nominal' and lim==.12 and tilt==10:examples[delay]=d
    # Additional friction / backlash surrogate sensitivity. These are NOT measured gear data.
    for lag,dead in [(15,.015),(30,.03)]:
        a,_=simulate(build('heavy'),.12,10,lag,dead,10);a['scenario']='heavy_extra_reversal_loss';sims.append(a)
    nm=build('nominal');head=[]
    for s,rows in scenarios.items():
        for p in rows:
            # alpha5rad/s², cable+friction0.01..0.04Nm are test hypotheses.
            for cable in [.01,.04]:
                demand=p['head_pitch_gravity_Nm']+p['head_pitch_inertia_joint']*5+cable
                yaw_demand=p['head_yaw_gravity_at_up_to_10deg_body_lean_Nm']+p['head_yaw_inertia_joint']*5+cable
                head.append(dict(scenario=s,pitch_deg=p['pitch_deg'],yaw_deg=p['yaw_deg'],cable_friction_Nm=cable,
                   acceleration_rad_s2=5,total_pitch_Nm=demand,vendor_2020_A0_rated_Nm_at6V=.75*.0980665,conservative_4p8V_rated_Nm=.65*.0980665,
                   rated_ratio=(.65*.0980665)/demand,total_yaw_Nm_at_up_to_10deg_body_lean=yaw_demand,
                   yaw_rated_ratio=(.65*.0980665)/yaw_demand,version_match='NOT_TESTED'))
    # Per-state rail-output powers. Deliberately input hypotheses, not nameplate averages.
    states={'balance':[4.,.5,2.0],'moving':[7.,.7,2.0],'disturbance_peak':[22.,2.,3.],
       'head_motion':[5.,4.8,2.0],'display_on':[4.,.5,2.7],'vision_tracking':[5.,1.,4.0],
       'audio_record_play':[5.,.8,5.0],'network_tx':[5.,.5,4.5],'concurrent_peak':[30.,12.,10.],
       'maintenance_charge':[0.,0.,2.]}
    power=[]
    for name,(w,h,l) in states.items():
        batt=w/.88+h/.88+l/.9+.5 # includes motion/IMU and converter quiescent contingency
        power.append(dict(state=name,wheel_W=w,head6V_W=h,interaction5V_W=l,battery_W=round(batt,2),
          battery_A_at_9p9V=round(batt/9.9,2),status='ASSUMED_NOT_TESTED',efficiency_wheel=.88,efficiency_head=.88,efficiency_logic=.9))
    energies=[dict(capacity_mAh=cap,nominal_Wh=11.1*cap/1000,usable_Wh=11.1*cap/1000*.8,
       max_average_input_W_for_60min_with_15percent_reserve=11.1*cap/1000*.8*.85,
       average_input_W=pw,estimated_minutes=60*11.1*cap/1000*.8*.85/pw)
       for cap in [2200,2600] for pw in [8.,12.,18.,25.]]
    # Regeneration budget, all kinetic + fall potential assumed electrically returned.
    massmax=build('heavy');E=.5*(massmax['total_mass']+massmax['Jwheels']/R**2)*.5**2
    E+=massmax['body_mass']*G*massmax['l']*(1-math.cos(math.radians(30)))
    E+=.5*(massmax['Jbody']+massmax['body_mass']*massmax['l']**2)*3**2
    regen=dict(assumed_worst_speed_m_s=.5,assumed_pitch_rate_rad_s=3,tilt_deg=30,energy_J=E,
       doubled_design_pulse_J=2*E,cap_uF=1000,cap_energy_9p5_to_10p8V_J=.5*.001*(10.8**2-9.5**2),
       dump_ohm=5.6,dump_power_at_10p8V_W=10.8**2/5.6,pulse_seconds=2*E/(10.8**2/5.6),
       note='No capacitor/TVS-only solution. External pulse-rated resistor and analog brake required; no indefinitely sustained backdrive guarantee.')
    # Outer bearing at39mm, wheel center68; inner at33. Simplified static+3g shock.
    radial=massmax['total_mass']*G/2;over=.029;span=.006
    bearing=dict(static_load_per_wheel_N=radial,outer_reaction_N=radial*(span+over)/span,
       inner_reaction_N=-radial*over/span,three_g_outer_N=3*radial*(span+over)/span,
       shaft_4mm_static_bending_MPa=32*radial*over/(math.pi*.004**3)/1e6,
       shaft_4mm_3g_bending_MPa=3*32*radial*over/(math.pi*.004**3)/1e6,
       status='CALCULATED_REQUIREMENT; bearing rating, shaft grade, press fit and printed supports NOT_QUALIFIED')
    speeds=[dict(speed_m_s=v,wheel_rad_s=v/R,wheel_rpm=v/R*60/(2*math.pi),
       output_encoder_counts_s=v/R/(2*math.pi)*8192) for v in [.1,.3,.5]]
    report=dict(status='HOST_CALCULATION_ONLY',mechanical_mass_sha256=hashlib.sha256(massfile.read_bytes()).hexdigest(),
      geometry_revision=geom['revision'],assumptions={'mass_scale_uncertain':[.75,1,1.35],'extra_power_wiring_mass_g':[50,90,160],'power_mechanical_relayout_required':True,
       'inertia':'raw inertia is about world origin; parallel-axis removed before rigid transforms; published precision is computational, not measured',
       'balance_equations':'[M+Jw/r², m*l*cos(theta); m*l*cos(theta), Jb+m*l²] [xdd,thetadd] = [tau/r+m*l*thetad²*sin(theta)-friction, m*g*l*sin(theta)-tau-damping]',
       'torque_port':'tau is summed physical wheel torque in SI; Unitree command conversion must be empirically identified',
       'controller':'offline LQR diagnostic only, not production firmware gains','head_joint_m':JOINT.tolist(),
       'exclusions':'floor compliance, pitch/yaw cross coupling, gearbox elasticity, IMU noise and time-varying cable routing not fully modeled'},
      scenarios=scenarios,wheel_speeds=speeds,output_encoder='8192 distinct states/rev; absolute encoder, NOT A/B quadrature x4',
      printing={'PLA_robot_g':sum(a['mass_g'] for a in items if a['assumption'].startswith('PLA')),
        'PLA_with_35percent_process_waste_g':1.35*sum(a['mass_g'] for a in items if a['assumption'].startswith('PLA')),
        'process_waste_fraction_assumed':.35,'cradle_and_trial_print_mass_g':None,
        'note':'Robot volume-based estimate only, not slicer or purchase weight. Cradle/trial coupons and minimum spool purchase still need pricing. Tyres remain separate; no double-counted TPU.'},
      simulations=sims,head_loads=head,power_states=power,energy=energies,regen=regen,bearing=bearing,
      conclusion='Continuous S288 torque remains unknown. Simulation success is conditional and is not evidence that S288 can supply the hypothesized torque or that MORI stands.')
    (OUT/'engineering_model.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for fn,rows in [('balance_sweep.csv',sims),('power_states.csv',power),('energy_sweep.csv',energies),('head_loads.csv',head)]:
        with (OUT/fn).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    for delay,d in examples.items():axes[0].plot(d[:,0],d[:,3]*180/math.pi,label=f'{delay} ms delay');axes[1].plot(d[:,0],d[:,2])
    axes[0].set_ylabel('Body tilt (deg)');axes[1].set_ylabel('Speed (m/s)');axes[1].set_xlabel('Time (s)')
    axes[0].legend();fig.suptitle('MORI V1.2 - assumed 0.12 Nm/wheel, 10 deg release\nSensitivity only - NOT a robot test')
    for a in axes:a.grid(alpha=.25)
    fig.tight_layout();fig.savefig(OUT/'balance_sensitivity.png',dpi=170);plt.close(fig)
    print(json.dumps({'masses_kg':{s:round(build(s)['total_mass'],2) for s in scenarios},'simulation_cases':len(sims),
        'conditional_criteria_met':sum(x['criterion_met'] for x in sims),'regen_design_J':round(2*E,3),'physical_tests':'NOT_TESTED'},indent=2))

if __name__=='__main__':main()
