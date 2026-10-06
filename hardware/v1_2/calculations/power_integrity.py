#!/usr/bin/env python3
"""P1 tolerance/energy/trace estimates; no measured or guaranteed thermal values."""
import json,itertools,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];out={}
for rail,rt,rov in [('wheel',33200,37400),('head',16500,18700)]:
 rows=[]
 # ±1% reference includes a design thermal allowance; comparator ±4mV,
 # resistors0.1%, open collector VOL0..0.4V. Not SPICE/startup/loop validation.
 for e in itertools.product([-1,1],repeat=6):
  ref=2.495*(1+.01*e[0])+.004*e[1];top=rt*(1+.001*e[2]);bot=10000*(1+.001*e[3]);rh=1e6*(1+.001*e[4]);vol=.2+.2*e[5]
  up=ref*(1+top/bot+top/rh)-vol*top/rh
  # Gate high ~rail (head) / ~10V clamp (wheel); unloaded comparator pullup.
  down=(ref*(1+top/bot+top/rh))/(1+top/rh) if rail=='head' else ref*(1+top/bot+top/rh)-10*top/rh
  ov=ref*(1+rov*(1+.001*e[2])/bot)
  rows.append([up,down,ov])
 out[rail]={'brake_on_V_range':[min(r[0] for r in rows),max(r[0] for r in rows)],'brake_off_V_range':[min(r[1] for r in rows),max(r[1] for r in rows)],'ovp_fault_V_range':[min(r[2] for r in rows),max(r[2] for r in rows)],'absolute_motor_limit_V':12.6 if rail=='wheel' else 7.4,'condition':'static tolerance only, gate capacitance/line inductance and startup NOT_TESTED'}
 # Full corner compliance is a necessary static condition, not a spike guarantee.
 assert out[rail]['ovp_fault_V_range'][1]<out[rail]['absolute_motor_limit_V']
 assert out[rail]['brake_on_V_range'][1]<out[rail]['ovp_fault_V_range'][0]
# IPC-2221 empirical external trace relation: I=k*dT^.44*A(mil²)^.725.
tr=[]
for width in [1,2]:
 for copper in [35,70]:
  area=(width/.0254)*(copper/25.4)
  tr.append(dict(width_mm=width,copper_um=copper,estimate_A_at_20C_rise=.048*20**.44*area**.725,length_mm=50,dc_milliohm_at20C=1.724e-8*.05/(width*.001*copper*1e-6)*1000))
out['trace_estimates']=tr
out['rails']={'wheel9V_module_4percent_tolerance':[8.64,9.36],'wheel_at_load_after_assumed_0p2_to_0p55V_diode':[8.09,9.16],'head6V_module_4percent_tolerance':[5.76,6.24],'head_after_assumed_0p2_to_0p55V_diode':[5.21,6.04],'heads_continuous_torque_basis':'use4.8V rated0.65kgcm until actual bus/temperature measured','low_battery':'request cradle at10.8V sustained500ms; <=10.2V sustained100ms reject new travel/request immediate support. Candidate thresholds depend selected pack/dropout; NO hard disarm merely to show low battery.'}
out['loss_examples']={'shunt_6A_W':6**2*.01,'each_B540C_3p5A_at0p5V_W':3.5*.5,'AO4407A_3p5A_at0p017ohm_W':3.5**2*.017,'assumptions':'Rds@-6V before temperature rise; diode Vf and regulator efficiencies require measured load/thermal curves.'}
out['adc']={'ratio':27/127,'V_at12p6V':12.6*27/127,'V_at14V':14*27/127,'battery_V_per_12bit_count_at3p3V':3.3/4095*127/27,'current_A_per_count':3.3/4095/.2,'current_A_at3V':3/.2,'max_poweroff_injection_uA_per_voltage_channel_bound':12.6/100000*1e6,'note':'Absolute voltage accuracy needs VREFINT calibration, divider tolerance and loading; passive dividers may inject limited current with MCU off. Supervisor must keep latch clear. No signed charge-current claim.'}
out['1S_vs_2S_vs_3S']=[{'cells':s,'nominal_V':3.7*s,'assumed_peak_input_A_at60W_90percent_efficiency':60/(3.7*s*.9),'wheel_path':'boost needed' if s<3 else '9V buck + blocking + brake','head_path':'boost6V' if s==1 else 'buck6V','charge':'1S CC/CV' if s==1 else str(s)+'S matched CC/CV + protection/balance independently'} for s in [1,2,3]]
out.update(status='HOST_CALCULATION_ONLY',BENCH='NOT_TESTED',charging_implementation='External3S USB-C charger SKU unresolved; power board is NOT a charger',brake_resistor_status='5R6 and10R external pulse/thermal qualification REQUIRED; 5W label alone does not qualify20W pulses',protection_limitations='OVP removes commanded drive but braking/backdrive may remain; loss of torque causes fall. Independent rail-powered dump is necessary but does not guarantee unlimited downhill energy absorption.')
(R/'reports/power_integrity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['wheel','head','loss_examples']},ensure_ascii=False,indent=2))
