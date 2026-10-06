"""Provisional parallel layer transitions, sized by documented DC-drop scenario.
Not a thermal current rating. Source is the accepted local-return revision.
"""
from review_P5R3 import *
from geometry_guard_P5 import Guard
e=Edit('power')
arrays=[
 ('BAT_MON_MAIN','/BAT_MON',[(35.7632,14.6304),(34.5632,14.6304),(33.3632,14.6304),(32.1632,14.6304)],1.,.45,6.48),
 ('BAT_MON_WHEEL','/BAT_MON',[(30.6324,6.5024),(30.6324,5.3024),(30.6324,4.1024)],1.,.45,3.8),
 ('BAT_MON_F60','/BAT_MON',[(32.003999,20.7264),(33.203999,20.7264)],.8,.3,.55),
 ('W_VM_MAIN','/W_VM',[(58.3184,10.6172),(57.3184,10.6172),(58.3184,9.6172)],1.,.45,3.34),
 ('W_VM_J8','/W_VM',[(61.2648,22.86),(62.4648,22.86),(63.6648,22.86)],1.,.45,3.34),
]
rows=[]
for name,net,ps,vd,dr,current in arrays:
 g=Guard(e.b,net)
 for p in ps[1:]:
  assert g.via_clear(p,vd),(name,p)
  e.via(net,p,vd,dr)
 # Small solid islands join the complete rings on BOTH outer layers. Inner
 # GND is preserved; it clears these barrels in the normal zone fill.
 margin=vd/2+.12
 x1=min(p[0] for p in ps)-margin;y1=min(p[1] for p in ps)-margin
 x2=max(p[0] for p in ps)+margin;y2=max(p[1] for p in ps)+margin
 for layer in [F,B]:
  z=k.ZONE(e.b);z.SetLayer(layer);z.SetNet(e.b.GetNetsByName()[net]);z.SetZoneName('P5R3_PARALLEL_'+name+'_'+e.b.GetLayerName(layer));z.SetAssignedPriority(4)
  z.SetLocalClearance(mm(.2));z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
  p=z.Outline();p.NewOutline()
  for xy_ in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:p.Append(int(mm(xy_[0])),int(mm(xy_[1])))
  e.b.Add(z)
 rho=1.724e-5*(1+.00393*(80-20));rv=rho*1.6/(math.pi*dr*.015)
 rows.append(dict(id=name,net=net,centres_mm=ps,via_diameter_mm=vd,drill_mm=dr,scenario_A=current,
                  assumed_barrel_plating_mm=.015,assumed_temperature_C=80,
                  ideal_single_barrel_mOhm=rv*1000,ideal_parallel_mV=current*rv/len(ps)*1000,
                  ideal_one_barrel_absent_mV=current*rv/(len(ps)-1)*1000,
                  criterion='barrel-only DC drop <= 5 mV with one of N barrels absent; provisional, not a current rating',
                  limitations='no copper spreading resistance, nonuniform sharing, temperature rise, inductance, plating tolerance or PCB vendor qualification'))
ok,j=e.check('PWR03_parallel_vias')
if ok:dump(e.r/'parallel_via_model.json',rows)
