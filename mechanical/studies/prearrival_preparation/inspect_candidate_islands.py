import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled();m=Solid(bpy.data.objects[PREFIX+'Pitch_Yoke']).m
for c in m.decompose():print(c.volume(),c.bounding_box(),flush=True)
