"""TDK-specific provisional paste rule and unambiguous sensor-axis markings."""
from review_P5R4 import *
e=Edit('imu');f=e.f['U1']
f.SetLocalSolderPasteMargin(0)
f.SetLocalSolderPasteMarginRatio(-.05)
f.SetLibDescription(f.GetLibDescription()+' P5R4: U1 only, KiCad -5 percent per-edge ratio gives 90 percent linear paste dimensions; provisional 100 um stencil per AN-000393 v2.4 pp7-8. Copper and mask unchanged. Assembly supplier confirmation required.')
k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(e.d/'footprints/MORI_Custom.pretty'),f)
def line(a,b):
 s=k.PCB_SHAPE(e.b);s.SetShape(k.S_SEGMENT);s.SetStart(pt(*a));s.SetEnd(pt(*b));s.SetLayer(k.F_SilkS);s.SetWidth(mm(.15));e.b.Add(s)
def label(s,p):
 t=k.PCB_TEXT(e.b);t.SetText(s);t.SetPosition(pt(*p));t.SetLayer(k.F_SilkS);t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.15));e.b.Add(t)
line((1.3,8.6),(3.1,8.6));line((3.1,8.6),(2.7,8.3));line((3.1,8.6),(2.7,8.9))
line((1.3,8.6),(1.3,7.1));line((1.3,7.1),(1,7.5));line((1.3,7.1),(1.6,7.5))
label('X',(3.8,8.6));label('Y',(2.2,7.2));label('+Z',(2.2,9.65))
e.check('imu_paste_axes_02')
for p in f.Pads():
 m=p.GetSolderPasteMargin(k.F_Paste)
 print(p.GetNumber(),'copper',xy(p.GetSize()),'effective_paste',(k.ToMM(p.GetSize().x+2*m.x),k.ToMM(p.GetSize().y+2*m.y)))
