from review_P5R3 import *

def kelvin():
 e=Edit('power')
 # Keep the reverse-gate clamp off the independent shunt sense branch.
 e.remove(ids=['d703b3d9','1929f594','06ce25d1','d7ec241f','f073fcf3','f0213282'])
 e.add('/BAT_REV',F,[(26.375,13.905),(27.675,13.905),(28.175,14.405),(28.175,17.5),(27.4,17.5)],.2)
 e.add('/BAT_REV',F,[(30.0375,13.35),(30.0375,14.6),(29.175,15.4625),(29.175,16.5)],.2)
 # Separate the load takeoff to the right from the shunt's lower sense takeoff.
 e.remove(ids=['7da95d9c','adc86355','f97c57d7','c777c33e'])
 e.add('/BAT_MON',F,[(35.9625,12),(35.9625,14.4311),(35.7632,14.6304)],1)
 e.add('/BAT_MON',F,[(38,11.775),(37.35,12.425),(36.3,12.425)],.4)
 e.add('/BAT_MON',F,[(36.45,13.35),(38,14.9),(38,15.675)],.2)
 return e.check('PWR01_kelvin')

def buck():
 e=Edit('power')
 # Local input bypass now presents its ground toward the open left-hand corridor.
 # Rebuild the input nets independently of the high-impedance feedback area.
 for n,y,prefix in [(60,26,'M5'),(70,40,'C5')]:
  e.remove(net='/'+prefix+'_VIN')
  e.move('C'+str(n+1),(22.1,y+2.5),180)
  if n==60:e.move('C60',(19.5,31),180)
  e.add('/'+prefix+'_VIN',F,[(23.65,y+.95),(23.65,y+2.5),(22.875,y+2.5)],.6)
  if n==60:
   e.add('/M5_VIN',F,[(20.975,31),(23.15,31),(23.65,30.5),(23.65,29.525),(26,29.525)],.8)
   e.add('/M5_VIN',F,[(23.65,28.5),(23.65,29.525)],.8)
  else:
   e.add('/C5_VIN',F,[(20.975,45),(24.525,45)],.8)
   e.add('/C5_VIN',F,[(23.65,42.5),(23.65,45)],.8)
 # A routing checkpoint is retained only for the ensuing local completion.
 e.save()
 dump(e.r/'buck_stage.json',{'status':'IN_PROGRESS','source_sha256':hashlib.sha256(e.saved).hexdigest()})
 (e.r/'before_buck.kicad_pcb').write_bytes(e.saved)
 print('buck local placement staged')

