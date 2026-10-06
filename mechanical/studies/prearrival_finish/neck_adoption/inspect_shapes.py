import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
from common import *
from validate import Solid
from neck_reference import approved
from export import topology
load_collections();assembled();bpy.context.view_layer.update()
for n in P['neck_harness_capacity']['changed_existing_ids']:
 s=Solid(bpy.data.objects[PREFIX+n]);a=approved(n);b=s.m;t=topology(s.v,s.f.tolist())
 print(n,{'plus':(b-a).volume(),'minus':(a-b).volume(),'components':len(b.decompose()),'topology':t},flush=True)
