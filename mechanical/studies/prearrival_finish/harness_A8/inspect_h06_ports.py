"""Read native H06 body pins and the separately labelled CAM allocation."""
from pathlib import Path
SCRIPT=Path(__file__).resolve();OUT=SCRIPT.parent
helper=OUT.parent/'harness_A2/check_static.py'
__file__=str(helper)
exec(compile(helper.read_text().split('MARGIN =')[0],str(helper),'exec'),globals())
__file__=str(SCRIPT)
port=port_pins['motion_J5']
head=json.loads((OUT.parent/'head_harness/head_hardware_groups.json').read_text())
cam=next(p for p in head['ports'] if p['object']=='CAM_Mainboard' and p['reference']=='UART_4P')
assert head['source_blend_sha256']==source_hash
result=dict(source_blend_sha256=source_hash,body=dict(
    port='motion_J5',source=board_sources['motion'],axis=port['axis'].tolist(),
    exit_face_mm=port['exit_face'].tolist(),pins={k:v.tolist() for k,v in port['pins'].items()},
    mating_housing_bounds_mm=[plug['motion_J5'].lo.tolist(),plug['motion_J5'].hi.tolist()],
    datum_status='Native pad numbers and pitch; actual crimped wire exit plane remains an allocation'),
    head=dict(port='CAM J11 / UART_4P',model_allocation=cam,
              actual_mating_view='BLOCKED',wire_exit_datums_mm=None),
    nearby_parts={n:dict(group=s.group,bounds_mm=[s.lo.tolist(),s.hi.tolist()]) for n,s in ss.items()
                  if n in ['MCU_Motion','Yaw_Base','Pitch_Yoke','CAM_Mainboard','Pitch_Cradle','Power_Module','Load_Frame']},
    main_geometry_changed=False,full_harness='BLOCKED')
(OUT/'h06_ports.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print(json.dumps(result,ensure_ascii=False,indent=2))
