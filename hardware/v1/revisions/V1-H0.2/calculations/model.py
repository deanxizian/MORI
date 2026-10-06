#!/usr/bin/env python3
"""Reproducible requirement envelope, NOT a qualified motor or standing test.
Run from any cwd. Inputs: V1 mechanical mesh moments + dated candidate register.
"""
import csv, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.linalg import solve_continuous_are
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'hardware/v1/reports'
G=9.80665
GEOM=json.loads((ROOT/'config/geometry.json').read_text())
MASS=json.loads((ROOT/'mechanical/reports/mass_budget.json').read_text())
MBOM={r['id']:r for r in json.loads((ROOT/'mechanical/reports/bom.json').read_text())}
BOM=json.loads((ROOT/'hardware/v1/bom_candidates.json').read_text())
if BOM.get('revision') != 'V1-H0.1':
    raise SystemExit('H0.1 model has explicit historical motor/mass inputs. Refusing to present them as the new BOM. Use procurement/calculation_checks.json for H0.2 screening; rebuild the physical model after placement/mass inputs are frozen.')
R=GEOM['wheel_diameter_mm']/2000
BODY_Z=GEOM['body_diameter_mm']/2+GEOM['ground_clearance_mm']
HEAD_Z=BODY_Z+GEOM['body_diameter_mm']/2-GEOM['body_top_cut_depth_mm']+GEOM['head_diameter_mm']/2-GEOM['head_embedding_depth_mm']
PIVOT=np.array([0,0,HEAD_Z/1000])

def dump(name,data):
    def convert(o):
        if isinstance(o,np.ndarray):return o.tolist()
        if isinstance(o,np.generic):return o.item()
        raise TypeError(type(o).__name__)
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=convert,allow_nan=False)+'\n')

def parallel(m,p):return m*(np.dot(p,p)*np.eye(3)-np.outer(p,p))
def box_inertia(m,xyz):
    x,y,z=np.array(xyz)/1000
    return np.diag([m*(y*y+z*z)/12,m*(x*x+z*z)/12,m*(x*x+y*y)/12])
def rot(yaw,pitch):
    y,p=map(math.radians,(yaw,pitch));cy,sy,cp,sp=math.cos(y),math.sin(y),math.cos(p),math.sin(p)
    return np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]]) @ np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])

def base_items():
    out=[]
    for a in MASS['density_and_component_mass_assumptions']:
        m=a['mass_g']/1000;p=np.array(a['com_mm'])/1000
        # Raw mechanical tensor is about assembly-ground origin (g mm² -> kg m²).
        j=np.array(a['raw_inertia_g_mm2'])*1e-9-parallel(m,p)
        assert np.linalg.eigvalsh(j).min()>-1e-9,(a['id'],'invalid raw tensor origin')
        out.append(dict(id=a['id'],group=a['group'],m=m,p=p,j=j,
                        printed=MBOM[a['id']]['category']=='PRINTABLE',basis=a.get('assumption','mechanical placeholder')))
    return out

def combine(items):
    mass=sum(a['m'] for a in items)
    p=sum((a['p']*a['m'] for a in items),np.zeros(3))/mass
    j=sum((a['j']+parallel(a['m'],a['p']-p) for a in items),np.zeros((3,3)))
    return dict(mass_kg=mass,com_m=p,inertia_COM_kg_m2=j)

def scenario(label,scale,harness,pcb,other):
    a=base_items()
    # Remove duplicate split display proxies; use one assembled module mass estimate.
    a=[i for i in a if i['id'] not in ('Display_PCB','Display_Connector')]
    replace={'Drive_Motor_L':96,'Drive_Motor_R':96,'Battery':99,'Yaw_Servo':12.5,
      'Pitch_Servo':12.5,'MCU_Motion':3,'MCU_Interaction':3,'Body_IMU':1.7,
      'Display_Module':15,'Speaker':6,'Audio_Amp':4,'Motor_Driver':6,
      'Power_Module':28,'USB_Charge':12,'Microphone':1}
    for i in a:
        ratio=scale if i['printed'] else (1+(scale-1)*.65)
        if i['id'] in replace:
            ratio=(replace[i['id']]/1000)/i['m']
            i['basis']='Vendor nominal where published; otherwise explicit candidate mass assumption. Inertia uses allocation shape, not measured part.'
        i['m']*=ratio;i['j']*=ratio
    for name,grams,p,xyz in [('Harness',harness,[0,0,115],[90,75,80]),('Carrier_PCB',pcb,[0,0,127],[96,76,1.6]),('Unallocated_protection_connectors',other,[0,-25,105],[60,20,20])]:
        m=grams/1000
        a.append(dict(id=name,group='body',m=m,p=np.array(p)/1000,j=box_inertia(m,xyz),printed=False,basis='ASSUMED added budget; not present in mechanical placeholders'))
    return a

