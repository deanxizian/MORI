"""Read-only whole-layout fit trial with replacement PCB models. No master save."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid,intersect_volume
from native_electronics import apply_native_electronics,E

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled()
for key,col in [('pcb',(.04,.3,.15)),('keepout',(.8,.3,.02))]:material(key,col)
apply_native_electronics();bpy.context.view_layer.update()
targets={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon'] and o.get('role')=='part'}
names=[v['object'] for v in E['boards'].values()]+['Power_Switch','USB_Receptacle']+list(E['modules'])
hits=[]
for n in names:
    for k,b in targets.items():
        if k==n or (k in names and names.index(k)<names.index(n)):continue
        v=intersect_volume(targets[n],b)
        if v>.02:hits.append({'board':n,'obstacle':k,'intersection_mm3':round(v,4)})
save_json(ROOT/'reports/native_electronics_trial.json',{'hits':hits,'source_revision':P['revision'],'scope':'Initial full-size source geometry; collisions are NOT waived and no master saved.'})
print('HITS',len(hits));print(json.dumps(hits,ensure_ascii=False,indent=2))
if '--save-study' in sys.argv:
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'studies/native_electronics_initial.blend'))
