import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from common import *
from validate_head_cleanup import geometry_record
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for c in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[c].hide_viewport=False
bpy.context.view_layer.update()
save_json(Path(__file__).parent/'baseline_geometry.json',{'revision':P['revision'],'parts':{o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}})
print('WAVESHARE_BASELINE_SAVED')
