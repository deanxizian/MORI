#!/usr/bin/env python3
"""Publish versioned candidate interfaces without changing mechanical allocations."""
import csv,hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=R/'hardware/v1';REV='V1-H0.1'
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
catalog=json.loads((H/'bom_candidates.json').read_text());items={x['id']:x for x in catalog['items']}
if catalog.get('revision') != REV:
    raise SystemExit('Historical H0.1 pin generator cannot wire newer candidates. Read procurement_update and publish a reviewed pinmap revision first.')
mechanical_path=R/'contracts/mechanical_interfaces.json'
mech=json.loads(mechanical_path.read_text())
snapshot=H/'interfaces/mechanical_V1_A_before_hardware.json'
if not snapshot.exists():shutil.copy2(mechanical_path,snapshot)
envelopes={}
for key,bom_id,extra,conflict in [
 ('wheel_foc','WH_FOC',None,'BLOCKED: exact motor unknown; current belt architecture is not a hub mounting drawing'),
 ('wheel_brushed_alternative','WH_BRUSH',{'connector_axial_service_mm':15},'BLOCKED: cylinder nominal fits; shaft, flange and plug not confirmed'),
 ('yaw_servo','HD_SERVO',{'wire_exit_mm':12,'screw_tool_access_mm':10},'FAIL: overall 32.6×12.19×28.55 vs body allocation24×13×24; orientation/horn sweep require Stage B'),
 ('pitch_servo','HD_SERVO',{'wire_exit_mm':12,'screw_tool_access_mm':10},'FAIL: vendor-axis overall32.6×12.19×28.55 cannot fit24×12×22 under any orthogonal permutation; output axis -X requires vendor-to-robot transform before mounting coordinates'),
 ('motion_mcu','MCU',{'antenna_no_metal_clearance_mm':15,'proposed_carrier_xyz_mm':[48,24,12]},'BLOCKED: module fits when rotated; carrier holes, headers and antenna near battery/yaw servo not checked'),
 ('interaction_mcu','MCU',{'antenna_no_metal_clearance_mm':15,'proposed_carrier_xyz_mm':[48,24,12]},'BLOCKED: module fits when rotated; full media routing/connector reserve pending'),
 ('body_imu','IMU',{'connector_exit_reserve_mm':12},'BLOCKED: PCB fits26×18×5, connector protrusion does not fit same box'),
 ('display','LCD',{'rear_wire_service_mm':12},'FAIL: active32.4 vs assumed58; revise aperture/eye spacing and frame. Thickness/holes unknown'),
 ('camera','CAM',{'fpc_bend_radius_mm':None},'BLOCKED: actual CCM/lens/FPC envelope unknown, cannot approve14×8×10'),
 ('battery','BAT',{'proposed_service_envelope_xyz_mm':[44,84,23],'connector_exit_mm':12},'BLOCKED: core39×71×18 nominally fits40×72×22, but service envelope does not'),
 ('charger','CHG',{'heat_sink_height_mm':7,'thermal_pad_mm':0.5,'connector_service_mm':12},'FAIL:28×37 exceeds24×16 power-module allocation before heatsink'),
 ('logic_regulator_each','REG_3V3',{'connector_service_mm':8},'BLOCKED:16.5×22 fits rotated plan only; totalheight and location unknown'),
 ('servo_regulator','REG_HEAD',None,'BLOCKED: no vendor dimensions'),
 ('power_monitor','PWR_MON',{'terminal_wire_exit_mm':15},'FAIL:30×22 requires new allocation'),
 ('microphone','MIC',{'acoustic_isolation_radial_mm':2},'BLOCKED: acoustic duct/height drawing pending'),
 ('amplifier','AMP',None,'BLOCKED: dimensions not published in reviewed page'),
 ('speaker','SPK',{'sealed_rear_cavity_depth_mm':5},'BLOCKED: cavity mechanical review and supply stock required')]:
    row=items[bom_id]
    envelopes[key]=dict(candidate_model=row['model'],bom_id=bom_id,vendor_dimensions_mm=row['vendor_dimensions_mm'],vendor_mass_g=row['vendor_mass_g'],
      dimension_status='VENDOR_VERIFIED' if row['vendor_dimensions_mm'] else 'ASSUMED',verification_scope='Only non-null fields in vendor_dimensions_mm; proposed clearances are ASSUMED, missing fields remain unknown',measurement_status='NOT_TESTED',
      shaft_hole_interface=row['shaft_hole_interface'],source_url=row['source_url'],accessed=row['accessed'],
      proposed_additional_clearance=extra,clearance_status='ASSUMED_DESIGN_REQUIREMENT',fit_status=conflict,
      vendor_hole_coordinates_mm=None)
