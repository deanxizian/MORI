"""Recheck A2 nominal terminal allocations with corrected containment."""
from pathlib import Path
import json,hashlib
STAGE=Path(__file__).resolve().parent
code=(STAGE/'check_static.py').read_text().split('specs=[')[0]
exec(compile(code,str(STAGE/'check_static.py'),'exec'),globals())
assert ECOWIRE
rows=[]
specs=[('H01',['power_J17','motion_J1'],2),('H02',['motion_J2','power_J13'],2),
    ('H03',['motion_J3','power_J14'],2),('H04',['motion_J4','imu_J1'],8),('H05',['motion_J7','power_J10'],8)]
for hid,ports,count in specs:
    od=float(wire_rows[hid]['绝缘外径最大mm'])
    for port in ports:
        for pin in range(1,count+1):
            rows.append(dict(harness=hid,port=port,pin=pin,**straight_check(port,pin,od)))
out=dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    source_blend_sha256=source_hash,rows=rows,
    check_static_script_sha256=hashlib.sha256((STAGE/'check_static.py').read_bytes()).hexdigest(),
    scope='Only nominal5mm straight exit allocation with unselected Alpha wireOD; pin numbering/pitch unchanged',
    method='Near-surface clearance plus closed-solid containment, no nearest-face-normal sign',
    main_geometry_changed=False,
    limits=['Terminal exit plane and5mm straight length are assumptions, not confirmed supplier dimensions.',
        'Passing a straight does not qualify its subsequent bend, full routing, crimp or assembly.'])
(STAGE/'terminal_straights_corrected.json').write_text(json.dumps(out,indent=2)+'\n')
print('TERMINAL_STRAIGHTS_CORRECTED',out['status'],len(rows),[r for r in rows if r['status']!='PASS'],flush=True)
