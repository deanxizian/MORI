"""Read the authoritative mechanical project; never modify its files."""
from pathlib import Path
import json,math,hashlib,struct
R=Path(__file__).resolve().parents[1];P=R.parent
p=json.loads((P/'params.json').read_text());d=json.loads((P/'reports/derived.json').read_text());m=json.loads((R/'mechanical_interfaces.json').read_text())
m['schema_version']=2;m['source']='../params.json + ../reports/derived.json + dimensions/requirements.json; real supplier parts below are NOT substitutes for placeholders'
m['mechanical_source_sha256']={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/'params.json',P/'reports/derived.json',P/'reports/export_manifest.json']}
m['coordinates']={'handedness':'right','x':'lateral (control left)','y':'fore/aft; front=-Y','z':'up','origin':'ground below axle midpoint','control_transform':'[x,y,z]_control=[-Y,X,Z]_Blender','status':'PASS coordinate definition; sensor mounting NOT_TESTED'}
m['parameters']={k:p[k+'_mm'] for k in ['head_diameter','body_diameter','wheel_diameter','wheel_width','ground_clearance','wheel_body_gap','shell_thickness']};m['parameters']['head_yaw_limit_deg']=p['head_yaw_limit_deg']
m['derived_layout_assumptions']={'wheel_axis_z':d['wheel_z'],'body_sphere_center':[0,0,d['body_z']],'head_sphere_center':[0,0,d['head_z']],'side_cut_x_abs':p['body_side_cut_x_mm'],'wheel_centers':[[69,0,47.5],[-69,0,47.5]],'track_width':d['track'],'body_top_cut_z':d['body_top_z'],'visible_black_mask_diameter':58,'motor_centers':[[5,-20,90.5],[-5,20,90.5]],'drive_type':'1:1 belt to independent 6mm axles; pitch/teeth/tension not selected'}
parts=m['parts'];mtr=parts['wheel_motor']
for key in ['gearbox_front_centers','wheel_hub_engagement_target','case_direction']:mtr.pop(key,None)
mtr.update(shaft_axis_global='X',reserved_case='diameter25 length60 + encoder23x12 + shaft4x14',target_shaft_axis_centres_yz=[[-20,90.5],[20,90.5]],connector_exit='factory20cm six-wire cable with2.54mm female header; custom XH6 retermination, reserve measured exit/bend space',catalog_case_box_excludes_encoder_overhang=False)
mtr.update(mpn='Pololu4863 25D MP12V 20.408667:1',actual_max_case_box=[25,25,65],catalog_case_box=[25,25,65],shaft={'diameter':4,'shape':'D','usable_length':12.5,'projection_envelope':12.5},mounting={'thread':'2 x M3','hole_pitch_mm':17,'max_engagement_mm':6, 'centres_local_mm':[[-8.5,0],[8.5,0]],'view':'gearbox face; centers +/-8.5mm from shaft, page2 drawing'},source='motor25; motor25_drawing',full_keepout_local=[29,29,88],fit_status='NOT_TESTED; diameter25 and total65 incl encoder within length72 reservation, encoder OD25 exceeds23 placeholder; output shaft12.5 shorter than14; bracket and leads require review')
parts['head_servo'].update(mpn='DFRobot SER0037 270 degree positional PWM',envelope=[22.9,12.3,22.6],mass_g=11.2,center=[-22,0,122],source='servo270',connector_exit='JR 3-pin 275mm cable into body',required_total_travel_deg=210,nominal_travel_deg=270,fit_status='NOT_TESTED; body width exceeds12mm reservation but fits12.6mm aperture with0.15mm/side; ears/spline/full height pending',gear_ratio_servo_to_head=1.75)
parts['display'].update(front_center=[0,d['face_y'],186],front_normal=[0,-1,0],fit_status='FAIL optical match: active32.4mm vs required60mm / aperture58mm; proposed smaller inner mask requires mechanical revision',reserved={'active_diameter':60,'pcb_diameter':65,'glass_thickness':2.8,'bare_pcb_thickness':1.6})
parts['battery']={'mpn':'BatterySpace5893 PL-605060S2-WR','envelope':[66,54,20],'center':[0,0,63],'mass_g':95,'fit_status':'FAIL: cannot fit40x70x20; withdrawn','source':'battery','procurement_hold':'Do not purchase for current tray'}
parts['battery_near_fit_candidate']={'mpn':'ANSMANN 2447-0105','envelope':[39,71,18],'mass_g':99,'nominal_V':7.2,'capacity_Ah':3.35,'max_discharge_A':5,'fit_status':'FAIL nominal length71>70; tray inner70.6 still short0.4mm before clearance; propose internal length>=72 plus lead relief, requires mechanical review','source':'ansmann_candidate manufacturer product sheet, hosted by distributor','charge_current_A':None,'cell_balance':None,'regen_path':None,'status':'HOLD procurement/charging; mass and energy used only for provisional budgets until manufacturer confirms full electrical spec'}
parts['rejected_battery_legacy']=parts['battery']
parts['battery']=dict(parts['battery_near_fit_candidate'],center=[0,0,63],keepout=[42,76,22],connector_exit='factory12cm open leads; ask factory keyed termination and strain relief; no bare-cell soldering',mount_holes=[],retention='padded tray+strap; no pressure into cells')
parts['mcu'].update(fit_status='FAIL provisional keepout65x30x18 vs55x24x7; exact board outline pending; external bench first',reserved=[55,24,7])
parts['imu'].update(center=[35,0,115],orientation='raw sensor-to-control rotation must be measured; no implicit identity',fit_status='FAIL25.6x17.8x4.6 vs16x16x4',reserved=[16,16,4])
parts['driver'].update(fit_status='NOT_TESTED; bare20.3x17.8 planar size fits36x20 but headers/terminals/current-sense changes may exceed7 high')
parts['carrier'].update(outline=[96,92,1.6],outline_description='intersection of +/-48 X, +/-46 Y and radius61 circle, polygon approximated clipped corners',center=[0,0,117],mount_holes_local=p['structure']['deck_mount_xy_mm'],hole_diameter=3.4,hole_status='PASS in CAD XY: copied deck holes +/-40,+/-42; standoff height/load/thread NOT_TESTED',placement_status='NOT_TESTED; standalone carrier proposal replaces existing board brackets only after structural review',cutouts=[{'rect_xy_mm':[-38,-6,-12,12],'reason':'servo envelope + bracket keepout'},{'center':[14,-7],'diameter':10},{'center':[14,7],'diameter':10}],connector_exit='upward from top; service loops and head/yaw clearance unverified')
m['model_names_to_control']={'control_left':'Blender Wheel_R / Motor_R; X positive; motor center[-5,20,90.5]','control_right':'Blender Wheel_L / Motor_L; X negative; motor center[5,-20,90.5]'}
parts['wheel_bearing']={'mpn':'NSK686ZZ','quantity':4,'nominal_id_od_width':[6,13,5],'catalog_mass_g':2.69,'fit_status':'PASS nominal dimensions only; physical fit NOT_TESTED. Printed13.6mm hole must be fitted, not used as precision clearance.','source':'NSK bearing guide, 600 series table'}
parts['head_bearing']={'mpn':'NSK6805ZZ candidate','quantity':1,'nominal_id_od_width':[25,37,7],'reserved_id_od_width':[24,36,6],'fit_status':'FAIL direct substitution; all three dimensions +1mm; HOLD revised bearing seat/shaft/preload and axial stack','source':'NSK6805ZZ product/calculation page'}
m['unresolved_mechanical']=['actual pulleys and belt tooth profile/length/tension','head bearing candidate NSK6805ZZ25x37x7 does not fit24x36x6 placeholder','motor clamp,4mm D-shaft pulley engagement and shorter12.5mm shaft','servo ears/spline/centre','screen active area mismatch','battery fit/connector/PCM','MCU and IMU brackets','carrier z stack and emergency stop integration']
(R/'mechanical_interfaces.json').write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
# Integrate tetrahedra in exported world-coordinate STL for volume and centroid.
manifest=json.loads((P/'reports/export_manifest.json').read_text());mass=[];volrows=[]
for e in manifest['parts']:
 if e['id'].startswith('Coupon'):continue
 raw=(P/e['file']).read_bytes();n=struct.unpack_from('<I',raw,80)[0];vol=0.;moment=[0.,0.,0.]
 for i in range(n):
  a,b,c=[struct.unpack_from('<3f',raw,84+50*i+12+j*12) for j in range(3)]
  cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]);v=sum(a[j]*cross[j] for j in range(3))/6;vol+=v
  for j in range(3):moment[j]+=v*(a[j]+b[j]+c[j])/4
 xyz=[v/vol for v in moment];rot=e['id'].startswith('Wheel_Cap');kg=abs(vol)*1.24e-6
 mass.append({'part':e['id'],'mass_kg':kg,'xyz_mm':xyz,'rotating_wheels':rot,'basis':'STL closed mesh volume x1.24g/cm3 solid PLA; no infill discount; actual material/print mass pending'})
 volrows.append({'id':e['id'],'volume_mm3':vol,'centroid_Blender_mm':xyz,'solid_PLA_kg':kg,'sha256':hashlib.sha256(raw).hexdigest()})
