"""Route reserved load paths before low-current controls. Inspect native DRC after routing."""
import pcbnew as k
import json,sys
from layout_P3 import paths,xy,F,B
from route_local_P2 import connect
name,d,pcb,r=paths('power');b=k.LoadBoard(str(pcb));fps={f.GetReference():f for f in b.GetFootprints()}
def p(ref,n):return next(p for p in fps[ref].Pads() if p.GetNumber()==str(n))
def coord(spec):return xy(p(*spec).GetPosition()) if isinstance(spec[0],str) else spec
jobs=[
 ('BAT_IN',(8.925,14.365),('J1',2),[B],[F,B],2),
 ('BAT_REV',(17.075,14.365),('R2',1),[B],[B],2),
 ('BAT_MON',('R2',2),('J2',2),[B],[F,B],2),
 ('BAT_MON',('J2',2),('J4',2),[F,B],[F,B],2),
 ('BAT_MON',('J2',2),('F60',1),[F,B],[F],1),
 ('BAT_MON',('F60',1),('F70',1),[F],[F],1),
 ('BAT_MON',('F70',1),('J6',2),[F],[F,B],2),
 ('W9_IN',('J3',2),('D10',2),[F,B],[B],1.5),
 ('W_PRE',('D10',1),(43.635,26.275),[B],[B],1.5),
 ('W_VM',(43.635,17.725),('C10',1),[B],[F,B],1.5),
 ('W_VM',('C10',1),('J7',2),[F,B],[F,B],1.5),
 ('W_VM',('J7',2),('J8',2),[F,B],[F,B],1.5),
 ('W_VM',('J7',2),('J11',2),[F,B],[F,B],1.5),
 ('H6_IN',('J5',2),('D30',2),[F,B],[B],1),
 ('H_PRE',('D30',1),(32.825,35.135),[B],[B],1),
 ('H_VM',(40.175,35.135),('C30',1),[B],[F,B],1),
 ('H_VM',('C30',1),('J9',2),[F,B],[F,B],1),
 ('H_VM',('J9',2),('J12',2),[F,B],[F,B],1),
 ('M5_VIN',('F60',2),('C60',1),[F],[F],.8),
 ('M5_VIN',('C60',1),('C66',1),[F],[F],.8),
 ('C5_VIN',('F70',2),('C70',1),[F],[F],.8),
 ('C5_VIN',('C70',1),('C76',1),[F],[F],.8),
 ('+5V_MOTION',('L60',2),('J17',1),[F],[F],.8),
 ('+5V_CAM',('L70',2),('J18',1),[F],[F,B],.8),
]
log=[]
for i,(net,a,z,al,zl,w) in enumerate(jobs):
 try:
  result=connect(b,'/'+net,coord(a),coord(z),al,zl,(80,55),step=.1,width=w,vd=1,dr=.45);result.update(index=i,width_mm=w,status='ROUTED');log.append(result);k.SaveBoard(str(pcb),b)
 except RuntimeError as exc:log.append(dict(index=i,net=net,width_mm=w,status='BLOCKED',reason=str(exc)));print('BLOCKED',i,str(exc),flush=True)
 (r/'power_trunks.json').write_text(json.dumps(log,indent=2)+'\n')