mech['hardware_candidate_revision']=REV
mech['hardware_candidate_envelopes']=envelopes
mech['hardware_handoff']=dict(status='BLOCKED',file='../hardware/v1/mechanical_handoff.md',
    instruction='Existing allocation fields and config/geometry.json preserved. Candidate dimensions do not approve holes or fit. No actual measured dimensions available.',
    board_requirement=dict(preferred='two compact MCU module carriers plus separate protected power/driver interfaces during bench stage',
        combined_board_candidate_xyz_mm=[96,76,1.6],central_cutout_candidate_xy_mm=[46,26],status='ASSUMED_NOT_PLACED',
        note='Central yaw servo/post corridor, antenna clearance and power module mounting must be collision-checked before PCB outline freeze. No inherited A0 board.'))
for joint in ['yaw','pitch']:
    mech['joints'][joint]['feedback_candidate']='FT90M-FB analog feedback; ADC electrical protection and multi-point calibration required'
    mech['joints'][joint]['feedback_status']='NOT_TESTED; actual angle remains ESTIMATED until calibrated feedback is validated'
write(mechanical_path,mech)

# Numbers below are WROOM module pad numbers, not ESP32 chip package pin numbers.
PAD={0:27,1:39,2:38,3:15,4:4,5:5,6:6,7:7,8:12,9:17,10:18,11:19,12:20,13:21,14:22,15:8,16:9,17:10,18:11,19:13,20:14,21:23,35:28,36:29,37:30,38:31,39:32,40:33,41:34,42:35,43:37,44:36,45:26,46:16,47:24,48:25}
motion={1:('VBAT_ADC','ADC1','100k/33k 1% +100nF; calibrate; max8.4=>2.084V'),2:('YAW_FB','ADC1','20k/10k +10nF +clamps; 5V=>1.667V'),4:('PITCH_FB','ADC1','as yaw; calibrated voltage-angle table'),5:('IMU_CS_N','SPI2','10k pull-up'),6:('IMU_SCLK','SPI2','8MHz target, short rigid-body route'),7:('IMU_MOSI','SPI2','3.3V'),8:('IMU_MISO','SPI2','3.3V'),9:('IMU_INT1','interrupt','DRDY latch hardware timestamp; 833Hz candidate ODR'),10:('ESTOP_N','input','NC actuator power-cut auxiliary status, pull-up own rail'),11:('ACTUATOR_ALLOW','output','pull-down; AND hardware watchdog, maintenance inhibit and latched local unlock'),12:('ALT_WHEEL_L_PWM','MCPWM','BRUSH only; PH/EN mode'),13:('ALT_WHEEL_R_PH','GPIO','BRUSH only'),14:('ALT_WHEEL_R_PWM','MCPWM','BRUSH only'),15:('YAW_PWM','LEDC','50Hz provisional; 1500us neutral; level shift5V'),16:('PITCH_PWM','LEDC','same; physical software endstops before enable'),17:('LINK_TX','UART1','460800 8N1 -> interactionGPIO47 via Ioff translator'),18:('LINK_RX','UART1','<-interactionGPIO44 via Ioff translator; 10k idle pullup'),21:('POWER_SDA','I2C0','400kHz max;3.3V 4.7k pullup; INA2190x45'),38:('POWER_SCL','I2C0','own motion rail pullup'),39:('FOC_TX_OR_ALT_ENC_L_A','UART2 / PCNT0','mutually exclusive profile; FOC physical level unverified'),40:('FOC_RX_OR_ALT_ENC_L_B','UART2 / PCNT0','mutually exclusive profile; x4 PPR not frozen'),41:('FOC_DIR_RESERVED_OR_ALT_ENC_R_A','GPIO / PCNT1','FOC half/full duplex unverified'),42:('ALT_ENC_R_B','PCNT1','3.3V encoder; open-drain/pushpull confirmation pending'),43:('ALT_WHEEL_L_PH','GPIO','ROM UART0 TX can pulse; hardware ACTUATOR_ALLOW stays low'),44:('WATCHDOG_KICK','GPIO','ROM UART0 RX input; external pulldown; supervisor timing unselected'),47:('HW_PERMIT_N','input','wired inhibit/status: USB/cradle/driver fault; exact gate circuit not frozen'),48:('LOCAL_ARM_BUTTON_N','input','pull-up/debounce; local unlock only; never automatic rearm')}
interaction={1:('CAM_SCCB_SDA','SCCB','pullup to camera IO rail; electrical translation pending'),2:('CAM_SCCB_SCL','SCCB','camera IO voltage pending'),**{n:('CAM_D'+str(n-4),'LCD_CAM','OV2640 DVP data; FPC pad UNKNOWN') for n in range(4,12)},12:('CAM_XCLK','LEDC','20MHz provisional; translate to camera IO voltage'),13:('CAM_PCLK','LCD_CAM','clock from sensor'),14:('CAM_VSYNC','LCD_CAM','frame timestamp'),15:('CAM_HREF','LCD_CAM','line valid'),16:('LCD_SCLK','SPI2','20MHz initial; 40MHz only after signal check'),17:('LCD_MOSI','SPI2','RGB565 eyes'),18:('LCD_DC','GPIO','3.3V'),21:('LCD_CS_N','SPI2','10k pull-up'),38:('AMP_ENABLE','GPIO','hardware pull-down; amp off through boot ROM UART43 output'),39:('LCD_BACKLIGHT','LEDC','3.3V BL input; waveform/current method verify'),40:('AUDIO_BCLK','I2S0','shared TX/RX synchronous clock'),41:('AUDIO_WS','I2S0','16kHz stereo slots, 32-bit slot initial'),42:('MIC_SD','I2S0 RX','single microphone LR strapped to GND'),43:('AMP_DIN','I2S0 TX','UART0 boot prints masked by AMP_ENABLE low'),44:('LINK_TX','UART1','->motionGPIO18; no UART0 console after boot'),47:('LINK_RX','UART1','<-motionGPIO17; isolated power domains'),48:('FUNCTION_BUTTON_N','input','short dialogue, double goal-cancel, long settings only supported maintenance')}
rows=[]
for domain,pins in [('MOTION',motion),('INTERACTION',interaction)]:
    for gpio,(sig,periph,note) in pins.items():rows.append(dict(revision=REV,status='CANDIDATE_NOT_RELEASED',domain=domain,module='ESP32-S3-WROOM-1-N16R8',module_pad=PAD[gpio],gpio=gpio,signal=sig,peripheral=periph,logic_voltage='3.3V unless explicit protected translation',notes=note))
    for gpio,sig in [(19,'USB_D_MINUS'),(20,'USB_D_PLUS'),(0,'BOOT_N_TESTPOINT')]:rows.append(dict(revision=REV,status='CANDIDATE_NOT_RELEASED',domain=domain,module='ESP32-S3-WROOM-1-N16R8',module_pad=PAD[gpio],gpio=gpio,signal=sig,peripheral='USB Serial/JTAG' if gpio!=0 else 'strap',logic_voltage='3.3V / USB',notes='Separate hidden pogo connector; no extra exterior USB. BOOT low only in supported maintenance.'))
    rows.append(dict(revision=REV,status='CANDIDATE_NOT_RELEASED',domain=domain,module='ESP32-S3-WROOM-1-N16R8',module_pad=3,gpio='EN',signal='CHIP_EN_AND_LCD_RESET' if domain=='INTERACTION' else 'CHIP_EN',peripheral='reset',logic_voltage='3.3V own domain',notes='10k/1uF EN timing candidate; interaction LCD_RST follows EN, runtime GC9A01 software reset (no extra GPIO); confirm vendor reset timings.'))
    for pad,signal in [(1,'GND'),(2,'3V3'),(40,'GND'),(41,'GND_EXPOSED_PAD')]:
        rows.append(dict(revision=REV,status='CANDIDATE_NOT_RELEASED',domain=domain,module='ESP32-S3-WROOM-1-N16R8',module_pad=pad,gpio='',signal=signal,peripheral='POWER',logic_voltage='own domain 3.3V / shared GND',notes='Pad2 local10uF+100nF candidate; pads1/40/41 to solid ground; exposed pad land/stencil per manufacturer.'))
    for gpio in [3,35,36,37,45,46]:
        rows.append(dict(revision=REV,status='CANDIDATE_NOT_RELEASED',domain=domain,module='ESP32-S3-WROOM-1-N16R8',module_pad=PAD[gpio],gpio=gpio,signal='RESERVED_PSRAM_NC' if gpio in [35,36,37] else 'RESERVED_BOOT_STRAP',peripheral='RESERVED',logic_voltage='Do not externally drive',notes='N16R8 internal octalPSRAM occupies35/36/37; strap3/45/46 left to documented default boot configuration, no peripheral attached.'))
