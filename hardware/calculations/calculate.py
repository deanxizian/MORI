#!/usr/bin/env python3
"""SI-unit sizing and screening, not a closed-loop stability proof."""
import json,math,csv,itertools
from pathlib import Path
R=Path(__file__).resolve().parents[1];C=json.loads((R/'calculations/inputs.json').read_text());M=json.loads((R/'mechanical_interfaces.json').read_text())
p=M['parameters'];a=C['assumptions'];mo=C['motor'];g=9.80665;r=p['wheel_diameter']/2000;eta=a['belt_efficiency']
items=C['mass_items'];body=[i for i in items if not i['rotating_wheels']];mb=sum(i['mass_kg'] for i in body);mw=sum(i['mass_kg'] for i in items if i['rotating_wheels']);mt=mb+mw
cb=[sum(i['mass_kg']*i['xyz_mm'][j]/1000 for i in body)/mb for j in range(3)];com=[-cb[1],cb[0],cb[2]];l=com[2]-r
Id=sum(i['mass_kg']*((i['xyz_mm'][1]/1000-cb[1])**2+(i['xyz_mm'][2]/1000-cb[2])**2) for i in body)
Is=0
for i in body:
 if i['part'].startswith('Body_') and 'Shell' in i['part']:Is+=2/3*i['mass_kg']*(p['body_diameter']/2000)**2
 elif i['part'].startswith('Head_') and 'Shell' in i['part']:Is+=2/3*i['mass_kg']*(p['head_diameter']/2000)**2
 else:Is+=i['mass_kg']*.02**2
Ib=Id+Is;rpm=60*a['speed_m_s']/(2*math.pi*r);cpr=mo['ratio']*mo['encoder_counts_motor_x4']
A=mt+.5*mw;B=mb*l;CC=Ib+mb*l*l;det=A*CC-B*B;pole=math.sqrt(A*mb*g*l/det)
triplo=.160/(.39*1.01);triphi=.240/(.39*.99)
# Worst trip threshold used for available torque. Current-torque linearization is approximate.
tcur=mo['stall_torque_Nm']*max(0,triplo-mo['no_load_A'])/(mo['stall_A']-mo['no_load_A'])
oper=[]
for vb,speed in itertools.product([8.4,7.2,6.6,6],[0,.1,.3,.6]):
 v=vb-.3;n=60*speed/(2*math.pi*r);n0=mo['no_load_rpm']*v/12;ts=mo['stall_torque_Nm']*v/12;u=mo['max_duty_balance']
 torque=lambda duty,tol:eta*min(tcur,ts*duty*max(0,1-n/(n0*duty*tol)))
 oper.append(dict(battery_V=vb,speed_m_s=speed,rpm=n,no_load_rpm=n0,full_duty_each_Nm=torque(1,1),limited_65pct_each_Nm=torque(u,1),slow20pct_65pct_each_Nm=torque(u,.8),unlimited_stall_A=mo['stall_A']*v/12))
def recover(total,ll,ii,angle):
 bmass=total-mw;aa=total+.5*mw;bb=bmass*ll;cc=ii+bmass*ll*ll;dd=aa*cc-bb*bb;th=math.radians(angle);td=-64*th;fr=total*g*a['rolling_coefficient']
 tau=(aa*bmass*g*ll*th+bb*fr-dd*td)/(aa+bb/r);xdd=((tau/r-fr)*cc-bb*(bmass*g*ll*th-tau))/dd
 return dict(total_kg=total,com_above_axle_m=ll,body_pitch_inertia_kg_m2=ii,lean_deg=angle,desired_pitch_accel_rad_s2=td,each_wheel_Nm=tau/2,each_motor_A_est=mo['no_load_A']+abs(tau/2)/eta/mo['stall_torque_Nm']*(mo['stall_A']-mo['no_load_A']),x_accel_m_s2=xdd,speed_change_100ms_m_s=xdd*.1,traction_ratio=abs(tau/r-fr)/(a['friction_coefficient']*total*g))
recovery=[recover(total,l,Ib*(total-mw)/mb,deg) for total in [.4,.6,.8,mt] for deg in [5,8,12]]
sensitivity=[recover(mt,z,Ib*f,deg) for z,f,deg in itertools.product([l-.02,l,l+.02],[.65,1,1.5],[5,8,12])]
base=[]
for mass,slope in itertools.product([.4,.6,.8,mt],[0,3]):
 f=mass*a['acceleration_m_s2']+mass*g*(a['rolling_coefficient']*math.cos(math.radians(slope))+math.sin(math.radians(slope)))
 base.append(dict(mass_kg=mass,slope_deg=slope,force_N=f,each_wheel_Nm=f*r/2,each_motor_Nm=f*r/2/eta))
