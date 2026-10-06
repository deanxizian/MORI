"""Source-backed head harness addendum. Never edits contracts or mechanical files."""
from pathlib import Path
import csv,json,hashlib,shutil,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];S=HERE/'sources'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,j:p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((HERE/'sources_manifest.json').read_text())
for row in manifest:
    if row['status']=='PASS':assert sha(S/row['file'])==row['sha256']
feetech=ROOT/'hardware/v1_2/harness_evidence_20261002/sources/feetech_SCS0009_A0.pdf'
assert sha(feetech)=='b8ce3f28a8c12d2ad9dee697087eae03eb716219016b48be9a7e1856755213c6'
shutil.copy2(feetech,S/'FEETECH_cached_20261002.pdf')
receipt=[];out=HERE/'received_mechanical';out.mkdir(exist_ok=True)
for name in ['HEAD_HARNESS_REQUIREMENTS.md','loop_source_solids.json','head_connectivity.json']:
    source=ROOT/'mechanical/studies/prearrival_finish/head_harness'/name
    shutil.copy2(source,out/name)
    receipt.append(dict(source=str(source.relative_to(ROOT)),sha256=sha(source),snapshot=str((out/name).relative_to(ROOT))))
rows=[]
def pin(ref,number,function,v1,v11,notes,source='CAM_V1.pdf p1 / CAM_V11.pdf p1'):
    rows.append(dict(reference=ref,pin=number,function=function,V1=v1,Rev1p1=v11,evidence='VENDOR_DOCUMENTED',source=source,physical_cavity_view='BLOCKED',notes=notes))
for n,signal in [(1,'CAM_RX / GPIO44'),(2,'CAM_TX / GPIO43'),(3,'CAM local 3V3'),(4,'GND')]:
    pin('CAM J11',n,signal,signal,signal,'MORI motion J5 same-number correspondence; pin3 only remote-side level-shifter reference, not CAM main feed')
for n,signal in [(1,'SCL / GPIO7'),(2,'SDA / GPIO8'),(3,'CAM local 3V3'),(4,'GND')]:pin('CAM J6',n,signal,signal,signal,'I2C; do not substitute for J11')
for n,signal in [(1,'PA_OUTL+'),(2,'PA_OUTL-')]:pin('CAM J5 SPK',n,signal,signal,signal,'Bridge output; neither conductor is GND; not battery connector J4')
camera=[
 (1,'NC'),(2,'AGND'),(3,'TWI_SDA / GPIO8'),(4,'AVDD 2V8'),(5,'TWI_CLK / GPIO7'),(6,'RESET'),(7,'CAM_VSYNC / GPIO17'),(8,'CAM_PWDN / EXIO3'),(9,'CAM_HREF / GPIO18'),(10,'DVDD 1V5'),(11,'DOVDD 2V8'),(12,'CAM_D7 / GPIO21'),(13,'CAM_XCLK / GPIO38'),(14,'CAM_D6 / GPIO39'),(15,'DGND'),(16,'CAM_D5 / GPIO40'),(17,'CAM_PCLK / GPIO41'),(18,'CAM_D4 / GPIO42'),(19,'CAM_D0 / GPIO45'),(20,'CAM_D3 / GPIO46'),(21,'CAM_D1 / GPIO47'),(22,'CAM_D2 / GPIO48'),(23,'Y1 AF_VDD'),(24,'Y0 AF_GND')]
for n,signal in camera:
    a=b=signal;note='Schematic electrical pin only; no cable orientation or extension approval'
    if n==2:a='AGND via R5 0R to GND';b='CAM_AGND via R53 0R to GND'
    if n==4:a='2V8 direct';b='2V8 via R50 5.1 ohm'
    if n==6:note+='; R10 10k pullup to3V3, C20 100nF'
    if n==23:a=b='3V3 through R2 0R; AF suitability not qualified'
    if n==24:a='GND through R1 0R';b='R1 NC; no populated ground link shown'
    pin('CAM J2 CAMERA',n,signal,a,b,note)
for n,signal in [(1,'GND'),(2,'VCC / MORI H_VM 6V'),(3,'Signal TTL / H_BUS')]:
    pin('SCS0009 p4 tail',n,signal,signal,'NOT_APPLICABLE','p8 P2/P5 example reverses DATA/GND numbering; physical mating map must be resolved','FEETECH A/0 p4 and p8')
