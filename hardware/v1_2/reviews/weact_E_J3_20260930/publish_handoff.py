# -*- coding: utf-8 -*-
"""Publish verified native source handoff; no mechanical/model/firmware writes."""
from update_native_P5R7 import *
from datetime import datetime, timezone
import copy

REV='V1.2-H0.5-P5R7'
review_rel=str(HERE.relative_to(ROOT))
verified={kind:json.loads((HERE/'reports'/kind/'verification.json').read_text())for kind in ['motion','rear']}
assert all(v['status']=='PASS' for v in verified.values())
for kind,v in verified.items():assert sha(paths(kind)[2])==v['pcb_sha256']
previous=H/'handoff/mechanical_P5R6.json'
handoff=json.loads(previous.read_text())
handoff.update(revision=REV,generated_utc=datetime.now(timezone.utc).isoformat(),
    mechanical_revision_read='M1.42 frozen socket candidate; M1.43 evolving assembly was not modified or fully requalified',
    mechanical_source_sha256=sha(ROOT/'contracts/mechanical_interfaces.json'),
    change_scope='Motion U100 E1-E8 native X+2.54mm, R19 horizontal relocation, R9 Y+3.25mm corridor move and signal routing; rear J3 B.Cu/180deg/Y+1.70mm and local routes. Power P5R6 and IMU P5R4 unchanged.',
    full_mated_fit='BLOCKED',physical_tests='NOT_TESTED')
