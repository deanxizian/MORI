#!/usr/bin/env python3
"""P3 geometry/material estimates; NOT a measured current or thermal rating."""
from pathlib import Path
import json,math
H=Path(__file__).resolve().parents[1];out=H/'layout_P3/reports';out.mkdir(parents=True,exist_ok=True)
rho=1.724e-8
boards=[]
for name,w,h,t in [('motion',70,35,.035),('imu',20,16,.035),('power',80,55,.070)]:
 area=w*h;core=1.6-.02-2*t
 # Nominal laminate density1.85g/cm3, copper8.96g/cm3; no hole/mask correction.
 mass=[area*core*.00185+area*2*t*f*.00896 for f in [.3,.8]]
 boards.append(dict(board=name,outline_mm=[w,h],finished_thickness_mm=1.6,copper_nominal_mm=t,FR4_density_g_cm3=1.85,assumed_copper_coverage_fraction=[.3,.8],bare_board_mass_estimate_g=[round(x,3) for x in mass],excludes='Components, connectors, solder and cables; hole/mask effects omitted. Not a populated fit or measured mass.'))
tracks=[]
for net,w,a in [('battery',2,6),('wheel',1.5,3),('head',1,2),('5V_CAM',.8,1.5),('5V_motion',.8,.5)]:
 length=.05;R=rho*length/(w*.001*.000070)
 tracks.append(dict(role=net,nominal_width_mm=w,nominal_copper_um=70,illustrative_length_mm=50,assumed_current_A=a,resistance_20C_ohm=round(R,6),voltage_drop_V=round(R*a,5),copper_dissipation_W=round(R*a*a,5),scope='50mm comparison, not extraction of the whole board current path or a qualified continuous-current rating.'))
barrel=[]
for plating_um in [20,25]:
 R=rho*.0016/(math.pi*.00045*plating_um*1e-6)
 barrel.append(dict(finished_drill_mm=.45,assumed_plating_um=plating_um,count_parallel=2,equivalent_resistance_20C_ohm=R/2,total_loss_at_6A_W=36*R/2,note='Two native1.0/0.45mm BAT_MON vias. PCB foil thickness is NOT the via plating thickness. Current sharing/temperature require measurement.'))
old_area=80*45;new_area=80*55;added_area=new_area-old_area
result=dict(revision='V1.2-H0.3-P3',status='DESIGN_ESTIMATE',physical_tests='NOT_TESTED',boards=boards,power_extra_area_mm2=added_area,power_area_increase_percent=100*added_area/old_area,power_bare_mass_increase_estimate_g=[round(added_area*(1.6-.02-.14)*.00185+added_area*.14*f*.00896,3) for f in [.3,.8]],track_comparisons=tracks,battery_parallel_via_estimate=barrel,limitations=['No measured assembled mass, temperatures, transient ripple or regenerative braking results.','These DC estimates omit connector/contact resistance, temperature rise, current crowding, copper removal and component losses.','The planned copper stack needs a supplier quote and verification; cost remains UNKNOWN.','No update to measured robot COM or60-minute runtime acceptance is implied.'])
(out/'layout_power_estimate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