with (HERE/'head_interface_pinmap_revA.csv').open('w',newline='')as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def field(value,source,scope='VENDOR_DOCUMENTED'):
    return dict(value=value,evidence=scope,source=source,status='PASS'if value is not None else'BLOCKED')
unknown=lambda reason:dict(value=None,evidence='ASSUMED / UNSELECTED',status='BLOCKED',missing_reason=reason)
evidence=dict(revision='HEAD-HARNESS-A7',date='2026-10-03',scope='Documented interfaces and bounded catalogue candidates only; no physical release',
 source_retrievals=manifest,feetech_reuse=dict(path=str(feetech.relative_to(ROOT)),sha256=sha(feetech),retrieval_date='2026-10-02',current_retry='BLOCKED_TLS_EOF',cached_file='sources/FEETECH_cached_20261002.pdf'),
 pinmap='head_interface_pinmap_revA.csv',received_mechanical=receipt,interfaces={
 'camera_OV3660':{
  'product':field('Waveshare CAM33700 / ESP32-S3-CAM-OV3660','CAM_docs.html'),
  'connector_circuits':field(24,'CAM_V1.pdf p1 J2'),
  'pitch_mm':field(.5,'CAM_V1.pdf p1 J2'),
  'connector_description':field('rear flip / 2.0H','CAM_V1.pdf p1 J2; 2.0H is connector height, not FPC thickness'),
  'complete_fpc_sku':unknown('Official full camera FPC/module SKU not located'),
  'complete_fpc_effective_length_mm':unknown('Visible photo tail10.5mm is not full length'),
  'full_width_mm':unknown('No dimensioned camera flex drawing'),
  'tail_width_mm':unknown('Do not derive from circuit count times pitch'),
  'thickness_mm':unknown('Connector height is not cable thickness'),
  'stiffener_mm':unknown('No selected drawing'),
  'contact_length_mm':unknown('No selected drawing'),
  'insertion_length_mm':unknown('No actual connector model'),
  'contact_side_and_pin1_view':unknown('Schematic symbol is not mated face view'),
  'minimum_static_bend_radius_mm':unknown('No supplier limit'),
  'approved_extension_sku':unknown('No exact supported CAM33700 extension found in inspected official material'),
  'maximum_extended_DVP_length_mm':unknown('No validated timing/SI limit for selected mode'),
  'mechanical_straight_lower_bound_mm':field(58.23,'received_mechanical/HEAD_HARNESS_REQUIREMENTS.md','ASSUMED / COMPUTED_ENVELOPE_BOUND'),
  'actual_installed_route_length_mm':unknown('Straight line obstructed and final anchors unknown'),
  'fit_status':'BLOCKED','physical_status':'NOT_TESTED'},
 'CAM_UART_SH':{
  'schematic_series':field('SH1.0 4P horizontal','CAM_V1.pdf p1 J11'),
  'actual_board_header_mpn':unknown('Series description does not identify manufacturer or full header'),
  'catalogue_housing_candidate':field('JST SHR-04V-S','JST_SH.pdf p2'),
  'catalogue_contact_candidate':field('JST SSH-003T-P0.2-H','JST_SH.pdf p2'),
  'catalogue_housing_width_axislength_thickness_mm':field([5.0,5.0,2.8],'JST_SH.pdf p2; nominal, no cable tail'),
  'catalogue_awg_range':field([32,28],'JST_SH.pdf p1/p2'),
  'catalogue_insulation_od_mm':field([.4,.8],'JST_SH.pdf p1/p2'),
  'actual_mated_exit_xyz_mm':unknown('No board-specific header drawing/pose and matched housing confirmed'),
  'actual_wire_sku_od_bend_life':unknown('No selected stock harness'),
  'compatibility':'BLOCKED','physical_status':'NOT_TESTED'},
 'CAM_SPK_GH':{
  'schematic_series':field('GH1.25 2P vertical','CAM_V1.pdf p1 J5 / CAM_V11.pdf p1 J5'),
  'catalogue_housing_candidate':field('JST GHR-02V-S','JST_GH.pdf p3'),
  'catalogue_contact_candidate':field('JST SSHL-002T-P0.2','JST_GH.pdf p2'),
  'catalogue_housing_width_axislength_thickness_mm':field([3.75,5.7,4.15],'JST_GH.pdf p3; nominal, no cable tail'),
  'catalogue_mated_top_entry_reference_height_mm':field(7.3,'JST_GH.pdf p2; catalogue pair only, not actual CAM board'),
  'catalogue_awg_range':field([30,26],'JST_GH.pdf p1/p2'),
  'catalogue_insulation_od_mm':field([.76,1.0],'JST_GH.pdf p1/p2'),
  'actual_mpn_and_mated_exit':unknown('Board manufacturer and matched header not established'),
  'actual_wire_sku_od_bend_life':unknown('No selected stock harness'),
  'compatibility':'BLOCKED','physical_status':'NOT_TESTED'},
 'CAM_USB_power':{
  'board_cc_rd_ohm':field([5100,5100],'CAM_V1.pdf / CAM_V11.pdf Type_C1, R21/R23'),
  'board_vbus_to_vsys_diode':field('D3 MBR230LSFT1G','CAM_V1.pdf / CAM_V11.pdf Type_C1'),
  'mori_supply_function':field('controlled 5V_CAM and GND','wiring_P5R7; unchanged'),
  'actual_plug_cable_mpn_dimensions':unknown('No selected internal USB power plug/cable'),
  'source_CC_implementation':unknown('Select and verify cable/source topology'),
  'wire_drop_and_current_limit':unknown('Actual length/AWG/contact resistance not established'),
  'physical_status':'NOT_TESTED'},
 'SCS0009':{
  'connector_description':field('5264-3P','FEETECH A0 p4'),
  'wire_length_nominal_mm':field(150,'FEETECH A0 p4; datum/tolerance unspecified'),
  'pitch_mm':field(2.5,'FEETECH A0 p4 printed dimension; not assumed2.54'),
  'partial_side_dimensions_mm':field({'length':8.9,'depth':4.7,'other_local_callouts':[3.9,3.3,4.2]},'FEETECH A0 p4; not complete envelope'),
  'full_housing_width_mm':unknown('Not dimensioned in cited view'),
  'complete_mating_part_numbers':unknown('5264 label alone is insufficient'),
  'physical_pin_order':unknown('Resolve p4 1G/3S versus p8 1DATA/3G numbering and views'),
  'wire_awg_od_dynamic_radius':unknown('Not specified in retrieved A0'),
  'included_splitter_board_geometry':unknown('Package photo alone does not define current SKU content or full geometry'),
  'upstream_two_servo_load_qualification':'NOT_TESTED','physical_status':'NOT_TESTED'},
 'LCD_FFC':{
  'electrical_pinmap_source':'hardware/v1_2/prearrival_20261002/ffc_pinmap.csv',
  'mechanical_external_socket':'Display_PCB Connector_108 / electrical L1; not Connector_107',
  'stock_description':field('18P /0.5mm /200mm /same-side contacts','hardware/v1_2/harness_evidence_20261002/sources/waveshare_LCD35079.html'),
  'actual_mated_contact_sides_and_pin1':unknown('Same-side cable does not alone establish1to1 mating'),
  'full_width_thickness_stiffener_bend':unknown('No full FFC drawing/SKU'),
  'physical_status':'NOT_TESTED'}},
 source_visual_review={'CAM_V1':'all four rendered quadrants, including J2/J11/J5/USB','CAM_V11':'all four rendered quadrants','FEETECH_A0':'p4 and p8','JST_SH':'p1,p2,p3 using PDFKit','JST_GH':'p1,p2,p3 using PDFKit','rendering_note':'Poppler omitted JST text due Adobe-Japan1 maps; discarded for dimensional reading. PDFKit rendered and extracted readable text.'},
 overall_complete_harness_status='BLOCKED',physical_tests='NOT_TESTED',formal_files_modified=False,mechanical_main_modified=False,messages_to_suppliers_sent=False,purchase_release='BLOCKED')
dump(HERE/'evidence.json',evidence)
files={str(p.relative_to(ROOT)):sha(p)for p in HERE.rglob('*')if p.is_file()and p.name!='delivery_manifest.json'and '__pycache__'not in str(p)}
dump(HERE/'delivery_manifest.json',dict(status='PASS',scope='File integrity only',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files))
print('Source-backed pin rows:',len(rows),'; complete harness BLOCKED; no formal edits.')