enc=[dict(speed_m_s=v,sample_s=dt,counts=v/(2*math.pi*r)*cpr*dt) for v,dt in itertools.product([.005,.01,.03,.3,.6],[1/416,.01,8/416])]
power=[]
for s,vb in itertools.product(C['power_states'],[8.4,6.6]):
 il=s['logic_5V_A']+s['lcd_3V3_A']+.02 # pair encoder <=20mA via5V
 ih=s['servo_5V_A'];im=s['motor_each_A'];pb=2*vb*im+5*(il+ih)/.85+.05
 power.append(dict(state=s['name'],battery_V=vb,power_W_upper_budget=pb,battery_A=pb/vb,logic_buck_A=il,head_buck_A=ih,driver_and_sense_heat_W=2*im**2*(.6+.39),motor_copper_each_W=im**2*(12/mo['stall_A'])))
# Clamp tolerance corners: TL431B 0.5% @25C plus ±17mV allocated temp drift,
# LM393 ±9mV offset budget, 0.1% divider and 1% feedback. Not stability/prop-delay proof.
clamp=[]
for vr,rt,rb,rh,vol in itertools.product([2.495*.995-.017-.009,2.495*1.005+.017+.009],[25500*.999,25500*1.001],[10000*.999,10000*1.001],[2.2e6*.99,2.2e6*1.01],[0,.4]):
 on=(vr*(1/rt+1/rb+1/rh)-vol/rh)*rt
 # OUT high loaded by100k gate pull-down,4k7 pull-up; conservative0.95*bus approximation.
 off=vr*(1/rt+1/rb+1/rh)/(1/rt+.95/rh)
 clamp.append((on,off))
