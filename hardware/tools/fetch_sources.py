#!/usr/bin/env python3
"""Cache manufacturer references, with immutable hashes and explicit failures."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
import hashlib,json,datetime
ROOT=Path(__file__).resolve().parents[1]
URLS={
'motor':'https://www.pololu.com/product/5216',
'motor_specs':'https://www.pololu.com/product/5216/specs',
'motor_alternative':'https://www.pololu.com/product/5214/specs',
'motor_drawing':'https://www.pololu.com/file/0J1487/pololu-micro-metal-gearmotors-rev-6-1.pdf',
'driver_module':'https://www.pololu.com/product/2130',
'driver_datasheet':'https://www.ti.com/lit/ds/symlink/drv8833.pdf',
'imu':'https://www.adafruit.com/product/4438',
'imu_pinouts':'https://learn.adafruit.com/lsm6dsox-and-ism330dhc-6-dof-imu/pinouts',
'imu_datasheet':'https://www.st.com/resource/en/datasheet/lsm6dsox.pdf',
'imu_application':'https://www.st.com/resource/en/application_note/an5272-lsm6dsox-alwayson-3d-accelerometer-and-3d-gyroscope-stmicroelectronics.pdf',
'esp_board':'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html',
'esp_schematic':'https://dl.espressif.com/dl/schematics/SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf',
'display':'https://www.waveshare.com/1.28inch-lcd-module.htm',
'display_docs':'https://docs.waveshare.net/1.28inch_LCD_Module/',
'display_alternative':'https://docs.waveshare.com/1.46inch_Touch_LCD_Module',
'servo':'https://www.pololu.com/product/2818',
'servo_datasheet':'https://www.pololu.com/file/0J1435/FS90-specs.pdf',
'regulator':'https://www.pololu.com/product/2858',
'current':'https://www.adafruit.com/product/904',
'current_datasheet':'https://www.ti.com/lit/ds/symlink/ina219.pdf',
'battery':'https://www.batteryspace.com/polymer-li-ion-battery-7.4v-2000-mah-14.8wh-4.2a-rate-with-pcb.aspx',
'charger':'https://www.batteryspace.com/Smart-Charger-1.2A-for-7.4V-Li-ion/Polymer-Rechargeable-Battery-Pack.aspx',
'watchdog':'https://www.ti.com/lit/ds/symlink/sn74hc123.pdf',
'gate':'https://www.ti.com/lit/ds/symlink/sn74hc08.pdf',
'clamp_comparator':'https://www.ti.com/lit/ds/symlink/lm393.pdf',
'clamp_reference':'https://www.ti.com/lit/ds/symlink/tl431.pdf',
}
def fetch(pair):
 key,url=pair
 r={'id':key,'url':url,'accessed':'2026-09-21'}
 try:
  with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 MORI-reference-audit'}),timeout=40) as f: data=f.read();ctype=f.headers.get('Content-Type','')
  suffix='.pdf' if data.startswith(b'%PDF') else '.html'
  out=ROOT/'sources'/f'{key}{suffix}';out.write_bytes(data)
  r.update(status='PASS',file=str(out.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
  if suffix=='.pdf':
   import fitz
   d=fitz.open(out); (out.with_suffix('.txt')).write_text('\n'.join(p.get_text() for p in d))
 except Exception as e:r.update(status='FAIL',error=str(e))
 return r
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(fetch,URLS.items()))
 (ROOT/'sources/manifest.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
 for r in rows:print(r['id'],r['status'],r.get('bytes',r.get('error')))
