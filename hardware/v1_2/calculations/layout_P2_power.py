#!/usr/bin/env python3
"""P2 illustrative copper/via loss estimates. No empirical bench results."""
from pathlib import Path
import math,json
H=Path(__file__).resolve().parents[1]
rho=1.724e-8;rows=[]
for label,w,i in [('BATTERY_MAIN',2,6),('WHEEL_MAIN',1.5,3.5),('HEAD_MAIN',1,3.5)]:
    t=70;length=50
    r=rho*(length/1000)/(w/1000*t/1e6)
    area=(w/.0254)*(t/25.4)
    rows.append(dict(path=label,width_mm=w,copper_um=t,example_length_mm=length,example_current_A=i,dc_resistance_mohm_at20C=r*1000,voltage_drop_V=i*r,copper_loss_W=i*i*r,IPC2221_external_estimated_A_at20C_rise=.048*20**.44*area**.725))
via_r=rho*.0016/(math.pi*.00045*.000025)
out=dict(revision='V1.2-H0.2-P2',status='HOST_CALCULATION_ONLY',BENCH='NOT_TESTED',note='50 mm segment examples, not extracted source-to-load path resistance. 70 um outer copper,20C copper resistivity; actual plating/copper/temperature/planes and pad constrictions affect results. IPC2221 empirical relation is a rough estimate, not a guaranteed rating. Total loop includes ground plane/connector/regulator losses. 0.2 mm signal/sense branches are not rated for these load currents.',traces=rows,battery_via_example=dict(outer_mm=1,drill_mm=.45,board_mm=1.6,assumed_barrel_plating_um=25,parallel_count=2,combined_A=6,single_dc_mohm=via_r*1000,parallel_loss_W=6**2*via_r/2,limitation='Equal current sharing and plating thickness assumed. No qualified via temperature rise/current rating; supplier and bench confirmation required.'),board_material=dict(thickness_mm=1.6,power_copper_um=70,logic_copper_um=35,finish='ENIG design target; quote pending'),required_tests=['current-limited no-load startup','single branch stepped load and supply drop','parallel wheel/head peak load','reverse/braking energy injection with protected fixture','connector/shunt/MOSFET/diode/plane temperatures','fault latch and interaction power-loss behavior'])
(H/'layout_P2/reports/copper_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