def pose(items,yaw,pitch):
    out=[]
    for item in items:
        a=dict(item)
        if a['group'] in ('pitch','yaw'):
            q=rot(yaw,pitch if a['group']=='pitch' else 0)
            a['p']=PIVOT+q@(a['p']-PIVOT);a['j']=q@a['j']@q.T
        out.append(a)
    return out

def parameters(items):
    b=combine([i for i in items if not i['group'].startswith('wheel')])
    w=combine([i for i in items if i['group'].startswith('wheel')])
    # The wheel axle is X; sum each spinning item's COM inertia and local axle offset.
    jw=sum(i['j'][0,0]+i['m']*(i['p'][1]**2+(i['p'][2]-R)**2) for i in items if i['group'].startswith('wheel'))
    l=b['com_m'][2]-R
    # Lateral/forward COM offsets require trim; small-angle model uses measured vertical l.
    return dict(body_mass=b['mass_kg'],wheel_mass=w['mass_kg'],l=l,
                Jbody=b['inertia_COM_kg_m2'][0,0],Jwheels=jw,
                total_mass=b['mass_kg']+w['mass_kg'],forward_COM=b['com_m'][1])

def plant_terms(p,theta=0):
    m,l=p['body_mass'],p['l']
    return np.array([[p['total_mass']+p['Jwheels']/R**2,m*l*math.cos(theta)],
                     [m*l*math.cos(theta),p['Jbody']+m*l*l]])

def gain(p):
    h=plant_terms(p);ainv=np.linalg.inv(h)
    A=np.zeros((4,4));A[0,1]=1;A[2,3]=1
    A[[1,3],2]=ainv@np.array([0,p['body_mass']*G*p['l']])
    B=np.zeros((4,1));B[[1,3],0]=ainv@np.array([1/R,-1])
    Q=np.diag([2,1,160,3]);RR=np.array([[1.]])
    P=solve_continuous_are(A,B,Q,RR)
    K=np.linalg.solve(RR,B.T@P)
    assert np.max(np.real(np.linalg.eigvals(A-B@K)))<0
    return K[0]

