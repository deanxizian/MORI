"""Deliberately failing coupon verifies selected source rules actually execute.

This coupon is never a product board or manufacturing output.
"""
from pathlib import Path
import pcbnew as k
import subprocess,json,shutil
from detail_P2 import track
from layout_P2 import pt,mm
R=Path(__file__).resolve().parents[1];CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
out=R/'layout_P2/reports/rule_probe';out.mkdir(exist_ok=True);name='rule_probe';p=out/(name+'.kicad_pcb')
src=R/'kicad/MORI_power_P2'
for ext in ['.kicad_pro','.kicad_dru']:shutil.copyfile(src/('MORI_power_P2'+ext),out/(name+ext))
b=k.BOARD();nets={}
for n in ['/GND','/+3V3','/SIG_A','/SIG_B','/KELVIN_P','/KELVIN_N']:
    nobj=k.NETINFO_ITEM(b,n);b.Add(nobj);nets[n]=nobj
for a,c in [((0,0),(90,0)),((90,0),(90,80)),((90,80),(0,80)),((0,80),(0,0))]:
    x=k.PCB_SHAPE(b);x.SetShape(k.S_SEGMENT);x.SetLayer(k.Edge_Cuts);x.SetStart(pt(*a));x.SetEnd(pt(*c));x.SetWidth(mm(.05));b.Add(x)
for y,n in [(20,'/SIG_A'),(25,'/+3V3'),(30,'/GND')]:
    track(b,nets[n],(20,y),(25,y),.2,k.F_Cu);track(b,nets['/SIG_B'],(20,y+.35),(25,y+.35),.2,k.F_Cu)
for x,n in [(35,'/SIG_A'),(40,'/+3V3')]:track(b,nets[n],(x,20),(x,25),.15,k.F_Cu)
f=k.FOOTPRINT(b);f.SetReference('RULE_PAD');b.Add(f);p0=k.PAD(f);p0.SetNumber('1');p0.SetAttribute(k.PAD_ATTRIB_SMD);p0.SetShape(k.PAD_SHAPE_RECT);p0.SetSize(pt(.8,.8));p0.SetPosition(pt(20,40));p0.SetLayerSet(k.LSET.AllCuMask());p0.SetNet(nets['/GND']);f.Add(p0)
for x,y,vd,dr in [(20.6,40,.8,.3),(30,40,1.2,.6),(40,40,1,.45),(40.55,40,1,.45)]:
    v=k.PCB_VIA(b);v.SetPosition(pt(x,y));v.SetWidth(mm(vd));v.SetDrill(mm(dr));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(nets['/GND']);b.Add(v)
track(b,nets['/SIG_A'],(20,50),(25,50),.2,k.F_Cu);track(b,nets['/SIG_A'],(20,50),(25,55),.2,k.F_Cu)
track(b,nets['/KELVIN_P'],(40,50),(48,50),.2,k.F_Cu);track(b,nets['/KELVIN_N'],(40,50.6),(48,50.6),.2,k.F_Cu)
k.SaveBoard(str(p),b)
cmd=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--exit-code-violations','-o',str(out/'drc.json'),str(p)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=120);(out/'command.log').write_text(r.stdout+r.stderr)
drc=json.loads((out/'drc.json').read_text());descriptions='\n'.join(x['description'] for x in drc['violations'])
checks={rid:rid in descriptions for rid in ['R01','R05','R06','R07','R08','R09','R15-R16','R27','R39','R40']}
result=dict(status='PASS' if all(checks.values()) and r.returncode==5 else 'FAIL',meaning='PASS means deliberate violations were detected; this is NOT a compliant product PCB',checks=checks,argv=cmd,returncode=r.returncode)
(out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
