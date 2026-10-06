"""Match P4 PH land annuli to source rules and synchronize CAD fields."""
import pcbnew as k
import json,csv,sys
from helpers_P4 import paths
from functional_schematic import sexpr,encode,q
from body_keepouts_P3R1 import create
from pathlib import Path
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));mapping={}
lib=d/'footprints/MORI_Custom.pretty';lib.mkdir(exist_ok=True)
for f in b.GetFootprints():
 if 'JST_PH_' not in str(f.GetFPID().GetLibItemName()):continue
 fn=str(f.GetFPID().GetLibItemName()).split('__P4')[0]+'__P4_PH_ANNULUS'
 for pad in f.Pads():pad.SetSize(k.VECTOR2I(k.FromMM(1.35),k.FromMM(1.35)))
 f.SetField('Datasheet','');f.SetFPID(k.LIB_ID('MORI_Custom',fn));mapping[f.GetReference()]='MORI_Custom:'+fn
 # Footprints contain row pin centers, not body centers. Through-hole
 # plated annulus now >= 0.25 mm with standard 0.75 mm drill.
 k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib),f)
 if kind=='power' and f.GetReference()=='J15':f.Move(k.VECTOR2I(k.FromMM(3),k.FromMM(-1)))
 if kind=='power' and f.GetReference()=='J10':f.Move(k.VECTOR2I(k.FromMM(2.5),0))
def update(n):
 if not isinstance(n,list):return
 props={json.loads(x[1]):x for x in n if isinstance(x,list) and x and x[0]=='property'}
 if 'Reference' in props and 'Footprint' in props:
  ref=json.loads(props['Reference'][2])
  if ref in mapping:props['Footprint'][2]=q(mapping[ref])
 for x in n:update(x)
for file in [d/(name+'.kicad_sch'),d/'MORI.kicad_sym']:
 n=sexpr(file.read_text());update(n);file.write_text(encode(n)+'\n')
data=json.loads((d/'connectivity.json').read_text())
for c in data['components']:
 if c['ref'] in mapping:c['footprint']=mapping[c['ref']]
(d/'connectivity.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
rows=list(csv.DictReader((d/'assembly_bom.csv').open()))
for row in rows:
 if row['ref'] in mapping:row['footprint']=mapping[row['ref']]
with (d/'assembly_bom.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
create(b);k.SaveBoard(str(p),b)
print(name,'PH annulus, metadata, and connector spacing updated')