def buck_finish():
 e=Edit('power')
 e.move('C76',(26,44.1),270)
 e.remove(net='/C5_VIN',predicate=lambda t:not isinstance(t,k.PCB_VIA)and xy(t.GetStart())in[(20.975,45),(23.65,42.5)])
 e.add('/C5_VIN',F,[(20.975,45),(23.15,45),(23.65,44.5),(23.65,42.625),(26,42.625)],.8)
 e.add('/C5_VIN',F,[(23.65,42.5),(23.65,42.625)],.8)
 # Historical inductor core areas were still centred on an old placement.
 for z in e.b.Zones():
  if z.GetZoneName()=='NO_UNDER_INDUCTOR_L60':z.Move(pt(-4,4))
  if z.GetZoneName()=='NO_UNDER_INDUCTOR_L70':z.Move(pt(-4,-2))
 e.remove(ids=['4af0a2dd','e2cfde8b','f2a9aea4'])
 # Reconnect these small-signal takeoffs after the local power cell is complete.
 e.remove(net='/WHEEL_ADC')
 for net in ['/+5V_MOTION','/+5V_CAM']:
  e.remove(net=net,predicate=lambda t:isinstance(t,k.PCB_VIA)or k.ToMM(t.GetWidth())<.4)
 # Motion feedback: component orientation puts both high-Z pads on the top side.
 e.remove(net='/M5_FB')
 e.remove(ids=['b0716ca2'])
 e.move('R60',(31.5,29),90);e.move('R61',(28.9,25.4),90)
 e.add('/M5_FB',F,[(26.35,26.95),(28.175,26.95),(28.9,26.225)],.2)
 e.add('/M5_FB',F,[(28.9,26.225),(28.9,27.725),(29.4,28.225),(31.45,28.225),(31.5,28.175)],.2)
 e.add('/M5_FB',F,[(29,28.225),(29.4,28.225)],.2)
 e.add('/+5V_MOTION',F,[(29,29.775),(29,30.15),(29.5,30.65),(31,30.65),(31.5,30.15),(31.5,29.825)],.2)
 # Local input power reaches the bypass bank from the bottom layer, outside FB.
 e.via('/M5_VIN',(29.7,23),1,.45);e.add('/M5_VIN',F,[(31.545,23),(29.7,23)],.8)
 e.via('/M5_VIN',(24.05,28.2),1,.45);e.add('/M5_VIN',F,[(24.05,28.2),(23.65,28.2)],.8)
 e.add('/M5_VIN',B,[(29.7,23),(29.7,26.9),(28.75,27.85),(24.4,27.85),(24.05,28.2)],.6)
 e.via('/C5_VIN',(30.5,41.2),1,.45);e.add('/C5_VIN',F,[(30.5,39.455),(30.5,41.2)],.8)
 e.via('/C5_VIN',(24.05,42.2),1,.45);e.add('/C5_VIN',F,[(24.05,42.2),(23.65,42.2)],.8)
 e.add('/C5_VIN',B,[(30.5,41.2),(29.2,41.2),(28.2,42.2),(24.05,42.2)],.8)
 # Dedicated ground-plane access immediately outside each capacitor land.
 for ref,points,w in [
  ('C61',[(21.325,28.5),(21.325,27.3)],.5),('C71',[(21.325,42.5),(21.325,41.3)],.5),
  ('C60',[(18.025,31),(16.825,31)],.8),('C66',[(26,32.475),(26,34.075)],.8),
  ('C70',[(18.025,45),(18.025,43)],.8),
  ('C63',[(10,21.525),(10,20.325)],.8),('C64',[(10,29.475),(10,30.675)],.8),
  ('C73',[(10,35.525),(10.6,34.925),(10.6,34.325)],.8),('C74',[(10,43.475),(10,44.675)],.8),
  ('R61',[(28.9,24.575),(28.9,24.1),(28.1,23.3)],.2)]:
  e.add('/GND',F,points,w);e.via('/GND',points[-1])
 from geometry_guard_P5 import Guard
 g=Guard(e.b,'/GND')
 for dist,p,route in g.portals(e.pos('C76',2),F,radius=3.5,step=.2,vd=.8):
  if all(g.line_clear(u,v,F,.6)for u,v in zip(route,route[1:])):
   e.add('/GND',F,route,.6);e.via('/GND',p);print('C76 ground',p,flush=True);break
 else:raise RuntimeError('No C76 local ground via')
 # Replace the undersized pre-existing U60 ground via, retaining its location.
 for t in e.b.GetTracks():
  if isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==(23.45,24.0):t.SetWidth(mm(.8))
 e.save();(e.r/'buck_finish_stage.kicad_pcb').write_bytes(e.p.read_bytes())
 # Only the low-current output sense feed and displaced ADC are searched.
 import close_P5
 close_P5.paths=paths
 close_P5.run('power',nets=['/+5V_MOTION','/+5V_CAM','/WHEEL_ADC'],widths={'/+5V_MOTION':.2,'/+5V_CAM':.2,'/WHEEL_ADC':.2})
 e.b=k.LoadBoard(str(e.p));return e.check('PWR02_buck')

if __name__=='__main__':
 if sys.argv[1]=='kelvin':kelvin()
 if sys.argv[1]=='buck':buck()
 if sys.argv[1]=='buck_finish':buck_finish()
