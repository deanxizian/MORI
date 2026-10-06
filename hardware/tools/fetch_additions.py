from fetch_sources import fetch,ROOT
from concurrent.futures import ThreadPoolExecutor
import json
u={
'motor25':'https://www.pololu.com/product/4863',
'motor25_specs':'https://www.pololu.com/product/4863/specs',
'motor25_drawing':'https://www.pololu.com/file/0J1634/25d-metal-gearmotor-dimension-diagram.pdf',
'motor25_datasheet':'https://www.pololu.com/file/0J1829/pololu-25d-metal-gearmotors.pdf',
'servo270':'https://www.dfrobot.com/product-1106.html',
'encoder_level':'https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf',
'watchdog':'https://www.ti.com/lit/ds/symlink/cd74hc123.pdf',
'ansmann_candidate':'https://batterie-boutique.fr/media/d3/cd/ed/1762344143/2447-0105_Lithium-Ionen-Akkupack.pdf?ts=1762344143',
'large_display':'https://www.displaymodule.com/products/2-4-inch-round-ips-high-brightness-display-480x480-octagon-with-mipi',
'imu_datasheet':'https://www.st.com.cn/resource/en/datasheet/lsm6dsox.pdf',
'regulator_logic':'https://www.pololu.com/product/2831',
'estop':'https://www.se.com/us/en/product/XB5AS8444/',
}
old={v['id']:v for v in json.loads((ROOT/'sources/manifest.json').read_text())}
with ThreadPoolExecutor(max_workers=6) as pool:
 for r in pool.map(fetch,u.items()):
  if r['status']=='PASS' or old.get(r['id'],{}).get('status')!='PASS':old[r['id']]=r
  print(r['id'],r['status'],flush=True)
(ROOT/'sources/manifest.json').write_text(json.dumps(list(old.values()),indent=2)+'\n')
