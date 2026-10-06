"""P4 exact PH connector replacement; preserves P3R1 and electrical pin numbers.

Run with KiCad bundled Python. Placement is a trial until native checks/routing.
"""
from pathlib import Path
import pcbnew as k
import json,csv,shutil,sys
from functional_schematic import sexpr,encode,q
from body_keepouts_P3R1 import create
H=Path(__file__).resolve().parents[1]
FP=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
pt=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
xy=lambda p:[k.ToMM(p.x),k.ToMM(p.y)]
# Center of the electrical pad row, orientation, component side. Connector
# pin order is retained; PH is not a footprint-compatible drop-in for GH/SH.
PLACEMENTS={
 'motion':{'J1':(52,4,0,'F'),'J2':(61,4,0,'F'),'J3':(60,21.5,180,'F'),
           'J4':(52,16.5,90,'F'),'J5':(65,13,90,'F'),'J6':(60,26,0,'B'),
           'J7':(56,29.5,180,'F'),'J8':(46,25.5,0,'B')},
 'imu':{'J1':(10,3.5,0,'F')},
 'power':{'J10':(56,38.4,270,'F'),'J13':(76,18,90,'F'),
          'J14':(76,31,90,'F'),'J15':(56,26.5,180,'F'),
          'J16':(74,39,90,'F'),'J17':(4.5,20,90,'F')}}

def replace(kind):
 name='MORI_'+kind+'_P4';d=H/'kicad'/name;p=d/(name+'.kicad_pcb')
 b=k.LoadBoard(str(p));data=json.loads((d/'connectivity.json').read_text())
 parts={c['ref']:c for c in data['components']};changes={};out=[]
 for ref,(cx,cy,angle,side) in PLACEMENTS[kind].items():
  old=next(f for f in b.GetFootprints() if f.GetReference()==ref);c=parts[ref];n=len(c['pins'])
  fn=f'JST_PH_B{n}B-PH-K_1x{n:02d}_P2.00mm_Vertical';lib='Connector_JST'
  dest=d/'footprints'/(lib+'.pretty');dest.mkdir(exist_ok=True)
  shutil.copy2(FP/(lib+'.pretty')/(fn+'.kicad_mod'),dest/(fn+'.kicad_mod'))
  new=k.FootprintLoad(str(dest),fn);new.SetReference(ref);new.SetValue(old.GetValue());new.SetPath(old.GetPath());new.SetFPID(k.LIB_ID(lib,fn))
  new.SetField('Datasheet','https://www.jst-mfg.com/product/pdf/eng/ePH.pdf')
  nets={pad.GetNumber():pad.GetNet() for pad in old.Pads() if pad.GetNumber() not in ['','MP']}
  for pad in new.Pads():pad.SetNet(nets[pad.GetNumber()])
  b.Add(new);new.SetOrientationDegrees(angle)
  if side=='B':new.Flip(pt(0,0),False)
  coords=[xy(pad.GetPosition()) for pad in new.Pads()]
  new.SetPosition(pt(cx-sum(v[0] for v in coords)/n,cy-sum(v[1] for v in coords)/n))
  new.Reference().SetVisible(False);new.Value().SetVisible(False)
  out.append(dict(ref=ref,old_footprint=str(old.GetFPID().GetLibItemName()),new_footprint=lib+':'+fn,
                  mpn=f'B{n}B-PH-K-S(LF)(SN)',mating=f'PHR-{n}',contact='SPH-002T-P0.5S',
                  rated_A=2,rating_wire='AWG24',bare_height_mm=6,mated_height_mm=8,
                  installed_height_status='VENDOR_DOCUMENTED connector only; wire bends not included',
                  old_pins=[dict(pin=pad.GetNumber(),xy=xy(pad.GetPosition()),net=pad.GetNetname()) for pad in old.Pads()],
                  new_pins=[dict(pin=pad.GetNumber(),xy=xy(pad.GetPosition()),net=pad.GetNetname()) for pad in new.Pads()]))
  b.Delete(old);changes[ref]=lib+':'+fn;c['footprint']=changes[ref];c['placed_at']=xy(new.GetPosition())+[new.GetOrientationDegrees()];c['side']=side
  c['selected_mpn']=f'JST B{n}B-PH-K-S(LF)(SN)';c['source']='https://www.jst-mfg.com/product/pdf/eng/ePH.pdf'
  c['note']='P4 PH 2.0 mm. PHR-'+str(n)+' / SPH-002T-P0.5S. Signal pin numbering unchanged. Check both mating views; never wire by color alone.'
 def update(node):
  if not isinstance(node,list):return
  props={json.loads(x[1]):x for x in node if isinstance(x,list) and x and x[0]=='property'}
  if 'Reference' in props and 'Footprint' in props:
   ref=json.loads(props['Reference'][2])
   if ref in changes:props['Footprint'][2]=q(changes[ref])
  for x in node:update(x)
 for p2 in [d/(name+'.kicad_sch'),d/'MORI.kicad_sym']:
  node=sexpr(p2.read_text());update(node);p2.write_text(encode(node)+'\n')
 for t in b.GetDrawings():
  if isinstance(t,k.PCB_TEXT):t.SetText(t.GetText().replace('P3R1','P4'))
 tb=b.GetTitleBlock();tb.SetRevision('V1.2-H0.4-P4 PROTOTYPE');b.SetTitleBlock(tb)
 create(b);k.SaveBoard(str(p),b)
 (d/'connectivity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 rows=list(csv.DictReader((d/'assembly_bom.csv').open()))
 for row in rows:
  if row['ref'] in changes:row['footprint']=changes[row['ref']];row['note']=parts[row['ref']]['note'];row['source']=parts[row['ref']]['source']
 with (d/'assembly_bom.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (H/'layout_P4/reports'/name/'connector_changes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(name,len(out),'PH replacements; routing NOT YET checked')
if __name__=='__main__':replace(sys.argv[1])
