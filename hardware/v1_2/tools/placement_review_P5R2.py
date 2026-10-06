import pcbnew as k,sys
from review_edit_P5R2 import Edit,F,B,xy
e=Edit(sys.argv[1])
if e.kind=='imu':
 e.move('R1',(6.5,8.85),180)
 e.remove(net='/MISO_IC',predicate=lambda t:not isinstance(t,k.PCB_VIA))
 e.add('/MISO_IC',F,[(7.325,8.85),(8.8375,8.85)])
 e.remove(net='/MISO',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==F and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<8)
 e.add('/MISO',F,[(5.675,8.85),(5.2,8.375),(5.2,7.4492),(5.6388,7.0104)])
 e.commit('R1 rotated 90 degrees: direct horizontal MISO_IC and outward MISO input; compare against folded diagonal input')
elif e.kind=='motion':
 e.move('R13',(46,19.5),90)
 e.remove(net='/IMU_CS',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==B and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>30)
 e.add('/IMU_CS',B,[(37.592,21.336),(45.35,21.336),(45.7564,20.9296),(58.115199,20.9296),(59.943999,22.7584),(59.943999,24.485599),(60.452,24.9936)])
 e.add('/IMU_CS',B,[(46,20.325),(46,20.9296)])
 e.remove(net='/+3V3',predicate=lambda t:not isinstance(t,k.PCB_VIA)and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>43 and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<46 and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>19 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<21)
 e.commit('R13 rotation and slight translation: CS straight corridor with outward perpendicular pull-up branch')
 e.move('C9',(12.2,28),0)
 e.remove(net='/BAT_ADC',predicate=lambda t:not isinstance(t,k.PCB_VIA))
 e.add('/BAT_ADC',B,[(11.125,25.825),(11.125,26.8),(11.425,27.1),(11.425,28)])
 e.add('/BAT_ADC',B,[(11.425,28),(11.18,28.245),(11.18,31.47),(12.45,32.74)])
 e.remove(net='/GND',predicate=lambda t:not isinstance(t,k.PCB_VIA)and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>12 and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<15 and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>27 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<29)
 e.commit('C9 small placement trial: align ADC corridor between header pads, remove S-shaped offset')
else:raise SystemExit(e.kind)
