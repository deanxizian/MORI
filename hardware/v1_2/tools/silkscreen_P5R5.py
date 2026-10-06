"""Add native printed interface labels. Never changes copper or pad geometry."""
from review_P5R5 import *
from layout_P5 import rect
from functional_schematic import sexpr,encode,q

def bb(item):
 b=item.GetBoundingBox();return tuple(k.ToMM(v)for v in[b.GetX(),b.GetY(),b.GetRight(),b.GetBottom()])
def intersects(a,b,g=.10):return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g

def run(kind):
 e=Edit(kind);b=e.b;size=(70,35)if kind=='motion'else(80,55);record=[];blocked=[]
 # Every generated label is in a tagged group, so reruns remove only our text.
 for group in list(b.Groups()):
  if group.GetName()=='P5R5_PRINTED_INTERFACE_LABELS':
   ids={t.m_Uuid.AsString()for t in group.GetItems()}
   for t in list(b.GetDrawings()):
    if t.m_Uuid.AsString()in ids:group.RemoveItem(t);b.Delete(t)
   b.Delete(group)
 group=k.PCB_GROUP(b);group.SetName('P5R5_PRINTED_INTERFACE_LABELS');b.Add(group)
 if kind=='power':
  mapping={}
  for ref in ['J11','J12']:
   f=e.f[ref]
   for t in f.GraphicalItems():
    if hasattr(t,'GetText')and t.GetLayer()==k.F_SilkS:
     if t.GetText()=='-':t.SetText('D');t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.12))
     if t.GetText()=='+':t.SetText('VM');t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.12))
     if ref=='J12' and t.GetText()in['D','VM']:t.SetPosition(pt(65 if t.GetText()=='D'else 70,53.6))
   new=str(f.GetFPID().GetLibItemName()).split('__P5R5')[0]+'__P5R5_DUMP';f.SetFPID(k.LIB_ID('MORI_Custom',new));mapping[ref]='MORI_Custom:'+new
   k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(e.d/'footprints/MORI_Custom.pretty'),f)
  def update(node):
   if not isinstance(node,list):return
   props={json.loads(x[1]):x for x in node if isinstance(x,list)and x and x[0]=='property'}
   if 'Reference'in props and 'Footprint'in props:
    ref=json.loads(props['Reference'][2])
    if ref in mapping:props['Footprint'][2]=q(mapping[ref])
   for x in node:update(x)
  for path in[e.d/(e.name+'.kicad_sch'),e.d/'MORI.kicad_sym']:
   root=sexpr(path.read_text());update(root);path.write_text('('+root[0]+'\n'+'\n'.join(encode(x)if isinstance(x,list)else x for x in root[1:])+'\n)\n')
 occupied={k.F_SilkS:[],k.B_SilkS:[]}
 for f in b.GetFootprints():
  for p in f.Pads():
   for lay,mask in [(k.F_SilkS,k.F_Mask),(k.B_SilkS,k.B_Mask)]:
    if p.IsOnLayer(mask):occupied[lay].append(bb(p))
  for g in [*f.GraphicalItems(),f.Reference(),f.Value()]:
   if g.GetLayer()in occupied and (not hasattr(g,'IsVisible')or g.IsVisible()):occupied[g.GetLayer()].append(bb(g))
  r=rect(f)
  if r:occupied[k.B_SilkS if f.IsFlipped()else k.F_SilkS].append(r)
 for v in b.GetTracks():
  if isinstance(v,k.PCB_VIA):
   for l in occupied:occupied[l].append(bb(v))
 for t in b.GetDrawings():
  if t.GetLayer()in occupied:occupied[t.GetLayer()].append(bb(t))
 def label(text,pos,lay=k.F_SilkS,fs=.8,angle=0,range_=2):
  fs=max(.8,fs)
  t=k.PCB_TEXT(b);t.SetText(text);t.SetLayer(lay);t.SetTextSize(pt(fs,fs));t.SetTextThickness(mm(.12));t.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T));t.SetMirrored(lay==k.B_SilkS)
  options=[]
  for i in range(-int(range_*4),int(range_*4)+1):
   for j in range(-int(range_*4),int(range_*4)+1):options.append((abs(i)+abs(j),abs(i),i/4,j/4))
  for _,__,dx,dy in sorted(options):
   t.SetPosition(pt(pos[0]+dx,pos[1]+dy));r=bb(t)
   if r[0]<.3 or r[1]<.3 or r[2]>size[0]-.3 or r[3]>size[1]-.3:continue
   if any(intersects(r,x)for x in occupied[lay]):continue
   b.Add(t);group.AddItem(t);occupied[lay].append(r);record.append(dict(text=text,layer=b.GetLayerName(lay),xy_mm=xy(t.GetPosition()),size_mm=fs,angle=angle));return True
  blocked.append(dict(text=text,position=pos,layer=b.GetLayerName(lay)));return False
 if kind=='motion':
  label('MORI P5R5',(40,15),k.B_SilkS,.9,angle=90,range_=6)
  label('MOTION',(20,10),k.B_SilkS,.9,range_=5)
  label('PROTO',(20,20),k.B_SilkS,.8,range_=5)
  ff=[('J1 5V',(59.5,5.6)),('J2 WHEEL',(52,5.6)),('J3 HEAD',(64,21)),('J4 IMU 3V3',(58,27.7)),('J5 CAM',(53.5,21)),('J6 KEY',(51.5,28.7)),('J7 CTRL',(58,13.5)),('J8 LOOP',(59.5,28.7))]
  for t,pp in ff:label(t,pp,k.B_SilkS,.75,range_=4)
  for text,pp in [('G',(60.5,1.5)),('G',(53,1.5)),('1',(49.1,31.3)),('1',(56.8,31.3))]:label(text,pp,k.B_SilkS,.65,range_=.5)
  for ref in ['J1','J2','J3','J4','J5','J6','J7','J8']:
   label(ref,tuple(x+1.5 for x in xy(e.f[ref].GetPosition())),fs=.65,range_=2)
   pin=e.pad(ref,1);x,y=xy(pin.GetPosition());label('1',(x,y-1.5),k.B_SilkS,.65,range_=.5)
   for pin in e.f[ref].Pads():
    if pin.GetNetname()=='/GND':
     x,y=xy(pin.GetPosition());label('G',(x,y+1.5),k.B_SilkS,.65,range_=.5)
 else:
  label('MORI POWER P5R5',(20,12),k.B_SilkS,1,range_=5)
  label('PROTOTYPE / 3S INPUT',(20,15),k.B_SilkS,.8,range_=4)
  ff=[('J1 PACK IN',(11.5,1.5)),('J2 W-BUCK IN',(24.5,.7)),('J3 9V IN',(37.5,.7)),('J6 H-BUCK IN',(50.5,.7)),('J11 W-DUMP',(63.5,.7)),('J18 CAM 5V',(13.5,53.7)),('J4 H-BUCK IN',(27.5,54.5)),('J5 6V IN',(42.5,54.5)),('J12 H-DUMP',(67.5,54.5)),('J7 WHEEL L',(78.6,16.5)),('J8 WHEEL R',(65.5,29)),('J9 HEAD 6V',(66.5,45.6)),('J10 CONTROL',(41,34)),('J13 W-BUS',(78.6,32.5)),('J14 H-BUS',(78.6,41)),('J19 MASTER',(1.0,16)),('J17 MOT 5V',(1.0,23)),('J15 CHG',(1.0,30)),('J16 VBUS',(1.0,45)),('JP60 OFF',(4,36.8)),('JP70 OFF',(38.2,46.3)),('TP60 5V',(9.5,34)),('TP61 GND',(13,34)),('TP70 5V',(35,53)),('TP71 GND',(34.5,46.2))]
  for t,pp in ff:
   if not label(t,pp,fs=.8,angle=90 if pp[0]in[1.,78.6,41]else 0,range_=1.25):
    ref=t.split()[0];f=e.f[ref];x,y=xy(f.GetPosition());p2=list(f.Pads())[-1].GetPosition();xx,yy=xy(p2)
    label(t,((x+xx)/2,(y+yy)/2+2.6),k.B_SilkS,.8,range_=3)
  # Individual key markings are intentionally short and adjacent to the
  # connector. The full wire/pin table remains a separate assembly document.
  for ref in ['J1','J2','J3','J4','J5','J6','J7','J8','J9','J10','J11','J12','J13','J14','J15','J16','J17','J18','J19']:
   pins=list(e.f[ref].Pads())
   for pin in pins:
    if pin.GetNumber()=='1' or pin.GetNetname()=='/GND':
     x,y=xy(pin.GetPosition());text='1G'if pin.GetNumber()=='1'and pin.GetNetname()=='/GND'else('1'if pin.GetNumber()=='1'else'G')
     vertical=abs(e.f[ref].GetOrientationDegrees())==90
     pos=(x+(-2.1 if x>40 else 2.1),y)if vertical else(x,y-2.1)
     label(text,pos,k.B_SilkS,.8,range_=.75)
  back=[('J1 1:GND 2:PACK',(11,10)),('J2/J4/J6 1:GND 2:BAT',(30,8)),('J3 1:GND 2:9V',(39,10)),('J5 1:GND 2:6V',(41,45)),('J11/J12 1:DUMP 2:VM',(61,11)),('J7/J8/J9 1:GND 2:VM 3:BUS',(63,30)),('J17/J18 1:5V 2:GND',(14,35)),('J13/J14 1:BUS 2:GND',(66,37)),('J14 PIN3 NC',(72,45)),('J19 1:MASTER 2:GND',(15,17)),('J15 1:CHG 2:GND',(14,27)),('J16 1:VBUS 2:GND',(15,46)),('J10 1:3V3 2:ARM 3:FAULT 4:CHG',(46,23)),('5:BAT 6:VM 7:CURRENT 8:GND',(46,26)),('JP60/70 1:EN 2:GND',(44,42))]
  for t,pp in back:label(t,pp,k.B_SilkS,.7,range_=4)
 e.save();dump(e.r/'silkscreen_labels.json',dict(labels=record,unplaced=blocked,meaning='G denotes GND; all pin numbers refer to native pads, not visual left/right',printed_status='PROTOTYPE_NOT_MANUFACTURED'));print(kind,'placed',len(record),'unplaced',blocked,flush=True)
if __name__=='__main__':
 for kind in sys.argv[1:]or KINDS:run(kind)
