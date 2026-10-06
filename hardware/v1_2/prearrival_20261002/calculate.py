#!/usr/bin/env python3
"""Reproducible screening, NOT bench qualification. Python standard library only.

The first run snapshots the received mechanical/electrical calculations. Later
runs use those immutable inputs; --refresh-inputs is deliberately unsupported.
"""
from pathlib import Path
import csv, hashlib, json, math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def snapshot(source,name):
    target=HERE/'inputs'/name
    target.parent.mkdir(exist_ok=True)
    if not target.exists():target.write_bytes((ROOT/source).read_bytes())
    return json.loads(target.read_text()),{'source':source,'snapshot':str(target.relative_to(HERE)),'sha256':sha(target)}

def run():
    mech,mi=snapshot('mechanical/studies/prearrival_finish/engineering_current.json','mechanical_received.json')
    electrical,ei=snapshot('hardware/v1_2/reports/power_integrity.json','power_integrity_received.json')
    # All supplementary masses/speeds/duties below are analysis scenarios, not measured values.
    base=mech['totals']['whole']['mass_g']/1000
    out={'date':'2026-10-02','scope':'source-backed component and hypothetical load screening',
         'status':'PASS','bench':'NOT_TESTED','qualification':'BLOCKED',
         'inputs':[mi,ei],'mechanical_revision':mech['revision'],
         'mass_base_kg':base,'additional_mass_status':'ASSUMED scenario allowance; not selected part totals',
         'resistors':{},'wheel_events':[],'wire_screen':{},'fuse_screen':{},'charge_screen':{}}
    for rail,r in [('wheel',5.6),('head',10.0)]:
        v=electrical[rail];rmin=r*.95;rmax=r*1.05
        p_abs=v['absolute_motor_limit_V']**2/rmin
        p_trip=v['ovp_fault_V_range'][1]**2/rmin
        # Smaller effective capacitance and worst static threshold separation.
        c=.001*.8
        e_margin=.5*c*(v['ovp_fault_V_range'][0]**2-v['brake_on_V_range'][1]**2)
        out['resistors'][rail]={
            'ohm_nominal':r,'tolerance_fraction':.05,'ohm_range':[rmin,rmax],
            'continuous_W_at_40C_datasheet':5,'continuous_W_at_70C_datasheet':4.7,
            'P_at_brake_on_high_V_Rmin_W':v['brake_on_V_range'][1]**2/rmin,
            'P_at_OV_high_V_Rmin_W':p_trip,'P_at_motor_absolute_limit_Rmin_W':p_abs,
            'minimum_dump_current_at_on_low_V_Rmax_A':v['brake_on_V_range'][0]/rmax,
            'pulse_demands_at_absolute_limit':[
                {'duration_ms':t,'energy_J':p_abs*t/1000,'status':'NOT_TESTED'} for t in [1,10,100,500,1000]],
            'average_power_only_duty_limit_at_40C':5/p_abs,
            'average_power_only_duty_limit_at_70C':4.7/p_abs,
            'duty_limit_warning':'NOT permission for pulsed operation; separate repetitive-pulse curve and thermal checks required',
            'C_effective_F_assumed':c,'energy_between_on_high_and_OV_low_J':e_margin,
            'time_to_OV_at_regen_W_without_dump_ms':{str(p):1000*e_margin/p for p in [5,20,40]},
            'transient_margin_status':'static screening only; comparator, FET, wiring and motor dynamics NOT_TESTED'}
    # Translation plus conservative rim-like wheel rotational allowance and body descent.
    # All energy is assigned to one wheel dump, with regen fraction 1; actual losses unknown.
    for name,extra,h,rim_mass in [('light',.05,.065,.10),('middle',.15,.08,.15),('heavy',.30,.10,.20)]:
        mass=base+extra
        for speed in [.1,.3,.5]:
            translation=.5*mass*speed**2
            wheel_rotation=.5*rim_mass*speed**2
            descent=mass*9.80665*h*(1-math.cos(math.radians(20)))
            energy=translation+wheel_rotation+descent
            out['wheel_events'].append({'scenario':name,'mass_kg':mass,'supplement_kg':extra,
                'COM_height_above_axle_m_assumed':h,'speed_m_s_assumed':speed,
                'wheel_radius_m':.0525,'rpm':speed/.0525*60/(2*math.pi),'rad_s':speed/.0525,
                'translation_J':translation,'wheel_rotation_J_assumed':wheel_rotation,
                '20deg_COM_descent_J_assumed':descent,'single_dump_energy_J_assumed':energy,
                'at_10_events_per_second_mean_W_assumed':energy*10,
                'continuous_5deg_downhill_W_assumed':mass*9.80665*speed*math.sin(math.radians(5)),
                'status':'NOT_TESTED; no repeated pulse approval'})
    pitch=mech['totals']['pitch'];yaw=mech['totals']['yaw']
    pitch_I=pitch['inertia_about_pivot_kg_m2'][0][0]
    yaw_I=yaw['inertia_about_pivot_kg_m2'][2][2]
    lever=math.dist(pitch['COM_mm'],pitch['pivot_mm'])/1000
    out['head_energy']={'assumed_speed_rad_s':2,'yaw_and_pitch_rotation_J':.5*(pitch_I+yaw_I)*2**2,
       'pitch_45deg_gravity_change_bound_J':pitch['mass_g']/1000*9.80665*2*lever*math.sin(math.radians(45)/2),
       'warning':'Combined upper-bound scenario; wire, horn and unknown drive inertia/efficiency excluded; not measured regeneration.'}
    # Actual manufacturer nominal OD and full tolerance. PH contact window is not a crimp approval.
    for series,awg,od,tol,dcr in [('5852',28,.035,.004,None),('5853',26,.039,.004,38),('5854',24,.0445,.0045,22.3),('5855',22,.051,.005,14),('5856',20,.058,.004,8.7)]:
        lo,hi=(od-tol)*25.4,(od+tol)*25.4
        out['wire_screen'][series]={'AWG':awg,'OD_min_mm':lo,'OD_nom_mm':od*25.4,'OD_max_mm':hi,
          'minimum_bend_radius_at_max_OD_mm':10*hi,
          'nominal_DCR_ohm_m':dcr/304.8 if dcr else None,
          'SPH002_full_window_fit':24<=awg<=30 and lo>=.8 and hi<=1.5,
          'SPH004_full_window_fit':28<=awg<=32 and lo>=.5 and hi<=.9,
          'SXH001_full_window_fit':22<=awg<=28 and lo>=.9 and hi<=1.9,
          'H05_previous_3p56mm_trial_satisfies_wire_bend':3.561434>=10*hi,
          'crimp_and_flex_life':'NOT_TESTED'}
    out['fuse_screen']={'old_6p3A':'target only; no selected fuse or holder',
       'candidate':'Littelfuse 029707.5WXNV + 0FHM0001SXJ','rating_A':7.5,
       'fuse_VDC':32,'fuse_breaking_A_at32VDC':1000,'holder_A':20,
       'simultaneous_input_W_assumed':64.15,'low_pack_V_assumed':9.9,
       'scenario_input_A':64.15/9.9,'ratio_to_candidate_rating':(64.15/9.9)/7.5,
       'rating_adopted':False,'status':'BLOCKED',
       'reason':'No pack prospective short-circuit, overload duration, assembled wire ampacity, holder drawing or inrush record; nominal current comparison alone is insufficient.'}
    for vin in [5,9,12,15,20]:
        out['charge_screen'][str(vin)+'V']={'rear_continuous_input_limit_A':1.0,
          'efficiency_assumed':.85,'at12p6V_max_charge_A_from_power_balance':vin*.85/12.6,
          'note':'Power-balance ceiling, not guaranteed input limiting or a supported PD contract'}
    out['charge_screen']['0p5A_at12p6V_input_A']={str(v):12.6*.5/(.85*v) for v in [5,9,12,15,20]}
    out['charge_screen']['CV_12p6V_plus1p5percent_V']=12.6*1.015
    assert all(v['energy_between_on_high_and_OV_low_J']>0 for v in out['resistors'].values())
    assert not out['wire_screen']['5852']['SPH002_full_window_fit']
    assert out['wire_screen']['5853']['SPH002_full_window_fit']
    assert not out['fuse_screen']['rating_adopted']
    dump(HERE/'calculation_results.json',out)
    with (HERE/'brake_scenarios.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(out['wheel_events'][0]));w.writeheader();w.writerows(out['wheel_events'])
    print(json.dumps({'mechanical_revision':mech['revision'],'mass_base_kg':base,
       'wheel_peak_resistor_W':out['resistors']['wheel']['P_at_motor_absolute_limit_Rmin_W'],
       'head_peak_resistor_W':out['resistors']['head']['P_at_motor_absolute_limit_Rmin_W'],
       'calculation':'PASS','bench':'NOT_TESTED'},ensure_ascii=False))

if __name__=='__main__':run()
