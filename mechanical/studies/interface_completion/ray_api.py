import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();bpy.context.view_layer.update()
s=Solid(bpy.data.objects[PREFIX+'Pitch_Cradle']);q=s.m.ray_cast([-16.3,-25,218.7],[-16.3,-25,230]);print([(dir(x),x) for x in q][:1]);print([[getattr(x,k) for k in ['distance','position','normal','face_id'] if hasattr(x,k)] for x in q])
