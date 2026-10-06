import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate import Solid
load_collections();assembled()
a=Solid(bpy.data.objects[PREFIX+'Pitch_Yoke'])
for m in a.m.decompose():
 if m.volume()>0: print('COMPONENT',round(m.volume(),3),m.bounding_box())