res={'status':'PASS','scope':'Arithmetic and model-volume integration only; physical verification NOT_TESTED','main_motor':mo,'mass':{'total_kg':mt,'body_kg':mb,'wheel_system_kg':mw,'body_com_Blender_m':cb,'body_com_control_m':com,'body_com_relative_axle_control_m':[com[0],com[1],l],'com_forward_uncertainty_m':.008,'com_height_uncertainty_m':.02,'pitch_inertia_about_body_com_kg_m2':Ib,'inertia_interval':[Ib*.65,Ib*1.5],'mass_interval_kg':[mt*.8,mt*1.2],'note':'19 closed STL volumes at1.24g/cm3; coupons excluded; bought placeholders NOT counted; tyres/shafts/bearings/boards allocations; true slice mass and rotor/belt inertia pending'},'kinematics':{'target_rpm':rpm,'encoder_output_counts_x4':cpr,'single_channel_cycles_motor_rev':mo['encoder_counts_motor_x4']/4,'distance_per_count_m':2*math.pi*r/cpr,'belt_ratio':1,'belt_efficiency_assumption':eta,'track_m':.138},'linear_model':{'states':'x,xdot,theta,thetadot; upright linearization, level rolling without slip','equations':['A*xdd+B*thetadd=tau/r-Frr','B*xdd+C*thetadd=mb*g*l*theta-tau'],'A':A,'B':B,'C':CC,'det':det,'open_loop_positive_pole_s-1':pole,'unmodelled':'motor electrical dynamics/reflected inertia, backlash, flexible belts, head yaw coupling, tyre compliance, Coulomb friction, slip, sensor phase delay; wheel inertia approximated solid discs'},'regen':{'cap_F':.001,'cap_energy_8_4_to_10_V_J':.5*.001*(100-8.4**2),'translation_energy_at_0_3_J':.5*mt*.3**2,'cap_bus_after_0_5J_V':math.sqrt(8.4**2+1000),'dump_R_ohm':5.6,'dump_current_at8_9_A':8.9/5.6,'dump_power_at8_9_W':8.9**2/5.6,'current_trip_range_A':[triplo,triphi],'clamp_on_tolerance_V':[min(i[0] for i in clamp),max(i[0] for i in clamp)],'clamp_off_tolerance_V':[min(i[1] for i in clamp),max(i[1] for i in clamp)],'qualification':'NOT_TESTED. Tolerance allocation must be confirmed; hysteresis, gate charge, resistor pulse energy and comparator turn-on overshoot require scope acceptance<10V.'},'runtime':{'candidate_battery_Wh':24.12,'usable_Wh':18.09,'assumed_average_W':[5,8],'estimated_hours':[18.09/8,18.09/5],'battery_fit':'FAIL; 71mm pack exceeds70mm slot; these runtime estimates require verified charge/usable capacity'},'head':{'inertia_kg_m2_assumed':.0002,'accel_rad_s2_assumed':2,'cable_friction_Nm_allocation':.01,'head_torque_2x_margin_Nm':2*(.0002*2+.01),'required_servo_Nm_with_efficiency_0_8':2*(.0002*2+.01)/1.75/.8,'required_total_servo_travel_deg':210,'SER0037_spec_lower_rated_torque_at4_8V_Nm':.3*.0980665,'status':'NOT_TESTED; use lower specification-table values when vendor introduction disagrees'},'motor_envelope':oper,'recovery':recovery,'sensitivity':sensitivity,'base_load':base,'encoder_counts':enc,'power':power,'mass_items':items}
(R/'reports/calculation_results.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
for name,rows in [('mass',items),('motor_envelope',oper),('recovery',recovery),('com_inertia_sensitivity',sensitivity),('base_load',base),('encoder_counts',enc),('power_states',power)]:
 with (R/f'reports/{name}.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
nom=[i for i in recovery if i['total_kg']==mt]
worst=[i for i in oper if i['battery_V']==6.6 and i['speed_m_s']==.3][0]
lines=['# 可复核计算 — PROTOTYPE / UNVALIDATED','',f'整机预算 **{mt:.3f} kg**（保守实体PLA，不把占位电池/电机重复算进模型）；机身{mb:.3f} kg，轮系{mw:.3f} kg。',f'控制坐标重心相对轮轴：前向{com[0]*1000:.1f}±8 mm，左向{com[1]*1000:.1f} mm，高{l*1000:.1f}±20 mm。俯仰惯量{Ib:.6f} kg·m²，范围0.65–1.5倍。',f'目标0.3m/s对应{rpm:.2f}rpm；精确输出{cpr:.3f}counts/rev，每计数{2*math.pi*r/cpr*1000:.4f}mm。','', '动力学包含轮端扭矩对机身的反作用；恢复表只筛选θdot=0、θdd=-64θ的瞬时需求。不能据此宣称整段轨迹或闭环稳定。','', '|电池V|速度m/s|空载rpm|全驱动Nm/轮|65% Nm/轮|慢20%电机、65% Nm/轮|','|---:|---:|---:|---:|---:|---:|']
for i in oper:lines.append(f"|{i['battery_V']}|{i['speed_m_s']}|{i['no_load_rpm']:.1f}|{i['full_duty_each_Nm']:.4f}|{i['limited_65pct_each_Nm']:.4f}|{i['slow20pct_65pct_each_Nm']:.4f}|")
lines+=['','上述已乘皮带效率0.85，扣0.3V供电降压，按限流最低触发值限制扭矩；连续扭矩尚未证明。','', '|预算质量kg|初倾deg|每轮需求Nm|估算电机A|100ms增速m/s|','|---:|---:|---:|---:|---:|']
for i in recovery:lines.append(f"|{i['total_kg']:.3f}|{i['lean_deg']}|{i['each_wheel_Nm']:.4f}|{i['each_motor_A_est']:.3f}|{i['speed_change_100ms_m_s']:.3f}|")
lines+=['',f"6.6V、0.3m/s、慢20%电机的可用值{worst['slow20pct_65pct_each_Nm']:.4f}Nm/轮； nominal 8°筛选需求{nom[1]['each_wheel_Nm']:.4f}Nm/轮。还必须检查恢复过程中增速后的余量、COM/惯量角落和摩擦。",'','最初台架目标设0.1m/s、±3°小扰动；0.3m/s仍是待验收的目标。不能将欠压后只禁止移动当成恢复余量已经足够。','',f"电容8.4→10V只吸收{res['regen']['cap_energy_8_4_to_10_V_J']:.5f}J；0.3m/s平动能{res['regen']['translation_energy_at_0_3_J']:.5f}J，且尚未含转动/势能。必须实测回灌。",'','完整CSV、惯量/COM敏感性、逐路功耗与元数据见同目录JSON。所有物理项目NOT_TESTED。']
(R/'reports/calculations.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'mass':res['mass'],'low_voltage_motor':worst,'nominal_recovery':nom,'power_peak':power[-1],'regen':res['regen']},indent=2))