for domain in ['MOTION','INTERACTION']:
    gp=[r['gpio'] for r in rows if r['domain']==domain and r['peripheral'] not in ['POWER','RESERVED']];assert len(gp)==len(set(gp))
    assert not set(gp)&{3,35,36,37,45,46}
    pads=[r['module_pad'] for r in rows if r['domain']==domain];assert sorted(pads)==list(range(1,42))
version=H/'interfaces/pinmap_V1-H0.1.csv'
with version.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
pinroot=R/'hardware/pinmap.csv';old=H/'interfaces/pinmap_before_V1.csv'
if pinroot.exists() and not old.exists():shutil.copy2(pinroot,old)
shutil.copy2(version,pinroot)

electrical=dict(schema_version='1.0',revision=REV,status='PROTOTYPE_CANDIDATE_NOT_RELEASED',physical_tests='NOT_TESTED',
 mechanical_contract='mechanical_interfaces.json',pinmap='../hardware/v1/interfaces/pinmap_V1-H0.1.csv',actuator_count=4,mcu_count=2,
 route=dict(primary='FOC4012 exact SKU/driver protocol blocked',alternative='FIT0521 + Pololu4035 + separate regulated5V; different plant/current loop and no gain reuse'),
 power_domains={'battery':{'chemistry':'Li-ion2S','nominal_V':7.2,'charge_max_V':8.4,'candidate':'ANSMANN2447-0105','cutoff_V':None,'balance':None,'regenerative_current_allowed_A':None},
 'motion_3v3':{'candidate':'DFR0570','separate_branch':True,'qualified_current_A':None},'interaction_3v3':{'candidate':'DFR0570','separate_branch':True,'qualified_current_A':None},
 'servo_5v':{'candidate':'DFR0753','two_servos':True,'peak_design_A':2.2,'measured':False},'wheel_bus':{'primary_voltage_V':None,'alternative_voltage_V':5,'regen_clamp_V':None},
 'charging':{'candidate':'DFR0564','input':'USB-C5V only, CC-advertisement current limit circuit not frozen','system_on':False,'requires_cradle':True,'balanced':False,'protection_not_equivalent_to_balance':True,'release':'BLOCKED'}},
 shared_battery_note='Separate regulated domains are not independent safety redundancy; BMS, battery and ground are common.',
 motion_interaction_link={'physical':'3.3V full duplex UART with two opposing Ioff translators','baud':460800,'format':'8N1','max_payload_bytes':96,'crc':'CRC-16/CCITT-FALSE','crc_check_123456789_hex':'29b1','heartbeat_ms':50,'heartbeat_loss_ms':200,'maximum_motion_lease_ms':300,'details':'../hardware/v1/link_protocol.md'},
 coordinate_and_units={'linear_velocity':'m/s +Y forward','body_forward_tilt':'rad around -X','yaw':'rad +Z left','head_pitch':'rad +X up','wheel_torque':'SI Nm only after calibration; raw FOC integer explicitly opaque','encoder':'signed accumulated counts, cpr field null until one-revolution measurement'},
 sensor={'imu':'LSM6DSOX body fixed; SPI2 8MHz candidate +INT1;833Hz candidate ODR','loop_hz_target':500,'sample_age_limit_ms_target':3,'actual_bandwidth_and_delay_test':'NOT_TESTED'},
 head={'candidate':'FT90M-FB','pwm_us':[500,2500],'vendor_travel_deg':280,'commissioning_start_us':1500,'yaw_joint_deg':[-60,60],'pitch_joint_deg':[-20,25],'ratio_servo_to_joint':None,'feedback_ADC':'20k top/10k bottom +10nF and protection, not validated circuit','position_quality':'ESTIMATED until multi-point loaded calibration, feedback range and stale/saturation checks pass'},
 safety={'boot':'DISARMED; both wheel and servo rails inhibited','rearm':'physical LOCAL_ARM plus fresh checks; no automatic fault recovery','stop_motion':'zero navigation goal while healthy local balance continues','disarm':'outputs disabled, robot cannot stand unsupported','interaction_loss':'zero goal on stale session/heartbeat/lease; motion IMU loop remains local','critical_fault':'latched outputs off; external catch protection required','physical_estop':'independent NC power-cut path for actuator domain; detailed rated components unresolved','firmware_reset':'only supported cradle; common dialogue button never resets motion MCU'},
 resources={'motion':'SPI2 IMU, UART1 interlink, UART2 FOC OR two PCNT x4 plus MCPWM brushed, LEDC2 servo, I2C0 power; ADC1 only',
 'interaction':'LCD_CAM DVP, SPI2 LCD, I2S0 duplex mic/DAC, UART1, LEDC XCLK+BL, SCCB; DMA/PSRAM simultaneous stress untested',
 'reserved':['GPIO35/36/37 octal PSRAM','GPIO19/20 USB','GPIO0 maintenance strap','GPIO3/45/46 left unused straps'],
 'reset_note':'LCD_RST wired interaction EN; no unallocated 28th application GPIO. AMP muted in hardware during UART0 boot log.'},
 unfrozen_device_interfaces={'camera_24pin':None,'camera_supply_and_IO_voltage':None,'audio_off_domain_I2S_protection':'Requires Ioff buffer or verified module power-off input tolerance; not qualified','wheel_FOC_physical_connector':None,'battery_cell_balance_interface':None},
 hardware_freeze=False,pcb_release=False,procurement_release=False)
electrical_path=R/'contracts/electrical_interfaces.json'
if electrical_path.exists():
    existing=json.loads(electrical_path.read_text())
    if existing.get('revision')!=REV:raise RuntimeError('An independently written electrical contract exists; merge review required, not overwritten')
write(electrical_path,electrical)
write(H/'reports/interface_validation.json',{'status':'PASS','scope':'serialization, module GPIO uniqueness/reserved GPIO check, actuator/MCU counts only; NOT electrical or fit approval','rows':len(rows),'revision':REV,'mechanical_allocations_preserved':True})
print(f'Published {len(rows)} candidate pad rows; allocations preserved; procurement and PCB remain BLOCKED.')