def simulate(p,k,limit_per_wheel,delay_ms,theta0=10,deadband_nm=.008,lag_ms=6):
    dt=.0005;period=.002;steps=int(3/dt);delay=max(0,int(delay_ms/1000/period))
    commands=[0.]*delay;state=np.array([0.,0.,math.radians(theta0),0.]);tau=0.;held=0.
    times=[];data=[];sat=0;cmd_peak=0.;failed=False;fail_reason=None
    def deriv(s,t):
        _,v,th,w=s;m,l=p['body_mass'],p['l']
        force=m*l*w*w*math.sin(th)-.08*math.tanh(v/.015)-.04*v
        rhs=np.array([t/R+force,m*G*l*math.sin(th)-t-.0002*w])
        ac=np.linalg.solve(plant_terms(p,th),rhs)
        return np.array([v,ac[0],w,ac[1]])
    for n in range(steps):
        if n%4==0:
            raw=-float(k@state);cmd_peak=max(cmd_peak,abs(raw)/2)
            lim=2*limit_per_wheel
            sat+=abs(raw)>lim
            cmd=float(np.clip(raw,-lim,lim));commands.append(cmd);held=commands.pop(0)
            # Conservative friction/gear reversal loss model, not a measured FIT0521 deadband.
            held=math.copysign(max(0,abs(held)-2*deadband_nm),held)
        tau+=(held-tau)*min(1,dt/(lag_ms/1000))
        a=deriv(state,tau);b=deriv(state+dt*a/2,tau);c=deriv(state+dt*b/2,tau);d=deriv(state+dt*c,tau)
        state+=dt*(a+2*b+2*c+d)/6
        if n%20==0:times.append(n*dt);data.append(state.copy())
        if abs(state[2])>math.radians(30):failed=True;fail_reason='tilt_over_30deg';break
        if abs(state[1])>.8:failed=True;fail_reason='wheel_speed_over_0.8m_s';break
    data=np.array(data);tail=data[np.array(times)>2]
    recovered=not failed and len(tail)>0 and np.max(np.abs(tail[:,2]))<math.radians(2) and np.max(np.abs(tail[:,1]))<.1
    result=dict(per_wheel_limit_Nm=limit_per_wheel,delay_ms=delay_ms,actuator_lag_ms=lag_ms,
        assumed_deadband_per_wheel_Nm=deadband_nm,initial_tilt_deg=theta0,
        criterion_met=bool(recovered),stopped=failed,stop_reason=fail_reason,
        max_tilt_deg=float(np.max(np.abs(data[:,2]))*180/math.pi),
        max_speed_m_s=float(np.max(np.abs(data[:,1]))),travel_m=float(np.max(np.abs(data[:,0]))),
        saturation_fraction=sat/max(1,(n//4+1)),unlimited_command_peak_per_wheel_Nm=cmd_peak,
        end_tilt_deg=float(state[2]*180/math.pi))
    return result,np.array(times),data

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    # Independent conservation check against mechanical aggregate, before candidate substitutions.
    orig=combine(base_items());expected=MASS['totals']['whole_robot']
    assert abs(orig['mass_kg']*1000-expected['mass_g_rounded'])<6
    assert np.max(np.abs(orig['inertia_COM_kg_m2']-np.array(expected['inertia_at_COM_kg_m2'])))<6e-8
    scenarios={k:scenario(k,*values) for k,values in {'light':(.8,35,25,10),'medium':(1.,55,35,20),'heavy':(1.3,85,50,35)}.items()}
    mass_results=[];head=[];sims=[];example=[]
    for name,items in scenarios.items():
        for yaw,pitch in [(0,0),(-60,-20),(60,25),(0,25),(0,-20)]:
            moved=pose(items,yaw,pitch);pars=parameters(moved)
            result=dict(case=name,yaw_deg=yaw,pitch_deg=pitch,whole=combine(moved),body=combine([i for i in moved if not i['group'].startswith('wheel')]),parameters=pars)
            mass_results.append(result)
            hp=[i for i in moved if i['group']=='pitch'];hy=[i for i in moved if i['group'] in ('pitch','yaw')]
            hp_mass=combine(hp)
            # Pitch axis rotates with yaw. Use vector gravity torque projected onto that axis.
            axis=rot(yaw,0)@np.array([1,0,0])
            jx=sum(axis@(i['j']+parallel(i['m'],i['p']-PIVOT))@axis for i in hp)
            jy=sum((i['j']+parallel(i['m'],i['p']-PIVOT))[2,2] for i in hy)
            hy_mass=combine(hy);loads=[]
            for lean in [-10,0,10]:
                gravity_body=rot(0,-lean).T@np.array([0,0,-G])
                tp=abs(np.dot(np.cross(hp_mass['com_m']-PIVOT,hp_mass['mass_kg']*gravity_body),axis))
                ty=abs(np.cross(hy_mass['com_m']-PIVOT,hy_mass['mass_kg']*gravity_body)[2])
                loads.append(dict(body_forward_lean_deg=lean,pitch_gravity_Nm=tp,yaw_gravity_Nm=ty))
            tgrav=max(v['pitch_gravity_Nm'] for v in loads);ygrav=max(v['yaw_gravity_Nm'] for v in loads)
            head.append(dict(case=name,yaw_deg=yaw,pitch_deg=pitch,pitch_mass_g=hp_mass['mass_kg']*1000,
                gravity_pitch_Nm=tgrav,pitch_required_Nm=tgrav+jx*math.radians(60)+.008,
                yaw_required_Nm=ygrav+jy*math.radians(60)+.010,body_lean_sensitivity=loads,
                note='body lean +/-10deg;60deg/s² + assumed cable/bearing resistance .008 pitch/.010 yaw Nm; neither resistance nor 5V servo continuous torque measured'))
        p=parameters(items);k=gain(p)
        for limit in [.05,.10,.20]:
            for delay in [2,10,30]:
                res,t,states=simulate(p,k,limit,delay)
                res.update(case=name,gains_SI_ideal_plant=k.tolist(),voltage_condition='torque cap parameter only; not a measured motor map')
                sims.append(res)
                if name=='medium' and limit==.1:example.append((delay,t,states))
    dump('mass_inertia.json',dict(status='NOT_TESTED',basis='Current V1 belt-layout mesh with FIT0521 candidate motor mass. Not a geometrically valid 4012 hub layout. Inertia proxies require Stage B update.',
        precision='Numbers retained for reproducibility; report 2 significant figures, not measured precision.',
        mechanical_origin_conservation_check='PASS',scenarios=mass_results,head_loads=head,
        component_assumptions=[dict(id=i['id'],mass_g=i['m']*1000,group=i['group'],basis=i['basis']) for i in scenarios['medium']]))
    dump('dynamics_sweep.json',dict(status='NOT_TESTED',simulation_run='PASS',model='Coupled cart/body with motor reaction torque; friction, torque saturation, actuator lag, discrete commands + transport delay; flat rigid contact. No tyre slip, belt compliance or thermal/current map.',
        acceptance='last 1s tilt<2deg & speed<0.1m/s; abort tilt>30deg or speed>.8m/s; no recovery/standing claim',runs=sims))
    fig,ax=plt.subplots(2,1,figsize=(8,5),sharex=True)
    for delay,t,s in example:ax[0].plot(t,np.degrees(s[:,2]),label=f'{delay} ms');ax[1].plot(t,s[:,1],label=f'{delay} ms')
    ax[0].set(ylabel='Body tilt (deg)',title='ASSUMED medium body, 0.10 Nm/wheel cap — simulation only');ax[1].set(xlabel='Time (s)',ylabel='Axle speed (m/s)');ax[0].legend();fig.tight_layout();fig.savefig(OUT/'delay_sensitivity.png',dpi=160);plt.close(fig)

    budgets={}
    for route in ['FOC','BRUSH']:
        selected=[r for r in BOM['items'] if r['route'] in ['COMMON',route]]
        sums={c:sum(r['quantity']*r['unit_price'] for r in selected if r['currency']==c and r['unit_price'] is not None) for c in ['CNY','USD','EUR']}
        known=sum(sums[c]*BOM['fx_cny_per_unit'][c] for c in sums)
        unknown=[r['id'] for r in selected if r['unit_price'] is None]
        allowances=sum(r['quantity']*(r['planning_unit_allowance_cny'] or 0) for r in selected if r['unit_price'] is None)
        budgets[route]=dict(public_list_subtotals=sums,assumed_fx_known_subtotal_cny=round(known,2),
            unknown_cost_rows=unknown,unknown_count=len(unknown),full_quote_coverage=False,
            remaining_to_900_cny=round(900-known,2),remaining_to_1000_cny=round(1000-known,2),
            scenario_with_unquoted_allowances_cny=round(known+allowances,2),
            scenario_over_900_cny=round(max(0,known+allowances-900),2),
            scenario_over_1000_cny=round(max(0,known+allowances-1000),2),
            conclusion='BLOCKED: landed price/unknowns' if known<1000 else 'FAIL under stated FX even before unquoted costs')
    dump('budget.json',dict(status='BLOCKED',fx=BOM['fx_cny_per_unit'],fx_note=BOM['fx_status'],routes=budgets,
        exchange_sensitivity={'FOC_low_USD6.8_EUR7.6':round(budgets['FOC']['public_list_subtotals']['CNY']+budgets['FOC']['public_list_subtotals']['USD']*6.8+budgets['FOC']['public_list_subtotals']['EUR']*7.6,2),
                             'FOC_high_USD7.5_EUR8.4':round(budgets['FOC']['public_list_subtotals']['CNY']+budgets['FOC']['public_list_subtotals']['USD']*7.5+budgets['FOC']['public_list_subtotals']['EUR']*8.4,2)}))

    # Absolute simultaneous load states; never sum these rows as if independent deltas.
    state_inputs=[('stand_eyes',2.0,.33,.9,.15,.15),('move_eyes',4,.33,.9,.15,.15),('disturbance',14,.45,1.2,.3,.15),
      ('turn_two_servos',2,.33,.9,4.0,.15),('vision_tracking',2,.33,1.5,.2,.15),('record_play_network',2,.33,1.8,.2,.55),
      ('maintenance_logic',0,.25,1.2,0,0),('concurrent_peak',18,.60,2.31,10,1.0)]
    states=[]
    for name,wheel,motion,inter,servo,audio in state_inputs:
        # Screen .15W, camera is included in interaction allowance. battery wheel is already input W.
        pb=wheel+(motion+inter+.15)/.88+(servo+audio)/.90+.08
        states.append(dict(state=name,wheel_battery_W=wheel,motion_3V3_W=motion,interaction_including_camera_W=inter,
            screen_W=.15,servo_5V_W=servo,audio_5V_W=audio,battery_W=round(pb,3),battery_A_at_6V4=round(pb/6.4,3),status='ASSUMED_NOT_TESTED'))
    usable=7.2*3.35*.80*.90 # 80% usable charge window, 90% ageing/capacity uncertainty; DC/DC already in loads.
    endurance=[]
    # Mixed-duty representative average, includes continuous vision/eyes and 10 min movement + 10 min voice + 5% head activity.
    for name,wheelavg in [('light',2),('medium',4),('heavy',8)]:
        base=wheelavg+(.33+1.5+.15)/.88+(.2+.15)/.9+.08
        avg=base+(4-2)/6+(.55-.15)/(.9*6)+(4-.2)/.9*.05
        endurance.append(dict(case=name,mean_battery_W=round(avg,2),usable_Wh=round(usable,2),estimated_minutes=round(60*usable/avg,1),energy_margin_for_60min_Wh=round(usable-avg,2),status='NOT_TESTED'))
    energy=.5*parameters(scenarios['heavy'])['total_mass']*.5**2 + .5*parameters(scenarios['heavy'])['Jwheels']*(.5/R)**2
    regen=dict(translation_plus_wheel_energy_at_0p5ms_J=energy,minimum_C_8p4_to_8p8V_F=2*energy/(8.8**2-8.4**2),
               energy_1000uF_8p4_to_8p8V_J=.5*.001*(8.8**2-8.4**2),
               note='8.8V is an illustrative bound, NOT an approved driver or battery voltage. Add body/rotor/inductor energy; buck reverse path must be measured.')
    dump('power_energy.json',dict(status='NOT_TESTED',states=states,battery_nominal_Wh=24.12,usable_Wh=usable,endurance=endurance,
        requirements_1S_2S=dict(example_20W_battery_A_1S_3V2=20/(3.2*.85),example_20W_battery_A_2S_6V4=20/(6.4*.90),
            decision='2S conditional: halves battery current, separately regulated 5V servo and 3V3 logic. Charger/protection/balance not yet matched.'),regen=regen,
        peak_warning='Concurrent modeled peak may exceed pack 5A and safe voltage headroom; firmware cannot replace hardware current limit. Characterize and reduce allowed concurrent loads.' ))
    speeds=[dict(v_m_s=v,wheel_rpm=v/(2*math.pi*R)*60,omega_rad_s=v/R,
        encoder_count_rates_s=[v/(2*math.pi*R)*c for c in [341.2*4,11*34.02*4]]) for v in [.1,.3,.5]]
    inner=GEOM['body_diameter_mm']/2-GEOM['shell_thickness_mm']
    halfwidth=math.sqrt(inner**2-(R*1000-BODY_Z)**2)
    load=parameters(scenarios['heavy'])['total_mass']*G/2*3
    # Bearings at 26/36 mm, wheel centre at75mm. Static overhang load multiplier.
    ra=-load*(75-36)/(36-26);rb=load*(75-26)/(36-26)
    torque=.20;belt_force=torque/(GEOM['drive']['pulley_radius_mm']/1000)
    shaft_moment=load*(75-36)/1000
    dump('mechanical_drive_checks.json',dict(status='NOT_TESTED',speeds=speeds,encoder_note='Candidate counts are alternative interpretations of erroneous vendor PPR, not frozen CPR. x4 assumes 4 edges per A/B cycle.',
        low_axle_inner_full_chord_mm=2*halfwidth,note='Sphere bound only; frame/battery/cuts further reduce it. Current motors at z100mm drive via belt; do not insert two long motors at z47.5mm.',
        trial_3g_wheel_load_N=load,bearing_reactions_N=[ra,rb],belt_tangential_force_at_0p2Nm_N=belt_force,
        shaft_bending_MPa_6mm=32*shaft_moment/(math.pi*.006**3)/1e6,
        bearing_and_shaft_release='BLOCKED: exact bearing dynamic/static rating, shaft steel, belt pretension and axial retention unknown; combine belt load/vector and wheel overhang before approval.'))
    # Deliberately separate motor surrogate from accepted plant: contradictory vendor points
    # cannot identify a trustworthy continuous envelope or motor Kt.
    rm=6/3.2;omega0=210*2*math.pi/60;ke=(6-.13*rm)/omega0
    output_torque_per_amp=(10*.0980665)/(3.2-.13)
    curves=[]
    for voltage in [4.5,5.0,6.0]:
        for velocity in [0,.1,.3,.5]:
            amps=max(0,min(1.5,(voltage-ke*velocity/R)/rm))
            curves.append(dict(motor_V=voltage,speed_m_s=velocity,limited_A=amps,
                optimistic_output_Nm=max(0,(amps-.13)*output_torque_per_amp),copper_loss_W=amps*amps*rm))
    dump('motor_voltage_surrogate.json',dict(status='NOT_TESTED',fit_status='BLOCKED_INCONSISTENT_VENDOR_DATA',
        warning='Uses only stall/no-load endpoints. Effective output torque/A includes gears, is not a physical rotor Kt. Excludes gear efficiency, thermal derating, battery sag, driver loss and dynamic inductance. Never use to qualify continuous torque.',
        endpoint_assumptions=dict(R_ohm=rm,output_Ke_V_per_rad_s=ke,effective_output_Nm_per_A=output_torque_per_amp),curves=curves,
        maximum_efficiency_point_reported_mechanical_W=2,maximum_efficiency_point_T_times_omega_W=2*.0980665*170*2*math.pi/60,
        maximum_power_point_reported_W=3.1,maximum_power_point_T_times_omega_W=5.2*.0980665*110*2*math.pi/60,
        FOC_curve=None,FOC_reason='No continuous/peak data, Kv/Kt, resistance, bus-voltage range or raw-unit calibration.'))
    plastic=sum(i['m'] for i in base_items() if i['printed'])
    dump('print_material_budget.json',dict(status='NOT_TESTED',robot_printed_mass_kg=plastic,
        input_basis='mechanical mesh volume with PLA1.24g/cm3, shells98% effective fill, brackets65%; not global slicer infill percentage',
        print_support_waste_factor=1.20,cradle_and_coupons_extra_kg=.15,
        material_required_kg=plastic*1.2+.15,assumed_filament_CNY_per_kg=70,
        assumed_material_cost_CNY=(plastic*1.2+.15)*70,
        procurement_price=None,note='Cradle/coupons .15kg is an explicit allowance because their slice volume not in robot mass table. No printer ownership assumed. External printing/labour cost unknown; do not confuse material-only sensitivity with a service quote.'))
    print('CALCULATION EXECUTION PASS; hardware/thermal/runtime remain NOT_TESTED')
    for name in scenarios:
        row=next(r for r in mass_results if r['case']==name and r['yaw_deg']==0 and r['pitch_deg']==0)
        print(name,round(row['whole']['mass_kg'],2),'kg, body COM z',round(row['body']['com_m'][2]*1000,1),'mm')
    for route,v in budgets.items():print(route,'known list subtotal',v['assumed_fx_known_subtotal_cny'],'scenario',v['scenario_with_unquoted_allowances_cny'],'unknowns',v['unknown_count'])
    print('Simulation criteria met',sum(r['criterion_met'] for r in sims),'/',len(sims),'not a physical pass')

if __name__=='__main__':main()
