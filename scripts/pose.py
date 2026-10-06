"""CLI: blender model.blend --python pose.py -- --state assembled|exploded --yaw 30
Interactive: edit CONTROLS / Head_Pivot custom yaw_deg, Wheel_*_Pivot spin_deg.
"""
import sys, argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser(); p.add_argument('--state',choices=['assembled','exploded'],default='assembled'); p.add_argument('--yaw',type=float,default=0); p.add_argument('--save',action='store_true')
a=p.parse_args(args)
bpy.context.window.scene=bpy.data.scenes['MORI_Assembly']; assembled()
if abs(a.yaw)>P['head_yaw_limit_deg']: raise ValueError('Yaw exceeds configured study limit')
bpy.context.scene.frame_set(80 if a.state=='exploded' else 1)
o=bpy.data.objects[PREFIX+'Head_Pivot']; o['yaw_deg']=a.yaw; o.update_tag(); bpy.context.view_layer.update()
if a.save: bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/MORI_assembly.blend'))
