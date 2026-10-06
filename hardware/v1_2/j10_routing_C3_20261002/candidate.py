"""C3 routing-only continuation of the immutable J10 C2/A3 placement study.

Run with KiCad 10's bundled Python. No released files are written.
"""
import sys, json, shutil, hashlib, subprocess, collections, math
from pathlib import Path
import wx, pcbnew as k
app = wx.App(False)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'hardware/v1_2/tools'))
from layout_P5 import xy, pt, mm, F, B, track, via, rect
from close_P5 import connected, clusters
from geometry_guard_P5 import Guard, obstacles
from plane_finish_P5 import simple
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
OLD = 'MORI_power_J10_C2_CANDIDATE'
NAME = 'MORI_power_J10_C3_CANDIDATE'
SD = ROOT/'hardware/v1_2/prearrival_20261002/j10_refinement_C2'/OLD
D = HERE/NAME
PCB = D/(NAME+'.kicad_pcb')
R = HERE/'reports'
R.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,j): p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def load():
    b=k.LoadBoard(str(PCB)); connected(b); return b
def save(b): k.SaveBoard(str(PCB),b)
def check(label):
    args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations','-o',str(R/(label+'_drc.json')),str(PCB)]
    c=subprocess.run(args,capture_output=True,text=True)
    dump(R/(label+'_command.json'),dict(argv=args,returncode=c.returncode,stdout=c.stdout,stderr=c.stderr,pcb_sha256=sha(PCB)))
    j=json.loads((R/(label+'_drc.json')).read_text())
    print(label,c.returncode,collections.Counter(x['type']for x in j['violations']),'opens',len(j['unconnected_items']),flush=True)
    return j
def init():
    assert not D.exists(), 'Do not overwrite a candidate.'
    inputs={}
    for p in SD.rglob('*'):
        if not p.is_file() or p.suffix in ['.kicad_prl','.lck'] or p.name.startswith('~'): continue
        inputs[str(p.relative_to(ROOT))]=sha(p)
        q=D/p.relative_to(SD).parent/p.name.replace(OLD,NAME);q.parent.mkdir(parents=True,exist_ok=True)
        data=p.read_bytes()
        if p.suffix in ['.kicad_sch','.kicad_pro']:data=data.replace(OLD.encode(),NAME.encode())
        q.write_bytes(data)
    dump(R/'input_hashes.json',inputs)
    b=load()
    b.GetTitleBlock().SetRevision('J10-C3 / PROTOTYPE / NOT RELEASED')
    b.GetTitleBlock().SetTitle('J10 side-entry: routed candidate; mechanical/physical qualification pending')
    save(b)
def snapshot(label):
    b=load(); out={'sha256':sha(PCB),'footprints':{},'tracks':[],'areas':[]}
    for f in b.GetFootprints():
        out['footprints'][f.GetReference()]={'xy':xy(f.GetPosition()),'layer':b.GetLayerName(f.GetLayer()),'rotation':f.GetOrientationDegrees(),'body':rect(f),'pads':[{'number':p.GetNumber(),'xy':xy(p.GetPosition()),'size':xy(p.GetSize()),'rotation':p.GetOrientationDegrees(),'shape':int(p.GetShape()),'drill':xy(p.GetDrillSize()),'net':p.GetNetname(),'layers':[b.GetLayerName(l)for l in [F,B]if p.IsOnLayer(l)]}for p in f.Pads()]}
    for t in b.GetTracks():
        out['tracks'].append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':k.ToMM(t.GetWidth(F))if isinstance(t,k.PCB_VIA)else k.ToMM(t.GetWidth()),'via':isinstance(t,k.PCB_VIA)})
    for z in b.Zones():
        if not z.GetIsRuleArea(): continue
        ol=z.Outline()
        out['areas'].append({'name':z.GetZoneName(),'layers':[b.GetLayerName(l)for l in [F,B]if z.IsOnLayer(l)],'polys':[[xy(ol.COutline(i).CPoint(n))for n in range(ol.COutline(i).PointCount())]for i in range(ol.OutlineCount())]})
    dump(R/(label+'_geometry.json'),out)
    print('snapshot',label,flush=True)
if __name__=='__main__':
    if sys.argv[1]=='init':init()
    elif sys.argv[1]=='check':check(sys.argv[2])
    elif sys.argv[1]=='snapshot':snapshot(sys.argv[2])
