"""Independent J10 C2 electrical trial. Never writes released PCB/contracts."""
import sys,json,shutil,hashlib,subprocess,collections
from pathlib import Path
import wx,pcbnew as k
app=wx.App(False)
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'hardware/v1_2/tools'))
from layout_P5 import xy,pt,mm,track,via,rect
from close_P5 import connected,clusters
from body_keepouts_P3R1 import rectangle
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
OLD='MORI_power_P5R7_J10_CANDIDATE'
NAME='MORI_power_J10_C2_CANDIDATE'
SD=HERE.parent/'j10_candidate'/OLD
D=HERE/NAME
PCB=D/(NAME+'.kicad_pcb')
R=HERE/'reports';R.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def pads(f):return sorted((p.GetNumber(),xy(p.GetPosition()),p.GetNetname(),xy(p.GetSize()),xy(p.GetDrillSize()))for p in f.Pads())
def load():
 b=k.LoadBoard(str(PCB));connected(b);return b
def save(b):k.SaveBoard(str(PCB),b)
def check(label):
 args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(R/(label+'_drc.json')),str(PCB)]
 c=subprocess.run(args,capture_output=True,text=True)
 j=json.loads((R/(label+'_drc.json')).read_text())
 dump(R/(label+'_command.json'),dict(argv=args,returncode=c.returncode,stdout=c.stdout,stderr=c.stderr,pcb_sha256=sha(PCB)))
 print(label,c.returncode,collections.Counter(x['type']for x in j['violations']),'opens',len(j['unconnected_items']),flush=True)
 return j
def move(b,f,point):
 old=f.GetPosition();diff=pt(*point)-old
 for z in b.Zones():
  if z.GetZoneName()in ['BODY_'+f.GetReference(),'NETBODY_'+f.GetReference(),'BODY_'+f.GetReference()+'_OPPOSITE','NETBODY_'+f.GetReference()+'_OPPOSITE']:z.Move(diff)
 f.SetPosition(pt(*point))
def init():
 assert not D.exists(),'Reviewed candidate must not be overwritten.'
 hashes={}
 for p in SD.rglob('*'):
  if not p.is_file()or p.suffix in ['.kicad_prl','.lck']or p.name.startswith('~'):continue
  hashes[str(p.relative_to(ROOT))]=sha(p)
  q=D/p.relative_to(SD).parent/p.name.replace(OLD,NAME);q.parent.mkdir(parents=True,exist_ok=True)
  data=p.read_bytes()
  if p.suffix in ['.kicad_sch','.kicad_pro']:data=data.replace(OLD.encode(),NAME.encode())
  q.write_bytes(data)
 dump(R/'input_hashes.json',hashes)
 b=load();fs={f.GetReference():f for f in b.GetFootprints()}
 changes=[]
 for ref in ['D30','F70']:
  f=fs[ref];before=pads(f);f.Flip(f.GetPosition(),k.FLIP_DIRECTION_LEFT_RIGHT)
  assert before==pads(f),'Numbered land positions changed'
  # Two-face BODY polygons are geometrically symmetric for these parts.
  # Keep both, exchange naming so suffix continues to mean opposite face.
  for z in b.Zones():
   n=z.GetZoneName()
   if n in ['BODY_'+ref,'NETBODY_'+ref]:z.SetZoneName(n+'_OPPOSITE')
   elif n in ['BODY_'+ref+'_OPPOSITE','NETBODY_'+ref+'_OPPOSITE']:z.SetZoneName(n.removesuffix('_OPPOSITE'))
  changes.append(dict(ref=ref,action='F.Cu -> B.Cu; identical numbered pad centres, dimensions and nets',pads=before))
 for ref,pos in [('R50',(39.5,23.3)),('JP70',(36.5,45.2))]:
  before=xy(fs[ref].GetPosition());move(b,fs[ref],pos)
  changes.append(dict(ref=ref,action='translation',before_mm=before,after_mm=pos))
 # Remove failed C1 copper, retaining all unaffected nets/segments and widths.
 report=json.loads((HERE.parent/'j10_candidate/reports/drc.json').read_text())
 bad={x['uuid']for v in report['violations']if v['type']=='items_not_allowed'for x in v['items']}
 full={'/BAT_ADC','/WHEEL_ADC','/H_PRE','/H6_IN','/C5_EN'}
 removed=[]
 for t in list(b.GetTracks()):
  cut=t.m_Uuid.AsString()in bad or t.GetNetname()in full
  # Old R50 BAT_MON branch needs fresh endpoint at translated land.
  if t.GetNetname()=='/BAT_MON' and not isinstance(t,k.PCB_VIA) and any(abs(q[0]-38.675)<.01 and abs(q[1]-24)<.01 for q in [xy(t.GetStart()),xy(t.GetEnd())]):cut=True
  if cut:removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
 # New B-face F70: its C5_VIN output retains the existing external via.
 for t in b.GetTracks():
  if t.GetNetname()=='/C5_VIN' and not isinstance(t,k.PCB_VIA) and xy(t.GetStart())==(30.5,39.455):t.SetLayer(k.B_Cu)
 b.GetTitleBlock().SetRevision('J10-C2 / PROTOTYPE / NOT RELEASED')
 b.GetTitleBlock().SetTitle('J10 side-entry with underside D30/F70 / mechanical acceptance pending')
 save(b)
 dump(R/'changes.json',dict(changes=changes,ripped_tracks=removed,J10_numbered_holes_unchanged=pads(fs['J10'])==pads(next(f for f in k.LoadBoard(str(SD/(OLD+'.kicad_pcb'))).GetFootprints()if f.GetReference()=='J10')),scope='Candidate only; F70 backside allocation3.09mm needs mechanical acceptance. Critical buck IC/capacitor placement preserved.'))
 check('01_placement')
if __name__=='__main__':
 if sys.argv[1]=='init':init()
 elif sys.argv[1]=='check':check(sys.argv[2])
