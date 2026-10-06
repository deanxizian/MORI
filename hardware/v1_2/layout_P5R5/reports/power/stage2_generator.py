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
  dy=y-26;P=lambda a:[(x,yy+dy)for x,yy in a]
  wire=lambda net,layer,a,w:e.add('/'+net,layer,P(a),w)
  hole=lambda net,p,vd=.8,dr=.3:e.via('/'+net,(p[0],p[1]+dy),vd,dr)
  e.remove(net='/GND',predicate=lambda t:16<xy(t.GetPosition())[0]<34 and y-5<xy(t.GetPosition())[1]<y+8.5)
  for net in [pre+'_VIN',pre+'_SW',pre+'_FB',pre+'_BOOT']:e.remove(net='/'+net)
  e.remove(net='/'+out,predicate=lambda t:xy(t.GetPosition())[0]>14 and y-1<xy(t.GetPosition())[1]<y+8)
  for ref,pos,angle in [(f'U{n}',(27,y),0),(f'C{n+1}',(23.2,y),90),(f'C{n}',(22.5,y+4),-90),(f'C{n+6}',(26.5,y+4),-90),(f'C{n+2}',(28.35,y-2.9),90),(f'R{n}',(31.2,y+1.7),180),(f'R{n+1}',(31.2,y+3.3),0),(f'C{n+5}',(31.2,y+4.9),180)]:
   if ref.startswith('U'):
    # Preserve exact-sized inner keepouts, translate to the actual IC body.
    for z in e.b.Zones():
     if z.GetZoneName().startswith(f'P5_BUCK_RETURN_AVOID_{ref}_'):z.Move(pt(2,0))
   e.move(ref,pos,angle)
  wire(pre+'_VIN',F,[(25.65,26.95),(25,27.6),(24.025,27.6),(23.2,26.775)],.5)
  wire(pre+'_VIN',F,[(23.2,26.775),(22.5,27.475),(22.5,28.525)],.8)
  wire(pre+'_VIN',F,[(25.65,26.95),(25.65,27.675),(26.5,28.525)],.8)
  wire(pre+'_VIN',F,[(26.5,28.525),(29,28.525)],.8);hole(pre+'_VIN',(29,28.525),1,.45)
  if n==60:
   wire(pre+'_VIN',F,[(31.545,23),(29.6,23)],.8);hole(pre+'_VIN',(29.6,23),1,.45)
   wire(pre+'_VIN',B,[(29.6,23),(29.6,27.925),(29,28.525)],.8)
  else:
   wire(pre+'_VIN',F,[(30.5,25.455),(30.5,26.5),(29,28)],.8);hole(pre+'_VIN',(29,28),1,.45)
   wire(pre+'_VIN',B,[(29,28),(29,28.525)],.8)
  wire('GND',F,[(25.65,25.05),(25.1,25.05),(24.65,24.6),(23.825,24.6),(23.2,25.225)],.5)
  wire('GND',F,[(23.2,25.225),(21.5,25.225),(21.5,31.475),(22.5,31.475)],.6)
  wire('GND',F,[(26.5,31.475),(26.5,32.8),(22.5,32.8),(22.5,31.475)],.8)
  hole('GND',(21.5,27.4));wire('GND',F,[(21.5,31.475),(20.3,31.475),(20.3,30.2)],.8)
  hole('GND',(20.3,31.475));hole('GND',(20.3,30.2))
  wire(pre+'_SW',F,[(25.65,26),(24.35,26)],.6);hole(pre+'_SW',(24.35,26),1,.45)
  wire(pre+'_SW',B,[(24.35,26),(24.35,24),(21.5,24)],.8)
  wire(pre+'_SW',F,[(21.5,24),(19.225,24)],.8);hole(pre+'_SW',(21.5,24),1,.45)
  wire(pre+'_SW',B,[(24.35,24),(24.35,21.15),(28.35,21.15)],.6)
  hole(pre+'_SW',(28.35,21.15));wire(pre+'_SW',F,[(28.35,21.15),(28.35,22.325)],.5)
  wire(pre+'_BOOT',F,[(28.35,23.875),(28.35,25.05)],.2)
  wire(pre+'_FB',F,[(28.35,26.95),(29.05,27.65),(29.05,30.9),(30.425,30.9)],.2)
  wire(pre+'_FB',F,[(29.05,27.7),(30.375,27.7)],.2)
  wire(pre+'_FB',F,[(29.05,29.3),(30.375,29.3)],.2)
  wire(out,F,[(32.025,27.7),(33.3,27.7),(34.1,28.5),(34.1,30.9),(31.975,30.9)],.2)
  hole(out,(34.1,28.5))
  wire('GND',F,[(32.025,29.3),(33.2,29.3)],.2);hole('GND',(33.2,29.3))
  wire('GND',B,[(33.2,29.3),(33.2,32.8),(28.1,32.8),(28.1,23.7),(25.65,23.7)],.2)
  hole('GND',(25.65,23.7));wire('GND',F,[(25.65,23.7),(25.65,25.05)],.2)
  for lay in [F,k.In1_Cu,k.In2_Cu,B]:
   for label,x0,y0,x1,y1 in [('FBvia',32.6,28.7,33.8,29.9),('starvia',25.05,23.1,26.25,24.3)]:
    area(e,f'P5R5_QUIET_{n}_{label}_{lay}',lay,P([(x0,y0),(x1,y0),(x1,y1),(x0,y1)]))
  area(e,f'P5R5_QUIET_{n}_Rground',F,P([(31.5,28.65),(33.8,28.65),(33.8,29.95),(31.5,29.95)]))
  area(e,f'P5R5_QUIET_{n}_Breturn',B,P([(25.15,23.3),(28.5,23.3),(28.5,32.4),(32.8,32.4),(32.8,28.7),(33.6,28.7),(33.6,33.2),(27.7,33.2),(27.7,24.1),(25.15,24.1)]))
 for net in ['/M5_EN','/C5_EN','/WHEEL_ADC','/CHG_N']:e.remove(net=net)
 e.save();(r/'buck_stage_02.kicad_pcb').write_bytes(p.read_bytes());print('Stage 2 saved; DRC acceptance pending',flush=True)
if __name__=='__main__':rebuild()
