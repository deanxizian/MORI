# -*- coding: utf-8 -*-
from pathlib import Path
import json
IMU_DIR=Path(__file__).resolve().parent
__file__=str(IMU_DIR/'check_static.py')
exec(compile(Path(__file__).read_text().split('specs=[')[0],__file__,'exec'),globals())
out={'source_blend_sha256':source_hash,'ports':{},'bounds':{}}
for n in ['motion_J4','imu_J1']:
    d=port_pins[n];out['ports'][n]=dict(axis=d['axis'].tolist(),pins={k:v.tolist() for k,v in d['pins'].items()})
for n in ['Load_Frame','Body_Upper','Body_Lower','Rear_Interface_PCB','Battery_Tray','Battery','IMU','Power_Module']:
    if n in obstacles:out['bounds'][n]=[obstacles[n].lo.tolist(),obstacles[n].hi.tolist()]
(IMU_DIR/'imu_endpoints.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
