"""Rebuild only the two buck cells from immutable P5R3. No manufacturing output.
Revision 2: move ICs 2 mm right, compact FB bank, outward SW on bottom.
Full native DRC, actual filled-return verification and bench tests are required.
"""
from review_P5R5 import *
def area(e,name,layer,points):
 z=k.ZONE(e.b);z.SetZoneName(name);z.SetLayer(layer);z.SetIsRuleArea(True)
 z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
 poly=z.Outline();poly.NewOutline()
 for x,y in points:poly.Append(mm(x),mm(y))
 e.b.Add(z)
def rebuild():
 _,_,p,r=paths('power');p.write_bytes(source('power')[2].read_bytes());e=Edit('power')
 for n,y,pre,out in [(60,26,'M5','+5V_MOTION'),(70,40,'C5','+5V_CAM')]:
  dy=y-26;dx=0 if n==60 else -.75;bulk_y=30.6 if n==60 else 30.4;P=lambda a:[(x,yy+dy)for x,yy in a]
  wire=lambda net,layer,a,w:e.add('/'+net,layer,P(a),w)
  hole=lambda net,p,vd=.8,dr=.3:e.via('/'+net,(p[0],p[1]+dy),vd,dr)
  e.remove(net='/GND',predicate=lambda t:16<xy(t.GetPosition())[0]<34 and y-5<xy(t.GetPosition())[1]<y+8.5)
  for net in [pre+'_VIN',pre+'_SW',pre+'_FB',pre+'_BOOT']:e.remove(net='/'+net)
  e.remove(net='/'+out,predicate=lambda t:xy(t.GetPosition())[0]>14 and y-1<xy(t.GetPosition())[1]<y+8)
  for ref,pos,angle in [(f'U{n}',(27+dx,y),0),(f'C{n+1}',(23.2+dx,y),90),(f'C{n}',(22.5,bulk_y+dy),-90),(f'C{n+6}',(26.5,bulk_y+dy),-90),(f'C{n+2}',(28.35+dx,y-3.4-(.5 if n==70 else 0)),90),(f'R{n}',(30,y+2.55),180),(f'R{n+1}',(30,y+4.1),0),(f'C{n+5}',(29.7,y+5.65),180)]:
   if ref.startswith('U'):
    # Preserve exact-sized inner keepouts, translate to the actual IC body.
    for z in e.b.Zones():
     if z.GetZoneName().startswith(f'P5_BUCK_RETURN_AVOID_{ref}_'):z.Move(pt(2+dx,0))
   e.move(ref,pos,angle)
  vpos=bulk_y-1.475;gpos=bulk_y+1.475
  wire(pre+'_VIN',F,[(25.65+dx,26.95),(25+dx,27.6),(24.025+dx,27.6),(23.2+dx,26.775)],.5)
  wire(pre+'_VIN',F,[(23.2+dx,26.775),(22.5,27.475-dx),(22.5,vpos)],.8)
  wire(pre+'_VIN',F,[(25.65+dx,26.95),(25.65+dx,vpos-.85-dx),(26.5,vpos)],.8)
  wire(pre+'_VIN',F,[(24.45,27.6),(24.45,27.9)],.5);hole(pre+'_VIN',(24.45,27.9))
  if n==60:
   wire(pre+'_VIN',F,[(31.545,23),(29.6,23)],.8);hole(pre+'_VIN',(29.6,23),1,.45)
   wire(pre+'_VIN',B,[(29.6,23),(29.6,27.2),(29,27.8),(24.55,27.8),(24.45,27.9)],.6)
  else:
   wire(pre+'_VIN',F,[(30.5,25.455),(30.5,27.3)],.8);hole(pre+'_VIN',(30.5,27.3),1,.45)
   wire(pre+'_VIN',B,[(30.5,27.3),(29.5,27.3),(29,27.8),(24.55,27.8),(24.45,27.9)],.6)
  wire('GND',F,[(25.65+dx,25.05),(25.1+dx,25.05),(24.65+dx,24.6),(23.825+dx,24.6),(23.2+dx,25.225)],.5)
  wire('GND',F,[(23.2+dx,25.225),(21.5,25.225),(21.5,26.5),(20.4,27.6),(20.4,gpos),(22.5,gpos)],.6)
  wire('GND',F,[(26.5,gpos),(26.5,bulk_y+2.2),(22.5,bulk_y+2.2),(22.5,gpos)],.8)
  hole('GND',(21.5,26.5));wire('GND',F,[(20.4,gpos),(20.4,gpos-1.3)],.8)
  hole('GND',(20.4,gpos));hole('GND',(20.4,gpos-1.3))
  wire(pre+'_SW',F,[(25.65+dx,26),(24.35+dx,26)],.6);hole(pre+'_SW',(24.35+dx,26),1,.45)
  wire(pre+'_SW',B,[(24.35+dx,26),(24.35+dx,24),(21.5,24)],.8)
  wire(pre+'_SW',F,[(21.5,24),(19.225,24)],.8);hole(pre+'_SW',(21.5,24),1,.45)
  by=20.65 if n==60 else 20.15
  wire(pre+'_SW',B,[(24.35+dx,24),(24.35+dx,by),(28.35+dx,by)],.6)
  hole(pre+'_SW',(28.35+dx,by));wire(pre+'_SW',F,[(28.35+dx,by),(28.35+dx,by+1.175)],.5)
  wire(pre+'_BOOT',F,[(28.35+dx,by+2.725),(28.35+dx,25.05)],.2)
  wire(pre+'_FB',F,[(28.35+dx,26.95),(28.6,27.2-dx),(28.6,31.65),(28.925,31.65)],.2)
  wire(pre+'_FB',F,[(28.6,28.55),(29.175,28.55)],.2)
  wire(pre+'_FB',F,[(28.6,30.1),(29.175,30.1)],.2)
  wire(out,F,[(30.825,28.55),(32.75,28.55),(32.75,31.65),(30.475,31.65)],.2)
  if n==60:
   wire(out,F,[(32.75,28.55),(32.75,27.2),(30.5,27.2)],.2);hole(out,(30.5,27.2))
  else:
   wire(out,F,[(32.75,28.55),(32.75,27.5),(32.3,27.5)],.2);hole(out,(32.3,27.5))
  wire('GND',F,[(30.825,30.1),(31.8,30.1),(31.8,29.5)],.2);hole('GND',(31.8,29.5))
  wire('GND',k.In1_Cu,[(31.8,29.5),(29,29.5),(29,24.3),(26.25+dx,24.3),(25.65+dx,23.7)],.2)
  hole('GND',(25.65+dx,23.7));wire('GND',F,[(25.65+dx,23.7),(25.65+dx,25.05)],.2)
  for lay in [F,k.In1_Cu,k.In2_Cu,B]:
   for label,x0,y0,x1,y1 in [('FBvia',31.2,28.9,32.4,30.1),('starvia',25.05+dx,23.1,26.25+dx,24.3)]:
    area(e,f'P5R5_QUIET_{n}_{label}_{lay}',lay,P([(x0,y0),(x1,y0),(x1,y1),(x0,y1)]))
  area(e,f'P5R5_QUIET_{n}_Rground',F,P([(30.3,29.6),(31.2,29.6),(31.2,28.9),(32.4,28.9),(32.4,30.6),(30.3,30.6)]))
  area(e,f'P5R5_QUIET_{n}_Ireturn',k.In1_Cu,P([(25.05+dx,23.1),(26.85+dx,23.9),(29.4,23.9),(29.4,29.1),(32.4,29.1),(32.4,29.9),(28.6,29.9),(28.6,24.7),(26.1+dx,24.7),(25.05+dx,24.1)]))
 for net in ['/M5_EN','/C5_EN','/WHEEL_ADC','/CHG_N']:e.remove(net=net)
 e.add('/C5_EN',F,[(27.6,40),(28.5,40),(28.5,37.85)],.2);e.via('/C5_EN',(28.5,37.85))
 dru=paths('power')[1]/'MORI_power_P5R5.kicad_dru'
 srcdru=(source('power')[1]/'MORI_power_P5R3.kicad_dru').read_text()
 srcdru=srcdru.replace('(rule "P5 R13 In1.Cu no tracks" (layer In1.Cu) (condition "A.Type == \'Track\' || A.Type == \'Arc\'")','(rule "P5 R13 In1.Cu localized FB ground return" (layer In1.Cu) (condition "(A.Type == \'Track\' || A.Type == \'Arc\') && !(A.NetName == \'/GND\' && (A.intersectsArea(\'P5R5_QUIET_60_Ireturn\') || A.intersectsArea(\'P5R5_QUIET_70_Ireturn\')))")')
 dru.write_text(srcdru)
 e.save();(r/'buck_stage_05.kicad_pcb').write_bytes(p.read_bytes());print('Stage 5 saved; DRC acceptance pending',flush=True)
if __name__=='__main__':rebuild()