# Non-STL moving wheels, axles and actual hardware; do not count placeholder volumes.
for name,kg,xyz,rot,basis in [
 ('wheel_hubs_tyres_shafts_pulleys',.11,[0,0,47.5],True,'pair allocation: excludes printed caps counted above; exact tyre material/shafts/bearings pending'),
 ('wheel_motors',.196,[0,0,90.5],False,'2x98g manufacturer; motor rotor/reflected inertia unknown'),
 ('battery',.099,[0,0,63],False,'ANSMANN2447-0105 catalog99g; tray revision/electrical verification HOLD'),
 ('lcd_and_mask',.025,[0,-36,186],False,'module+mask allowance; no duplication of mount frame'),
 ('servo',.0112,[-22,0,122],False,'SER0037 specification weight, ears not measured'),
 ('boards_and_carrier',.065,[0,0,117],False,'allowance; all bare modules, carrier and local small parts'),
 ('bearings_fasteners_standoffs',.045,[0,0,96],False,'nonprinted hardware allocation incl four axle bearings/head bearing/fasteners'),
 ('dump_resistor_clamp',.025,[0,28,85],False,'power resistor+heat-spreader allowance; measured thermal requirements may increase'),
 ('wires_connectors',.035,[0,0,95],False,'allowance; external test stand/estop excluded')]:mass.append(dict(part=name,mass_kg=kg,xyz_mm=xyz,rotating_wheels=rot,basis=basis))
c=json.loads((R/'calculations/inputs.json').read_text());c['mass_items']=mass;c['mass_coordinate_system']='Blender X lateral, front -Y, Z up';c['assumptions'].update(belt_efficiency=.85,drive_ratio_motor_output_to_wheel=1.0,model_mass_relative_uncertainty=.2)
(R/'calculations/inputs.json').write_text(json.dumps(c,indent=2,ensure_ascii=False)+'\n');(R/'reports/model_volume_mass.json').write_text(json.dumps(volrows,indent=2)+'\n')
print('CAD volume integrated parts:',len(volrows),'total proposed mass kg',sum(i['mass_kg'] for i in mass))
