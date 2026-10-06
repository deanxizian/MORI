"""Outward escape corridors on unpublished C2; retains original rules."""
from candidate import *
from geometry_guard_P5 import Guard
def run():
 b=load();fs={f.GetReference():f for f in b.GetFootprints()}
 move(b,fs['D30'],(37.5,35.));move(b,fs['R50'],(40.5,24.3))
 for t in list(b.GetTracks()):
  if t.GetNetname()in ['/H_PRE','/H6_IN','/BAT_ADC','/WHEEL_ADC']:b.Delete(t)
 routes=[
  ('/H_PRE',k.B_Cu,[(37.7,31.6),(37.7,23.7),(38.4,23),(47.6,23),(48.5,23.9),(48.5,27.5),(50.5,29.5)],1.),
  ('/H_PRE',k.F_Cu,[(50.5,29.5),(50.5,31.525),(52.905,31.525)],1.),
  ('/H_PRE',k.F_Cu,[(49.825,29.5),(50.5,29.5)],.2),
  ('/H6_IN',k.B_Cu,[(37.5,38.4),(37.5,43.7),(38,44.2),(48,44.2),(49,45.2),(49,49),(48,50),(45,50)],1.),
  ('/BAT_ADC',k.B_Cu,[(41.325,24.3),(46.5,24.3),(46.5,35),(44.5,35)],.2),
  ('/WHEEL_ADC',k.F_Cu,[(44.5,37),(47.1,37),(47.1,27.0),(46.6,26.5),(46.6,23.0),(47.5,23.0),(47.5,23.675)],.2),
  ('/WHEEL_ADC',k.F_Cu,[(44.675,21),(46.5,21),(47.5,22),(47.5,23.675)],.2),
 ]
 for net,layer,points,w in routes:track(b,net,points,w,layer)
 via(b,'/H_PRE',50.5,29.5,vd=1.,dr=.45,grid=False)
 # Divider output needs a separate safe via to the F-face lower resistor.
 via(b,'/BAT_ADC',42.8,23.7,vd=.8,dr=.3,grid=False)
 track(b,'/BAT_ADC',[(42.8,23.7),(42.8,24.3)],.2,k.B_Cu)
 track(b,'/BAT_ADC',[(40.175,22),(40.175,22.7),(41.175,23.7),(42.8,23.7)],.2,k.F_Cu)
 save(b);dump(R/'04_manual_routes.json',dict(D30_xy=[37.5,35],R50_xy=[40.5,24.3],routes=routes,reason='Create2mm bulk corridor between F70 and D30; J10 numbered holes unchanged; no rule exemptions.'))
 check('04_manual')
if __name__=='__main__':run()
