#!/usr/bin/env python3
"""Explicit P4 electrical estimates; never a PCB ampacity/thermal qualification."""
import json,math
from pathlib import Path
O=Path(__file__).resolve().parent
rho20_ohm_mm=1.724e-5
copper_mm=.035 # ASSUMED 1oz finished copper; order stack-up must confirm.
via_plating_mm=.025 # ASSUMED, not a fabricator guarantee.
length_mm=1.6

def track(l,w,i):
 r=rho20_ohm_mm*l/(w*copper_mm)
 return dict(length_mm=l,width_mm=w,current_A=i,resistance_mohm=r*1000,drop_mV=i*r*1000,loss_W=i*i*r)
def via(drill,n,i):
 area=math.pi*(drill+via_plating_mm)*via_plating_mm
 r=rho20_ohm_mm*length_mm/area/n
 return dict(drill_mm=drill,parallel_count=n,total_current_A=i,resistance_mohm=r*1000,loss_W=i*i*r,assumed_uniform_current_share=True)
report=dict(status='ESTIMATE_NOT_TESTED',assumptions=dict(copper_thickness_mm=copper_mm,via_barrel_plating_mm=via_plating_mm,temperature_C=20,does_not_include='contact resistance, solder necks, copper plating tolerances, hot resistance, convection, thermal vias or board thermal coupling'),rear=dict(design_continuous_input_A=1,series_fuse_A=1.5,USB_neck=track(1.355,.4,1),interconnect_example=track(20,.6,1),via_example=via(.25,1,1),warning='Individual neck conservatively carries full1A; no assumed perfect USB-pin current sharing. The fuse is not an electronic1A limit.'),master=dict(pack_max_V=12.6,gate_return_resistor_ohm=10000,gate_pullup_ohm=100000,maximum_static_switch_current_mA=12.6/10000*1000,unclamped_divider_Vgs_at_full_pack=-12.6*100000/110000,Rds_on_design_example_ohm=.017,Rds_condition='Use AO4407A datasheet stated gate voltage and junction temperature; hot value not established',loss_at_3A_W=3**2*.017,loss_at_6p5A_W=6.5**2*.017,loss_hot_2x_sensitivity_at_6p5A_W=6.5**2*.017*2,loss_2x_is_assumption_not_vendor_rating=True,source_via_array=via(.45,3,6.5),capacitor_inrush_J_per_1000uF=.5*.001*12.6**2,qualification='NOT_TESTED: inrush, MOSFET SOA, transient Vgs, hot drop, OFF leakage and reverse supply'),limits='Resistance estimates do not establish allowable current, temperature rise or continuous motor capability. Validate using real copper stack-up, representative load and thermal measurement; scope/appropriate electronic load required for transients.')
report['power_board_native_copper_intent_um']=70
report['power_conservative_calculation_copper_um']=35
report['head_output']=dict(trunk_20mm_example=track(20,1,2),parallel_transition=via(.45,2,2),actual_via_centers_mm=[[49.3,44.2],[49.3,45.4]],qualification='Two1.0mm lands with0.45mm drills;2A is an estimate scenario, not a verified continuous rail rating. Copper, plating, terminal heating and current sharing NOT_TESTED.')
(O/'interconnect_estimate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
