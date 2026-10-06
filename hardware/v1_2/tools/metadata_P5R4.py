"""Synchronize candidate metadata with actual KiCad poses; no circuit changes."""
from review_P5R4 import *
from functional_schematic import sexpr,encode,q
import csv
REV='V1.2-H0.5-P5R4'
for kind in KINDS:
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
 cp=d/'connectivity.json';data=json.loads(cp.read_text())
 data.update(revision=REV,layout_revision='P5R4',circuit_revision='V1.2-H0.5-P5')
 for c in data['components']:
  if c['ref']not in fps:continue
  f=fps[c['ref']];c['placed_at']=[*xy(f.GetPosition()),f.GetOrientationDegrees()];c['footprint']=f.GetFPIDAsString()
 dump(cp,data)
 with(d/'assembly_bom.csv').open()as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
 for row in rows:
  if row['ref']in fps:row['footprint']=fps[row['ref']].GetFPIDAsString()
 with(d/'assembly_bom.csv').open('w',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 s=d/(n+'.kicad_sch');node=sexpr(s.read_text())
 for entry in node:
  if not isinstance(entry,list)or entry[0]!='title_block':continue
  for x in entry[1:]:
   if isinstance(x,list)and x[0]=='rev':x[1]=q(REV)
   if isinstance(x,list)and x[0]=='comment'and x[1]=='1':x[2]=q('P5R4 layout/assembly review; circuit P5; PROTOTYPE / NOT_TESTED')
 s.write_text('('+node[0]+'\n'+'\n'.join(encode(v)if isinstance(v,list)else v for v in node[1:])+'\n)\n')
 (d/'README.md').write_text(f'# {n}\n\n{REV} / PROTOTYPE / 实物 NOT_TESTED。\n\n本版保留 P5 电路、元件和针号；修改摆位、局部布线、IMU 专用 Paste 与轴向丝印。详见 [审查处理记录](../../layout_P5R4/README.md)。\n\n外形与安装接口不变。PCB 不是制造释放文件；没有台架、ESD、温升或整机装配合格声明。\n')
print('Candidate metadata synchronized; native checks must follow.')
