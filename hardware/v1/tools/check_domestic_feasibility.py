#!/usr/bin/env python3
"""Numerical procurement screening, not a simulation or bench qualification."""
import json
import math
from pathlib import Path

R=Path(__file__).resolve().parents[3]
H=R/'hardware/v1'
P=H/'procurement'
G=json.loads((R/'config/geometry.json').read_text())
battery_nominal_V=7.4
battery_Ah=2.0
usable_soc=0.8
capacity_margin=0.9
energy_Wh=battery_nominal_V*battery_Ah*usable_soc*capacity_margin
wheel_diameter=G['wheel_diameter_mm']/1000
body_center_z=G['ground_clearance_mm']+G['body_diameter_mm']/2
inner_R=G['body_diameter_mm']/2-G['shell_thickness_mm']
z_axle=G['wheel_diameter_mm']/2
old_peak_W=33.78  # Explicitly inherited stress scenario, not a new motor prediction.
low_bus_V=6.4    # Design screening value; not a confirmed BMS cutoff.
torque_vendor_gcm=300
motor_Nm=torque_vendor_gcm/1000*9.80665/100
result={
    'revision':'V1-H0.2','status':'PASS','meaning':'Screening calculations executed; hardware qualification NOT_TESTED',
    'physical_test_status':'NOT_TESTED',
    'input_status':{'dimensions':'config/geometry.json','battery':'Yahboom factory specification, not measurement',
        'old_power_envelope':'H0.1 stress scenario only; OV5640 and FOC consumption must be rebuilt',
        'efficiency_and_usable_capacity':'ASSUMED'},
    'voltage_screen':{
        'battery_screening_range_V':[low_bus_V,8.4],
        'FIT1034_motor_min_V':7.4,'DRI0058_driver_min_V':8.0,
        'motor_low_voltage_margin_V':low_bus_V-7.4,
        'driver_low_voltage_margin_V':low_bus_V-8.0,
        'direct_connection_result':'FAIL',
        'remedy_status':'BLOCKED: compatible regulated supply or different qualified driver/motor; no invented part/quote'},
    'capacity_screen':{
        'nominal_Wh':battery_nominal_V*battery_Ah,'usable_soc_factor':usable_soc,
        'capacity_margin_factor':capacity_margin,'usable_Wh':energy_Wh,
        'battery_side_avg_W_for_60min_at_most':energy_Wh,
        'sensitivity':[{'battery_side_avg_W':p,'estimated_minutes':60*energy_Wh/p} for p in [5.34,7.34,11.34,20]],
        'acceptance':'NOT_TESTED; sensitivity only, not 60min promise'},
    'current_screen':{
        'inherited_peak_W':old_peak_W,'screening_low_V':low_bus_V,
        'inherited_peak_A':old_peak_W/low_bus_V,
        'yahboom_vendor_continuous_A':15,'yahboom_rating_margin_to_old_scenario_A':15-old_peak_W/low_bus_V,
        'FIT0137_vendor_continuous_A':2.5,'FIT0137_margin_A':2.5-old_peak_W/low_bus_V,
        'FIT0137_result':'FAIL for stated concurrent demand',
        'yahboom_whole_system_result':'NOT_TESTED: connector/BMS/thermal/actual new loads not qualified'},
    'wheel_speeds':[{'m_per_s':v,'rpm':v/(math.pi*wheel_diameter)*60,
                      'rad_per_s':v/(wheel_diameter/2)} for v in [0.1,0.3]],
    'FOC_torque_screen':{
        'vendor_300_g_cm_as_Nm':motor_Nm,'continuous_rating_known':False,
        'assumed_transmission_efficiency':0.85,
        'hypothetical_ratios':[{'ratio':ratio,'wheel_Nm_if_vendor_torque_sustainable':motor_Nm*ratio*0.85} for ratio in [1,3,4,5]],
        'warning':'No ratio is selected; neither continuous torque nor speed/thermal data are validated. No Hover tor integer conversion.'},
    'low_axle_geometry':{'axis_z_mm':z_axle,'body_center_z_mm':body_center_z,'inner_sphere_radius_mm':inner_R,
        'note':'Inner sphere clearance, not outer wheel diameter, constrains the driven pulley; preserve belt/shaft service clearances.'}}
if inner_R is not None:
    x=40.5  # Existing trial driven-pulley plane. Shaft/BOM not frozen.
    z_floor=body_center_z-math.sqrt(inner_R**2-x**2)
    result['low_axle_geometry'].update({'existing_trial_pulley_x_mm':x,
        'inner_bottom_z_at_trial_x_mm':z_floor,'available_downward_radius_mm':z_axle-z_floor,
        'hypothetical_GT2_20_to_60_output_pitch_radius_mm':60*2/(2*math.pi),
        'simple_3to1_driven_pulley_result':'FAIL for ideal spherical-inner-envelope screen at existing trial x; current relief mesh collision NOT_TESTED'})
(P/'calculation_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
