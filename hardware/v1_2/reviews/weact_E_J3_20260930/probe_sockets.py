from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
from collections import Counter
OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'long_socket_screen_source.kicad_pcb'))
remove=set(json.loads((OUT/'long_socket_routes.json').read_text())['removed'])
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove or t.GetNetname() in ['/WHEEL_ADC_IN','/CURRENT_ADC_IN']: b.Delete(t)
for net,points in [('/S288_BUS',[(33.125,8.75),(34,8.75),(35,8.75),(35.8,8.75),(36.6,7.95),(38,7.95),(42,7.95),(45,7.95),(46,7),(47,5),(48,5)]),('/CURRENT_ADC_IN',[(17.625,24.175),(17.625,23.2),(18.5,23.2),(19.3,23.2),(21,22),(25,21),(30,16.5),(39,16.5),(43,16.5),(47,16.5)])]:
 for q in points:
  print(net,q,{b.GetLayerName(l):obstacles(b,net,q,l) for l in [k.F_Cu,k.B_Cu]},'VIA',Guard(b,net).via_clear(q))
print('zones')
for z in b.Zones():
 if z.GetIsRuleArea():
  bb=z.Outline().BBox(); a=[k.ToMM(v)for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
  if a[0]<50 and a[2]>30 and a[1]<12:print(z.GetZoneName(),z.GetDoNotAllowTracks(),z.GetDoNotAllowVias(),a)