board_inputs={};native_boards={}
for kind in ['motion','rear']:
    name,d,p=paths(kind);oldname,_,_=paths(kind,'P5R6')
    b=k.LoadBoard(str(p));native_boards[name]=b
    entry=handoff['boards'].pop(oldname)
    entry['native_project']=str((d/(name+'.kicad_pro')).relative_to(ROOT));entry['pcb_sha256']=sha(p)
    entry['native_checks']=str((HERE/'reports'/kind/'verification.json').relative_to(ROOT))
    entry['inner_signal_tracks']=sum(not isinstance(t,k.PCB_VIA) and t.GetLayer()not in [k.F_Cu,k.B_Cu]for t in b.GetTracks())
    assert entry['inner_signal_tracks']==0
    fp={f.GetReference():f for f in b.GetFootprints()}
    for item in entry['placements']:
        ref=item['reference'];f=fp[ref];item['board']=name
        item['xy_mm']=xy(f.GetPosition());item['rotation_deg']=f.GetOrientationDegrees()
        item['side']='B'if f.IsFlipped()else'F';item['footprint']=f.GetFPID().GetUniStringLibId()
        if ref in (['R19','R9','U100']if kind=='motion'else['J3']):
            item['fab_projection_mm']=rect(f)
            bounds=[list(rect(f))]
            for q in f.Pads():
                box=q.GetBoundingBox();bounds.append([k.ToMM(box.GetX()),k.ToMM(box.GetY()),k.ToMM(box.GetRight()),k.ToMM(box.GetBottom())])
            item['native_body_and_pad_bounds_mm']=[min(x[0]for x in bounds),min(x[1]for x in bounds),max(x[2]for x in bounds),max(x[3]for x in bounds)]
            item['bounds_basis']='Native Fab/pad union, not a complete populated height or mating envelope'
    for item in entry['connectors']:
        f=fp[item['ref']];item['xy_mm']=xy(f.GetPosition());item['rotation_deg']=f.GetOrientationDegrees()
        item['side']='B'if f.IsFlipped()else'F'
        for pin in item['pins']:
            q=next(q for q in f.Pads()if q.GetNumber()==str(pin['pin']))
            pin.update(revision=REV,board=name,xy_mm=xy(q.GetPosition()),component_side=item['side'])
            assert pin['net']==q.GetNetname()
        if kind=='rear'and item['ref']=='J3':
            item['native_body_and_pad_bounds_mm']=[6.5,19.5,16.4,24]
            item['actual_housing_projection_mm']=[6.5,19.5,16.4,24]
            item['insertion_axis_native_xyz']=[0,0,1]
            item['removal_axis_native_xyz']=[0,0,-1]
            item['wire_bend_clearance_mm']=None
            item['mating_clearance']='Frozen nominal envelope/sweep screening PASS; current assembly/wires/hands NOT_TESTED'
    bare=HERE/'previews'/kind/(name+'_BARE_BOARD.step')
    if not bare.exists():
        cmd=[CLI,'pcb','export','step','--force','--board-only','--user-origin','0x0mm','-o',str(bare),str(p)]
        cp=subprocess.run(cmd,capture_output=True,text=True)
        dump(HERE/'reports'/kind/'bare_step_command.json',{'argv':cmd,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
        assert cp.returncode==0
    entry.update(bare_STEP=str(bare.relative_to(ROOT)),bare_STEP_sha256=sha(bare),bare_STEP_is_populated_assembly=False,
        bare_STEP_note='Fresh native P5R7 hole geometry. Bare substrate only; no complete module/socket/connector model claim.')
    handoff['boards'][name]=entry
    for suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru']:
        q=d/(name+suffix);board_inputs[str(q.relative_to(ROOT))]=sha(q)
    for q in d.rglob('*'):
        if q.is_file() and (q.suffix in ['.kicad_mod','.kicad_sym'] or q.name in ['fp-lib-table','sym-lib-table']):
            board_inputs[str(q.relative_to(ROOT))]=sha(q)

alignment=json.loads((HERE/'weact_alignment_audit.json').read_text())
handoff['weact_assembly']={
 'user_confirmation':str((HERE/'user_decisions.json').relative_to(ROOT)),
 'component_side':'UP','male_pin_direction':'DOWN from core underside; replace/reorient source STEP headers rather than flipping the whole core',
 'core_model_source':str((H/'sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 3D.step').relative_to(ROOT)),
 'core_model_sha256':alignment['official_STEP_source_sha256'],
 'core_STEP_to_robot_rotation':alignment['component_up_R_STEP_to_world'],
 'core_STEP_to_robot_translation_xy_mm':alignment['component_up_translation_xy_mm'],
 'core_STEP_to_robot_translation_z_mm':None,
 'carrier_native_to_robot_xy':'Xrobot=Xnative-35; Yrobot=-26.5-Ynative for the received fixed carrier datum. Mechanical owns final rigid mounting transform.',
 'pin_coordinate_audit':str((HERE/'weact_68_pin_alignment.csv').relative_to(ROOT)),
 'pin_coordinate_residual_max_mm':alignment['maximum_nominal_to_STEP_residual_mm'],
 'pin_coordinate_status':'PASS','physical_mating_status':'NOT_TESTED',
 'core_flipped_candidate_retired':'P1.1 VB overlaps B2 GND in the former component-down candidate; that assembly transform is invalid even though hole sets overlap.',
 'E_pads':verified['motion']['E_pad_change'],
 'E_pin_signals':alignment['E_pin_mapping'],
 'E_carrier_connection':'Only E7 /NRST is connected. Other E pads are NC on the carrier; core circuits still exist on those pins.',
 'socket_candidates':[
  {'mpn':'61303021821','quantity':2,'native_centres_xy_mm':[[25.15,31.47],[25.15,3.53]],'body_xyz_mm':[38.6,5.08,8.5],'solder_tail_mm':3.1},
  {'mpn':'61300821821','quantity':1,'native_centres_xy_mm':[[36.2,23.09]],'body_xyz_mm':[5.08,10.66,8.5],'solder_tail_mm':3.1},
  {'mpn':'61300821121','quantity':1,'use':'Core E straight male header candidate','body_xyz_mm':[5.08,10.16,2.54],'mating_pin_length_mm':6,'solder_tail_mm':3}],
 'socket_datum':'Dimensions are vendor catalogue values, not measured parts. Male/female contact engagement and tolerance stack remain unqualified.',
 'carrier_hole_diameter_mm':1.0,'hole_basis':'Preserved native carrier holes; female catalogue recommends 1.02 +/-0.15mm. Physical soldering and plating fit NOT_TESTED.',
 'nominal_board_face_gap_candidate_mm':11.04,'gap_basis':'8.5mm female housing +2.54mm male insulator only; do not reuse the former inverted-core Z pose or label this full assembly fit.',
 'mechanical_checks_required':['Core upper component/USB/boot/reset clearance in component-up orientation','Male pin installation side and header-only transforms','Female solder tails and underside SMD/structure clearance','E7 identity and alignment; A-D numbered identity, not set overlap','Insertion/removal paths, actual contact depth, retention and full tolerance stack','Accessible SWD method after E changes from right-angle to downward straight header']}
screen=json.loads((HERE/'j3_geometry_screen.json').read_text())
selected=next(c for c in screen['candidates']if c['side']=='B'and c['rotation_deg']==180 and c['native_pad1_xy_mm']==[14.45,21.2])
handoff['rear_J3']={'board':'MORI_rear_P5R7','reference':'J3','mpn':'B4B-PH-K-S(LF)(SN)',
 'mate':'PHR-4','contact':'SPH-002T-P0.5S','side':'B','rotation_deg':180,'native_pad1_xy_mm':[14.45,21.2],
 'top_view_left_to_right_pins':[4,3,2,1],
 'numbered_signals':{'1':'MASTER_RETURN -> power J19.1','2':'GND -> power J19.2','3':'LOOP_3V3 -> motion J8.1','4':'CLR_N -> motion J8.2'},
 'nominal_screen':selected,'screen_source_blend':screen['assembly'],'screen_source_sha256':screen['assembly_sha256'],
 'screen_limits':screen['limits'],'integrated_mechanical_fit':'BLOCKED','physical_tests':'NOT_TESTED'}
handoff['source_manifest']=board_inputs
handoff['review']=review_rel+'/README.md'
handoff['procurement_release']=False;handoff['manufacturing_release']=False
dump(H/'handoff/mechanical_P5R7.json',handoff)

# Native-derived updated connector coordinates. Signal definitions are unchanged.
oldcsv=H/'layout_P5R6/connector_pinmap.csv'
with oldcsv.open(encoding='utf-8-sig',newline='')as h:ports=list(csv.DictReader(h))
for row in ports:
    for kind in ['motion','rear']:
        oldname,_,_=paths(kind,'P5R6');name,_,_=paths(kind)
        if row['board']!=oldname:continue
        f=next(f for f in native_boards[name].GetFootprints()if f.GetReference()==row['reference'])
        q=next(q for q in f.Pads()if q.GetNumber()==row['pin'])
        assert row['net']==q.GetNetname()
        row.update(board=name,revision=REV,xy_mm=json.dumps(xy(q.GetPosition())),component_side='B'if f.IsFlipped()else'F')
with (HERE/'connector_pinmap_P5R7.csv').open('w',encoding='utf-8-sig',newline='')as h:
    w=csv.DictWriter(h,list(ports[0]));w.writeheader();w.writerows(ports)

# Publish a compact versioned wiring supplement; leave the historical workbook intact.
wiring=H/'wiring_P5R7';wiring.mkdir(exist_ok=True)
for filename in ['01_端口总表.csv','02_端口逐针定义.csv','03_逐针接线表.csv','04_线束汇总.csv','05_维护与外设.csv','06_屏幕FFC待核对.csv']:
    with (H/'wiring_P5R6'/filename).open(encoding='utf-8-sig',newline='')as h:rows=list(csv.DictReader(h))
    for row in rows:
        for key,value in row.items():
            row[key]=value.replace('MORI_motion_P5R6','MORI_motion_P5R7').replace('MORI_rear_P5R6','MORI_rear_P5R7')
        if row.get('board_id')=='MORI_rear_P5R7'and row.get('接口')=='J3':
            row['安装面']='B'
            if '插入方向'in row:row['插入方向']='从板背面向板插入；拔出方向 −Z，须结合机械安装变换'
            if '板端坐标mm'in row:
                match=next(x for x in ports if x['board']=='MORI_rear_P5R7'and x['reference']=='J3'and x['pin']==row['针号'])
                row['板端坐标mm']=json.dumps([json.loads(match['xy_mm'])])
            if '注意'in row:row['注意']+='；P5R7 顶视图左到右4/3/2/1，按针号确认，不按旧板孔位置或线色接线。'
    with (wiring/filename).open('w',encoding='utf-8-sig',newline='')as h:
        w=csv.DictWriter(h,list(rows[0]));w.writeheader();w.writerows(rows)
(wiring/'README.md').write_text('''# P5R7 端口与接线增补

当前组合：motion P5R7、rear P5R7、power P5R6、IMU P5R4。各编号对应的信号、MCU GPIO 和线束对端保持；实物均 NOT_TESTED。

- 运动板 WeAct 元件面朝上，所有排针从背面向下；E 孔阵列 X+2.54 mm，只有 E7/NRST 接入载板。E 向下后，原来的顶部弯针维护方式不能直接沿用；SWD 可接触性由机械复核。
- 后板 J3 在 B 面，180°，原生1号孔 (14.45,21.20) mm；顶视图从左到右4、3、2、1。1=MASTER_RETURN、2=GND、3=LOOP_3V3、4=CLR_N。
- 当前 CSV 已同步板号、J3 面向和坐标；P5R6 工作簿保留作历史记录，不作为本次装配方向依据。

原生几何、逐针数据及未闭合事项见 [交接记录](../reviews/weact_E_J3_20260930/README.md)。原理图保留的 SW1 与整机已取消的外露开关存在单独的功能交接事项；本次局部插合修正不表示物理断电/急停已闭合。
''')

manifest={'revision':REV,'native_inputs':board_inputs,'checks':verified,
 'unchanged_board_checks':{'power':'hardware/v1_2/layout_P5R6/reports/power/drc.json','imu':'hardware/v1_2/layout_P5R6/reports/imu/drc.json'},
 'unchanged_board_checks_note':'Historical checks, not rerun in this scoped E/J3 correction; source board hashes remain those of the received P5R6/P5R4 handoff.',
 'mechanical_handoff':'hardware/v1_2/handoff/mechanical_P5R7.json','manufacturing_release':False,'physical_tests':'NOT_TESTED'}
dump(HERE/'verification.json',manifest)

# Snapshot and atomically advance only hardware-owned contracts and the pinmap.
snap=HERE/'sources/pre_publish';snap.mkdir(exist_ok=True)
for rel in ['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv']:
    q=ROOT/rel;dest=snap/q.name
    if not dest.exists():dest.write_bytes(q.read_bytes())
def atomic_json(path,value):
    tmp=path.with_name(path.name+'.P5R7.tmp');dump(tmp,value);tmp.replace(path)
components=json.loads((ROOT/'contracts/components.json').read_text())
assert components['revision']=='V1.2-H0.5-P5R6'
components['revision']=REV;components['date']='2026-10-01'
components['layout_P5R7_E_J3_review']={'source':review_rel+'/README.md','native_checks':review_rel+'/verification.json','mechanical_handoff':'hardware/v1_2/handoff/mechanical_P5R7.json','scope':handoff['change_scope'],'physical_tests':'NOT_TESTED'}
for row in components['components']:
    if isinstance(row.get('schematic_references'),list):
        row['schematic_references']=[s.replace('MORI_motion_P5R6','MORI_motion_P5R7').replace('MORI_rear_P5R6','MORI_rear_P5R7')for s in row['schematic_references']]
    if row['id']=='motion_mcu':
        row['schematic_references']=['MORI_motion_P5R7:U100']
        row['notes']+=' P5R7: component side UP, all pins DOWN; E corrected +2.54mm native X, E7 NRST only. Correct upper stack and SWD access pending mechanical integration.'
    elif row['id']=='carrier_pcb':
        row['full_model']='MORI_motion_P5R7 + MORI_imu_P5R4 + MORI_power_P5R6 + MORI_rear_P5R7'
        row['board_revision']='motion/rear:P5R7; power:P5R6; imu:P5R4'
        row['interface']='Native Edge.Cuts/holes/connectors: hardware/v1_2/handoff/mechanical_P5R7.json'
    elif row['id']=='p4_motion_module_sockets':
        row['full_model']='Catalogue candidates: 61303021821 x2 +61300821821 x1; core E male61300821121 x1'
        row['board_revision']='P5R7';row['source_date']='2026-09-30'
        row['shaft_hole_interface']='2.54mm pitch; corrected P5R7 A-E numbered array, see handoff'
        row['interface']='hardware/v1_2/handoff/mechanical_P5R7.json#/weact_assembly'
        row['notes']='Female housing8.5mm, tail3.1mm; exact catalogue candidates, not ordered or physically qualified. A-D male headers supplied/assembly details and contact stack pending. Do not reuse inverted-core mechanical candidate. Quote/stock still unknown.'
        row['data_status']='VENDOR_DOCUMENTED';row['dimensions_mm']=None
        row['missing']=['Domestic quote/stock and actual core supplied-header option','Component-up full stack and SWD/removal clearance','Actual solder/contact depth, retention and tolerance qualification']
electrical=json.loads((ROOT/'contracts/electrical_interfaces.json').read_text())
assert electrical['revision']=='V1.2-H0.5-P5R6'
electrical['revision']=REV;electrical['mechanical_handoff']='hardware/v1_2/handoff/mechanical_P5R7.json'
electrical['layout_validation']=review_rel+'/verification.json';electrical['schematic_validation']=review_rel+'/verification.json'
electrical['connector_pinmap']=review_rel+'/connector_pinmap_P5R7.csv'
electrical['pcb_revision_relationship']=handoff['change_scope']+' Numbered net functions and GPIO assignments unchanged.'
electrical['layout_P5R7_E_J3_review']=components['layout_P5R7_E_J3_review']
for kind,v in verified.items():
    oldname,_,_=paths(kind,'P5R6');name,d,_=paths(kind)
    info=electrical['pcb_projects'].pop(oldname);info['path']=str(d.relative_to(ROOT))
    info['native_checks'].update(board=name,status='PASS',ERC=0,DRC=0,unconnected=0,parity=0,ignored_ERC_checks=[],ignored_DRC_checks=[],source_sha256=v['pcb_sha256'],report=review_rel+'/reports/'+kind+'/released/drc.json')
    electrical['pcb_projects'][name]=info
    electrical['active_schematics'][kind]=str((d/(name+'.kicad_sch')).relative_to(ROOT))
with (ROOT/'hardware/pinmap.csv').open(encoding='utf-8-sig',newline='')as h:pinmap=list(csv.DictReader(h))
for row in pinmap:row['revision']=REV
for file in [HERE/'pinmap_P5R7.csv',H/'interfaces'/('pinmap_'+REV+'.csv'),ROOT/'hardware/pinmap.csv']:
    with file.open('w',encoding='utf-8-sig',newline='')as h:
        w=csv.DictWriter(h,list(pinmap[0]));w.writeheader();w.writerows(pinmap)
for row in electrical['pinmap']:row['revision']=REV
# Refresh the active inline wiring from the already published P5R6 table,
# preserving numbered connections and external-device definitions.
with (H/'interfaces/harness_V1.2-H0.5-P5R6.csv').open(encoding='utf-8-sig',newline='')as h:
    harness_rows=list(csv.DictReader(h))
active_harness=[]
for row in harness_rows:
    row['revision']=REV
    entry=dict(row)
    for key in ['from_','to']:
        endpoint=json.loads(row[key])
        endpoint['board']=endpoint['board'].replace('MORI_motion_P5R6','MORI_motion_P5R7').replace('MORI_rear_P5R6','MORI_rear_P5R7')
        row[key]=json.dumps(endpoint,ensure_ascii=False)
        entry[key]=endpoint
    entry['length_mm']=float(row['length_mm']) if row['length_mm'] else None
    active_harness.append(entry)
with (H/'interfaces'/('harness_'+REV+'.csv')).open('w',encoding='utf-8-sig',newline='')as h:
    w=csv.DictWriter(h,list(harness_rows[0]));w.writeheader();w.writerows(harness_rows)
electrical['harness']=active_harness
electrical['versioned_pinmap']='hardware/v1_2/interfaces/pinmap_'+REV+'.csv'
electrical['versioned_harness']='hardware/v1_2/interfaces/harness_'+REV+'.csv'
atomic_json(ROOT/'contracts/components.json',components);atomic_json(ROOT/'contracts/electrical_interfaces.json',electrical)
print('Published native handoff and hardware-owned contract references; mechanics unchanged.',flush=True)
