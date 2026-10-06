from analyze import *
import sys, math, json, collections
sys.path.append('/mnt/data/latest_review_work/legacy')
from geometry import objects
from shapely.geometry import Polygon
OUT=Path('/mnt/data/latest_review_work/evidence')
boards={}; out={}
for n,r in [('power','P5R5'),('motion','P5R5'),('imu','P5R4'),('rear','P5R4')]:
 b,d=get_board(n,r); boards[n]=(b,d); ob=objects(d); kerrs=[]
 for z in sub(b,'zone'):
  ko=one(z,'keepout')
  if not ko:continue
  rings=[[p[1:3]for p in one(q,'pts')[1:]]for q in sub(z,'polygon')]
  if not rings or len(rings[0])<3:continue
  poly=Polygon(rings[0], holes=rings[1:]).buffer(0)
  layers=one(z,'layers')[1:] if one(z,'layers') else [val(z,'layer')]
  forbids={x[0]:x[1]for x in ko[1:]}
  for o in ob:
   if o['layer'] not in layers:continue
   kk={'segment':'tracks','via':'vias','pad':'pads','zone':'copperpour'}.get(o['kind'])
   if kk is None or forbids.get(kk)!='not_allowed':continue
   a=poly.intersection(o['geom']).area
   if a>1e-6:kerrs.append({'keepout':val(z,'name'),'layer':o['layer'],'object':o['label'],'area_mm2':a,'lines':[z.line,o['line']]})
 out[n]={'sha256':d['sha256'],'file':d['path'],'keepout_intersections':kerrs,'all_paste_settings':[(i+1,l.strip())for i,l in enumerate(Path(d['path']).read_text().splitlines())if any(k in l for k in ['solder_paste_margin','pad_to_paste_clearance'])]}
 print(n,'keepout overlaps',len(kerrs),kerrs[:5])
# Pin map table: electrical endpoint assignments; harness orientation is not established by these files.
def pins(n,ref):return {p['num']:p['net'].lstrip('/') for p in boards[n][1]['footprints'][ref]['pads'] if p['num']}
interfaces=[]
for a,ar,bb,br in [('power','J17','motion','J1'),('power','J10','motion','J7'),('power','J13','motion','J2'),('power','J14','motion','J3'),('motion','J4','imu','J1')]:
 pa,pb=pins(a,ar),pins(bb,br); interfaces.append({'a':a+'.'+ar,'b':bb+'.'+br,'pins':[{'pin':k,'a_net':pa[k],'b_net':pb.get(k)}for k in pa]})
interfaces.extend([{'a':'rear.J3.1/2','a_pins':pins('rear','J3'),'b':'power.J19.1/2','b_pins':pins('power','J19')},{'a':'rear.J3.3/4','b':'motion.J8.1/2','b_pins':pins('motion','J8')},{'connector':'rear.J2','pins':pins('rear','J2'),'note':'external PD/charger and harness not supplied; pin5 is unfused raw VBUS'}])
out['interfaces']=interfaces
out['imu_paste']={'margin_absolute':0,'margin_ratio':-.05,'interpretation':'per-edge ratio','copper_pad_mm':[.475,.25],'predicted_paste_mm':[.475*.9,.25*.9],'paste_area_vs_copper':.81,'assumed_stencil_mm':.1,'rectangular_area_ratio':(.475*.9*.25*.9)/(2*.1*(.475*.9+.25*.9)),'note':'Calculated from uploaded settings; not actual Gerber/stencil inspection. Footprint describes provisional100um. Supplier must confirm.'}
# Earlier main power arrays have not reverted to one-via cuts.
j=json.loads((OUT/'power_P5R5_geometry.json').read_text())
locations=[(35.7632,14.6304),(30.6324,6.5024),(32.004,20.7264),(58.3184,10.6172),(61.2648,22.86)]
out['prior_power_via_checks']=[]
for pos in locations:
 close=[v for v in boards['power'][1]['vias'] if math.dist(v['xy'],pos)<.002]
 cuts=[v for v in j['single_via_cuts'] if math.dist(v['xy'],pos)<.002]
 out['prior_power_via_checks'].append({'original_coordinate':pos,'still_present':bool(close),'still_single_via_cut':bool(cuts)})
# Circuit source consistency check between version names, no claim about manufacturer validity.
for n,new,old in [('power','P5R5','P5R3'),('motion','P5R5','P5R3'),('imu','P5R4','P5R2'),('rear','P5R4','P5R2')]:
 path=Path(f'/mnt/data/MORI_{n}_{new}.kicad_sch');out[n]['schematic_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
(OUT/'final_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('interfaces',json.dumps(interfaces,ensure_ascii=False,indent=2))
print('paste',out['imu_paste'])
