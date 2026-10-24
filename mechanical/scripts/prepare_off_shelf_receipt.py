"""Promote the user-approved 2026-10-13 layout parameters and source receipt.

Run once, after capture_off_shelf_baseline.py. Hardware sources stay read-only.
"""
import json, hashlib, shutil
from pathlib import Path

project = Path(__file__).resolve().parents[2]
root = project/'mechanical'
study = root/'studies/off_shelf_modules_20261013'
refs = root/'input_assets/off_shelf_M1_56'
baseline = json.loads((refs/'baseline.json').read_text())
center = json.loads((refs/'center_checks.json').read_text())
direct = json.loads((refs/'direct_checks.json').read_text())
assert center['status'] == direct['status'] == 'PASS'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
save = lambda p,d: p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
sources = root/'sources/off_shelf_20261013'
sources.mkdir(parents=True, exist_ok=True)
sample = Path('/Users/dean/Documents/MORI')
origins = {
 'ups_step':sample/'hardware/test_rig/specifications/03_Waveshare_UPS_3S/UPS_3S_official.step',
 'ups_cache':sample/'mechanical/test_rig/cad_cache/ups3s.json',
 'imu_step':sample/'hardware/test_rig/specifications/05_DFRobot_SEN0693/SEN0693_official.stp',
 'imu_cache':sample/'mechanical/test_rig/cad_cache/bmi323.json',
 'imu_socket':study/'bmi323_socket_surface.json',
 'buck_step':sample/'mechanical/test_rig/r42/sources/DC BUCK Adapter (7.2V).step',
 'buck_cache':study/'buck_family.json',
}
receipt = {}
for key,p in origins.items():
 dest=sources/p.name
 if dest.exists(): assert sha(dest)==sha(p)
 else: shutil.copy2(p,dest)
 receipt[key]={'file':str(dest.relative_to(project)), 'sha256':sha(dest)}
save(sources/'source_receipt.json', dict(date='2026-10-13', units='mm', scale_factor=1,
     files=receipt, source_match_limits={'ups':'Simplified vendor CAD; full installed cells/insulation/connectors not established',
     'imu':'Official STEP without optional unpopulated header; original socket open surface retained',
     'buck':'Selected 6V; official 7.2V family CAD. Exact selected variant population is ASSUMED'},
     physical_measurements=False))
