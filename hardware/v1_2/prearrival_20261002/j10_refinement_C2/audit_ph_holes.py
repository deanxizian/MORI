"""Read-only audit against JST's PH-specific glass-epoxy PTH FAQ."""
from candidate import *
import csv
def run():
 rows=[];hashes={}
 for kind,rev in [('motion','P5R7'),('power','P5R6'),('rear','P5R7'),('imu','P5R4')]:
  n='MORI_'+kind+'_'+rev;d=ROOT/'hardware/v1_2/kicad'/n
  for ext in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru']:hashes[str((d/(n+ext)).relative_to(ROOT))]=sha(d/(n+ext))
  b=k.LoadBoard(str(d/(n+'.kicad_pcb')))
  for f in b.GetFootprints():
   fid=str(f.GetFPID().GetLibItemName())
   if 'JST_PH_'not in fid:continue
   ps=[p for p in f.Pads()if p.GetAttribute()==k.PAD_ATTRIB_PTH];num=len(ps)
   if not num:continue
   lo,hi=(.80,.85)if num==2 else(.85,.90)
   drill=sorted({k.ToMM(p.GetDrillSize().x)for p in ps})
   rows.append(dict(board=n,ref=f.GetReference(),pins=num,footprint=fid,nominal_KiCad_hole_mm=','.join(map(str,drill)),
                    manufacturer_finished_min_mm=lo,manufacturer_finished_max_mm=hi,
                    status='FAIL'if any(v<lo or v>hi for v in drill)else'BLOCKED',
                    reason='Nominal hole outside manufacturer material/process-specific window'if any(v<lo or v>hi for v in drill)else'Nominal within window; finished tolerance not qualified'))
 with(HERE/'PH_finished_hole_audit.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 dump(HERE/'formal_source_hashes.json',hashes)
 dump(HERE/'PH_finished_hole_audit.json',dict(source='https://www.jst.com/resources/faq/',source_accessed='2026-10-02',
  source_question='What is the recommended PCB hole size for the PH through-hole headers for harder resin boards?',
  source_html_sha256=sha(HERE/'jst_faq.html'),rows=rows,formal_boards_changed=False,
  scope='Applies to specified JST B*B-PH-K-S / S*B-PH-K-S on plated glass-epoxy PCB. Not automatically a rule for other vendors or non-plated holes. Manufacturing release blocked, historical ERC/DRC not redefined as footprint qualification.'))
 print('PH',len(rows),collections.Counter(r['status']for r in rows),flush=True)
if __name__=='__main__':run()
