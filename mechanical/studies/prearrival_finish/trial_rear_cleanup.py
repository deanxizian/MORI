"""Screen bounded numerical mesh repairs without editing the main assembly."""
import sys, json, collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
from export import topology
load_collections();assembled();bpy.context.view_layer.update()
s=Solid(bpy.data.objects[PREFIX+'Head_Rear']);rows=[]
for tol in [.00005,.0001,.0002,.0005,.001,.002,.005,.01]:
    m=s.m.set_tolerance(tol).simplify(tol)
    d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts)
    unique,inv=np.unique(v,axis=0,return_inverse=True);wf=inv[f]
    t=topology(unique,wf)
    rows.append(dict(tolerance_mm=tol,topology=t,volume_mm3=m.volume(),
                     removed_mm3=(s.m-m).volume(),added_mm3=(m-s.m).volume()))
    print(json.dumps(rows[-1]),flush=True)
    np.savez_compressed(HERE/('rear_trial_'+str(tol)+'.npz'),vertices=v,faces=f)
(HERE/'rear_cleanup_trials.json').write_text(json.dumps(rows,indent=2)+'\n')
