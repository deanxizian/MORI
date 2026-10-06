#!/usr/bin/env python3
"""Reproducible component/cable/thermal estimates, not hardware validation."""
from pathlib import Path
import json, math, csv
H=Path(__file__).resolve().parents[1]
OUT=H/'schematic_S3/reports'

def calculate():
    rt,rb=100000.,13300.
    nominal=.596*(1+rt/rb)
    def voltage(tol):return [.581*(1+rt*(1-tol)/(rb*(1+tol))),.611*(1+rt*(1+tol)/(rb*(1-tol)))]
    scenarios=[]
    for condition,max_delta in [('25C_initial_tolerance',0),('resistor_0_to_85C_design_window',60),('resistor_minus40_to125C_outside_design_window',100)]:
        tol=.001+25e-6*max_delta
        lo,hi=voltage(tol)
        # Explicit preliminary allowances; neither ripple nor loop-R is measured.
        low_at_cam=lo-2*.070-.020
        high_at_board=hi+.020
        scenarios.append(dict(condition=condition,resistor_relative_bound=tol,
            dc_V=[lo,hi],CAM_min_V_with_70mohm_2A_and_20mV_ripple=low_at_cam,
            max_V_with_20mV_ripple=high_at_board,
            static_budget_within_4p75_to5p25=low_at_cam>=4.75 and high_at_board<=5.25))
    cases=[]
    for rail,continuous,peak,fuse,fuse_r in [('MOTION',.5,.75,1,.078),('CAM',1.5,2.,2,.0367)]:
        for vin in [9.0,9.9,11.1,12.6]:
            for current,label in [(continuous,'continuous_target'),(peak,'transient_target')]:
                # -20% initial L, further20% DC-bias fall; minimum switching rate.
                lmin=10e-6*.8*.8;fsmin=290e3
                duty=nominal/vin
                ripple=nominal*(1-duty)/(lmin*fsmin)
                il_rms=math.sqrt(current**2+ripple**2/12)
                input_a=nominal*current/(vin*.85)
                # Hot FET Rds twice25C typical, edge-time25ns assumed.
                conduction=(current**2+ripple**2/12)*(.085*2*duty+.040*2*(1-duty))
                switching=.5*vin*current*25e-9*510e3
                ic_loss=conduction+switching+.05
                inductor_loss=il_rms**2*.069*1.3
                temp=[45+ic_loss*x for x in [57.2,118.9]]
                cases.append(dict(rail=rail,load_case=label,Vin_V=vin,Iout_A=current,
                    Vout_setpoint_V=nominal,inductor_ripple_pp_A=ripple,inductor_peak_A=current+ripple/2,
                    inductor_rms_A=il_rms,min_chip_HS_limit_A=4.,chip_HS_limit_max_A=6.,
                    inductor_Isat20percent_A=7.5,inductor_Irms40C_A=4.,
                    input_current_at85percent_A=input_a,input_fuse_A=fuse,
                    fuse_utilization=input_a/fuse,fuse_cold_loss_W=input_a**2*fuse_r,
                    input_cap_ripple_A=current*math.sqrt(duty*(1-duty)),
                    input_cap_ripple_pp_V_at12uF=current*duty*(1-duty)/(fsmin*12e-6),
                    output_ripple_pp_V_at30uF_10mohm=ripple/(8*fsmin*30e-6)+ripple*.01,
                    IC_loss_estimate_W=ic_loss,inductor_copper_loss_estimate_W=inductor_loss,
                    Tj_estimate_at45C_with_EVM_and_JEDEC_theta=temp,
                    status='ESTIMATE_NOT_TESTED'))
    result=dict(revision='V1.2-H0.3-S3',physical_tests='NOT_TESTED',
        setpoint_V=nominal,feedback=dict(Rtop_ohm=rt,Rbottom_ohm=rb,tolerance=.001,TCR_ppm_per_C_assumed=25,
                                      Vref_range_V=[.581,.596,.611]),
        voltage_scenarios=scenarios,cases=cases,
        common_logic_peak_input_W=nominal*(.75+2)/.85,
        common_logic_peak_input_A_at9V=nominal*(.75+2)/(.85*9),
        system_concurrent_capacity_budget=dict(wheel_output_W=30.,head_output_W=12.,wheel_head_efficiency_assumed=.88,
            battery_W=42/.88+nominal*(.75+2)/.85,
            battery_A_at9p9V=(42/.88+nominal*(.75+2)/.85)/9.9,
            legacy_master_fuse_A=6.3,
            status='PEAK_ENVELOPE_FUSE_DURATION_AND_TEMPERATURE_REVIEW_REQUIRED',
            note='Combines capacity targets, not measured simultaneous consumption. Exceeds6.3A nominal, does not by itself predict fuse opening. Do not up-rate fuse without pack/wire/switch/connector qualification.'),
        removed_external_modules='Pololu D24V22F5 x2: removed from current main BOM, not assumed owned.',
        harness_requirements=dict(MOTION_loop_R_max_ohm=.15,CAM_loop_R_max_ohm=.070,
            CAM_drop_at2A_V=.14,note='Whole round trip: PCB traces, all contacts, crimp, wire, USB pigtail. Cable length remains mechanical-owned.'),
        capacitor_assumptions=dict(input_nominal_uF=44,output_nominal_uF=44,
            input_effective_min_uF=12,output_effective_min_uF=30,
            ripple_limit_assumption_mV_peak=20,
            note='DC bias, temperature, aging and ESR require actual selected-part curves and bench confirmation. No simulated phase margin is claimed.'),
        dynamic_limit=dict(delta_I_A=1.5,uncompensated_time_us=10,Ceff_uF=30,
            capacitive_only_droop_V=1.5*10e-6/30e-6,
            note='This250mV energy bound omits regulator/inductor response and local module capacitors. It is not a predicted closed-loop transient. Scope/load-step validation required.'),
        startup=dict(Cin_uF_per_branch=44.1,Vin_max_V=12.6,loop_R_example_ohm=.2,
            ideal_RC_inrush_I2t_A2s=44.1e-6*12.6**2/(2*.2),
            fuse_1A_nominal_I2t_A2s=.6029,fuse_2A_nominal_I2t_A2s=.530,
            note='Ideal RC example only; actual source inductance, repetition, temperature, main fuse and buck startup load can change stress.'),
        budget=dict(status='BLOCKED_FULL_CNY_QUOTES',incremental_total_cny=None,
                    note='Catalog/MPNs are documented in the S3 BOM. No module price is silently converted to zero.'),
        limitations=[
            'Targets are0.5A motion/1.5A CAM sustained,0.75A/2A transient, not a guaranteed3A board rating.',
            'The temperature/loss numbers depend on future copper and airflow. EVM/JEDEC theta are illustrative bounds, not MORI thermal measurements.',
            'Input fuse is not an electronic output current limiter or regulator-failure OVP. Shared-input fault sag can still reset motion.',
            'Full resistor -40..125C tolerance plus provisional ripple violates5.25V ceiling; this design is not qualified over that full component temperature span.',
            'The0..85C resistor budget has little remaining voltage margin. Dynamic overshoot and cable sag must be measured at the actual MCU connector.',
            'DMM and current-limited PSU alone cannot qualify ripple, overshoot, stability, inrush or interruption time. Oscilloscope and temperature measurement are required before release.',
            'No updated mass or envelope is claimed while PCB frame/placement is unfrozen.'
        ],
        sources=['https://www.ti.com/lit/ds/symlink/tps54302.pdf','https://www.bourns.com/docs/product-datasheets/srp7050ta.pdf',
                 'https://product.samsungsem.com/mlcc/CL32B226KAJNNN.do',
                 'https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1'])
    return result

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);r=calculate()
    (OUT/'logic5v_calculations.json').write_text(json.dumps(r,indent=2)+'\n')
    with (OUT/'logic5v_corner_cases.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(r['cases'][0]));w.writeheader();w.writerows(r['cases'])
    print('logic5V calculation cases',len(r['cases']),'nominal_V',r['setpoint_V'])
