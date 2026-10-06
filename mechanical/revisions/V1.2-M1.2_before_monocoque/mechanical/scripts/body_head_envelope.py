"""Additional all-head-poses x +/-15 deg body-tilt envelope; extent sampling, not control certification."""
import sys,math,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
start=time.time(); groups={g:[] for g in ['body','yaw','pitch']}
for o in parts():
 if o.get('group')=='dock':continue
 g=o.get('group');g=g if g in ['yaw','pitch'] else 'body';groups[g].extend([tuple(v) for v in vertices_world(o)])
groups={k:np.array(v,dtype=float) for k,v in groups.items()};hz=D['head_z'];wz=D['wheel_z'];lo=np.array([1e9]*3);hi=-lo.copy();head0=np.array([0,0,hz]);axle0=np.array([0,0,wz])
for t in range(-15,16):
 rx=np.array(Matrix.Rotation(math.radians(-t),3,'X'));body=(groups['body']-axle0)@rx.T+axle0;lo=np.minimum(lo,body.min(axis=0));hi=np.maximum(hi,body.max(axis=0))
 for y in range(-60,61,10):
  rz=np.array(Matrix.Rotation(math.radians(y),3,'Z'))
  for p in range(-20,26,5):
   rp=np.array(Matrix.Rotation(math.radians(p),3,'X'));yw=(groups['yaw']-head0)@rz.T+head0;pt=(groups['pitch']-head0)@(rz@rp).T+head0
   h=(np.vstack((yw,pt))-axle0)@rx.T+axle0;lo=np.minimum(lo,h.min(axis=0));hi=np.maximum(hi,h.max(axis=0))
save_json(ROOT/'reports/body_head_envelope.json',{'status':'PASS','purpose':'Sampled extent report, not collision proof and not a safe control angle','poses':31*13*10,'body_forward_tilt_deg':[-15,15],'body_step_deg':1,'yaw_deg':[-60,60],'yaw_step_deg':10,'pitch_deg':[-20,25],'pitch_step_deg':5,'bbox_xyz_mm':list(zip(lo.tolist(),hi.tolist())),'size_xyz_mm':(hi-lo).tolist(),'elapsed_s':round(time.time()-start,1)})
print('BODY_HEAD_ENVELOPE_COMPLETE',flush=True)
