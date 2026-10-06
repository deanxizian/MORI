"""P4 procurement evidence; catalog presence is not a checkout quote."""
from pathlib import Path
import csv,json,hashlib
H=Path(__file__).resolve().parents[1];O=H/'layout_P4'
rows=[]
for n,code,item in [(2,'C131337','142630'),(3,'C131339','142632'),(4,'C131334','142627'),(8,'C157974','169322')]:
 rows.append(dict(manufacturer='JST',mpn=f'B{n}B-PH-K-S(LF)(SN)',lcsc_code=code,domestic_url=f'https://item.szlcsc.com/{item}.html',pitch_mm=2,pins=n,mating=f'PHR-{n}',crimp='SPH-002T-P0.5S',wire='AWG24 for 2A rating; smaller signal wire requires qualified crimp',current_A=2,bare_xyz_mm=[2*(n-1)+3.9,4.5,6],mated_height_mm=8,source='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'))
rows += [dict(manufacturer='JST',mpn='S5B-PH-K-S(LF)(SN)',lcsc_code='C157923',domestic_url='https://item.szlcsc.com/169271.html',pitch_mm=2,pins=5,mating='PHR-5',crimp='SPH-002T-P0.5S',wire='AWG24 power; AWG26-28 CC/sense subject crimp qualification',current_A=2,bare_xyz_mm=[11.9,7.6,4.8],mated_depth_mm=9.6,source='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'),
 dict(manufacturer='HRO',mpn='TYPE-C-31-M-12',lcsc_code='C165948',domestic_url='https://item.szlcsc.com/184090.html',pitch_mm=None,pins=16,mating='USB-C plug',crimp=None,wire='USB-C cable; PD rating must match external charger',current_A=None,bare_xyz_mm=[8.94,7.35,3.16],source='https://www.krhro.com/Product-Details/726.html'),
 dict(manufacturer='SOFNG',mpn='MS-202V-G3',lcsc_code='C42378287',domestic_url='https://item.szlcsc.com/44278924.html',pitch_mm=2.5,pins=6,mating=None,crimp=None,wire='signal-only; PCB load switch carries battery current',current_A=.5,bare_xyz_mm=[9.1,3.5,3.5],source='sources/connectors_P4/SOFNG_MS202V.pdf')]
# HRO domestic URL is not inferred from an LCSC C-code; only verified LCSC SKU is retained.
rows[-2]['domestic_url']=None
for row in rows:row.update(access_date='2026-09-23',unit_price_cny=None,quote_date=None,stock_status='NOT_LIVE_CONFIRMED',shipping='未核；不能默认包邮',confirmation='VENDOR_DOCUMENTED dimensions + catalog SKU; physical fit NOT_TESTED',mass_g=None,substitution='不同品牌兼容件需重核针脚、孔位、锁扣、额定和插头；不是免验证代换')
(O/'connector_catalog.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
keys=list(dict.fromkeys(k for r in rows for k in r))
with (O/'connector_catalog.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in r.items()} for r in rows)
ss=H/'sources/connectors_P4'
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ss.glob('*.pdf'))}
(O/'connector_sources.json').write_text(json.dumps(dict(access_date='2026-09-23',files_sha256=manifest,source_status='Vendor drawings, not measurements. No CNY checkout quote or stock claim.'),ensure_ascii=False,indent=2)+'\n')