modules = {
 'ups':dict(id='UPS_Module', label='微雪 UPS Module 3S / 原厂简化总成',
    matrix_world=[[1,0,0,0],[0,1,0,-12],[0,0,1,97.5],[0,0,0,1]],
    manufacturer='Waveshare', sku='UPS Module 3S', category='PURCHASED_REFERENCE',
    data_status='VENDOR_DOCUMENTED', omit_solid_indices=[],
    limit='原厂简化 CAD；电芯、绝缘板和接插件完整装件形状及实物修订仍待复核'),
 'imu':dict(id='IMU_BMI323', label='DFRobot SEN0693 / 无排针、保留小插座',
    matrix_world=center['selected']['imu']['matrix_world'], manufacturer='DFRobot',
    sku='SEN0693 Fermion BMI323', category='PURCHASED_REFERENCE', data_status='VENDOR_DOCUMENTED',
    omit_solid_indices=list(range(84,91)), limit='官方 CAD；未焊排针按用户配置去除。小插座为原始开放曲面，碰撞用保守框；插合待核'),
 'buck':dict(id='Head_Buck_6V', label='微雪 DC BUCK Adapter 6V / 同系列 CAD 占位',
    matrix_world=center['selected']['buck']['matrix_world'], manufacturer='Waveshare',
    sku='DC BUCK Adapter (6V)', category='PLACEHOLDER', data_status='ASSUMED',
    omit_solid_indices=[], limit='34×21.5 外形与安装孔有系列资料；7.2V CAD 不证明 6V 版元件和高度一致。保持琥珀色'),
}
q=dict(enabled=True, approved=True, revision='V1.2-M1.56',
 approval='USER_APPROVED: 采用直固方案（推荐）', approval_date='2026-10-13',
 baseline=str((refs/'baseline.json').relative_to(project)),
 baseline_sha256=sha(refs/'baseline.json'),
 construction_source='This geometry.json section only. Captured candidate meshes are independent verification references.',
 controller_pose=center['controller_pose'], controller_group_ids=center['controller_group_ids'],
 retired_ids=center['retired_reference_ids'], sources=receipt, modules=modules,
 old_mount_sites=center['obsolete_mount_sites_removed'], small_board_mounts=center['mounts'],
 deck=dict(bottom_z_mm=111., top_z_mm=115., carrier_seat_capture_z_mm=[115.,122.],
           carrier_seat_capture_radius_mm=3.4, old_top_cut_z_mm=[115.,122.],
           old_bottom_cut_z_mm=[102.,111.], pilot_fill_radius_mm=1.75,
           small_seat_start_z_mm=114.8, small_hole_start_z_mm=110.5, segments=64, saved_float32_cleanup_mm=0.00001),
 ups_mount=dict(centers_xy_mm=[r['xy_mm'] for r in direct['sites']],
    seat_z_mm=[99.1,111.2], seat_radius_mm=4.2, through_bore_z_mm=[98.9,115.2],
    through_bore_radius_mm=1.65, screw_shank_z_mm=[90.,115.01], screw_radius_mm=1.5,
    screw_head_z_mm=[115.,118.], screw_head_radius_mm=2.84, hex_socket_z_mm=[116.5,118.1],
    hex_socket_af_mm=2.5, nut_z_mm=[95.1,97.5], nut_af_mm=5.5, nut_bore_z_mm=[95.,97.6],
    segments=96, screws='4x ISO4762 M3x25', nuts='4x DIN934 M3 AF5.5 h2.4',
    thread_representation='Nominal cylinders; supplier/threads/tolerances not physically qualified'),
 service=dict(shells_removed=['Body_Front','Body_Rear'],
     UPS_independently_supported=True, screw_tool='Short 2.5mm AF L key; straight long driver is obstructed',
     remove_fasteners=['UPS_Direct_Screw_0..3','UPS_Direct_Nut_0..3'],
     extraction_direction='+Y/front, wires unplugged', flexible_harness='NOT_TESTED'),
 physical_strength='NOT_TESTED', manufacturing_release=False,
 electrical_adaptation='BLOCKED: BAT capacity, physical power-cut, 5V distribution, IMU I2C and rear DC interface remain unresolved')
save(refs/'approval.json', dict(approval=q['approval'], parameters=q,
     references=baseline['reference_files'], source_files=receipt, geometry_role='verification only'))
cfg=project/'config/geometry.json';p=json.loads(cfg.read_text())
assert p['revision']=='V1.2-M1.55' and 'off_shelf_modules' not in p
p['revision']=q['revision'];p['off_shelf_modules']=q;save(cfg,p)
ip=project/'contracts/mechanical_interfaces.json';i=json.loads(ip.read_text())
i['revision']=q['revision'];i['mechanical_revision']=q['revision'];i['current_geometry_revision']=q['revision']
i['current_authority']='config/geometry.json; off_shelf_modules overrides historical battery/power/IMU/buck allocations and carrier pose. Hardware contract remains received P5R7, awaiting electrical redesign.'
i['off_shelf_modules']=dict(revision=q['revision'],approved=True,geometry_source='config/geometry.json#/off_shelf_modules',
     controller='WeAct STM32F412 + received P5R7 carrier; central rigid placement',
     modules=modules, retired_ids=q['retired_ids'], sources=receipt,
     mount=q['ups_mount'], service=q['service'], physical_strength='NOT_TESTED',
     electrical_adaptation=q['electrical_adaptation'], manufacturing_release=False)
i['verification_note']='M1.56 mechanical adoption only. P5R7 electrical sources unchanged. Old battery/power/IMU and two-buck geometry are construction history, not the current installed route.'
save(ip,i)
print('RECEIPT_PREPARED',q['revision'],len(receipt))
