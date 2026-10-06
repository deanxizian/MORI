"""Explicit placement/route trials from the complete per-net review atlas."""
import sys,pcbnew as k
from review_edit_P5R2 import Edit,F,B,xy
kind=sys.argv[1];e=Edit(kind)
if kind=='imu':
 e.remove(['7912ac08','d3b36e18','ee469b89'])
 e.add('/GND',F,[(11.1625,8.85),(11.6186,8.85),(12.1158,9.3472)])
 e.add('/GND',F,[(11.1625,9.85),(11.613,9.85),(12.1158,9.3472)])
 e.commit('U1 ground pins: replace two short free right angles with outward horizontal/45-degree entries into existing ground via')
 e.remove(net='/+3V3',predicate=lambda t:not isinstance(t,k.PCB_VIA))
 e.add('/+3V3',F,[(3,3.5),(3,7.8),(7.7,12.5),(8.225,12.5)])
 e.add('/+3V3',F,[(9.5,10.5125),(9.5,11.05),(9,11.55),(8.725,11.55),(8.225,12.05),(8.225,12.5)])
 e.add('/+3V3',F,[(8.225,12.5),(9.025,13.3),(11.325,13.3),(11.725,12.9)])
 e.add('/+3V3',F,[(11.1625,10.35),(12.875,10.35),(13.2,10.675)])
 e.add('/+3V3',F,[(11.725,12.9),(11.725,11.65),(12.225,11.15),(12.725,11.15),(13.2,10.675)])
 e.add('/+3V3',F,[(13.2,10.675),(14.45,10.675),(15.9,9.225)])
 e.commit('3V3: align physical junctions, eliminate overlapping vertical tracks and connect U1.8 directly outward to C1')
elif kind=='rear':
 # Preserve the close USB-to-ESD branch; move onward CC1 routing to the right.
 e.remove(['022f29f3','184b911f','397c25af','43f93ba3','7dee163b','8844cffe','9367b063','9c8680a2','de885002','e2c65ffc','e5f08458'])
 e.add('/CC1',B,[(12,9.85),(12,9.05),(11.6,8.65)])
 e.via('/CC1',(11.6,8.65))
 e.add('/CC1',F,[(11.6,8.65),(15.65,8.65),(16.9,9.9),(16.9,19.2),(17.4,19.7),(19,19.7)])
 e.commit('CC1: compare right-side corridor against original left/bottom loop; retain USB ESD branch before onward path')
elif kind=='motion':
 # Move the CS pull-up to the existing straight corridor; its other pad uses the 3V3 plane.
 e.move('R13',(46,20.975),180)
 e.remove(net='/IMU_CS',predicate=lambda t:not isinstance(t,k.PCB_VIA)and t.GetLayer()==B and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>30)
 e.add('/IMU_CS',B,[(37.592,21.336),(46.464,21.336),(46.825,20.975),(58.160599,20.975),(59.943999,22.7584),(59.943999,24.485599),(60.452,24.9936)])
 # Existing 3V3 pad stub will be replaced by the new pad's plane landing.
 e.remove(net='/+3V3',predicate=lambda t:not isinstance(t,k.PCB_VIA)and min(xy(t.GetStart())[0],xy(t.GetEnd())[0])>43 and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<46 and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>19 and max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<21)
 e.commit('R13 placement trial: bring pull-up onto CS corridor to remove small roof-shaped detour')
 e.remove(['21e6e7ae','24ff1e78','724d16f5','7ea6594a','d091f7e7','d4cc7eb2','f73c82dd'])
 e.add('/CAM_3V3',B,[(41.725,12),(42.7298,13.0048),(51.206399,13.0048)])
 e.commit('CAM_3V3: eliminate small raise/lower jog between C7 and J5, preserve local U4 decoupling connection')
else:raise SystemExit(kind)
