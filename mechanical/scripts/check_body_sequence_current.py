"""Current native shell-module translation checks for the assembly presentation.

No historical fingerprints are promoted to fresh checks. Separate mating plugs,
flexible cables, tooling and human support are outside this test's scope.
"""
from pathlib import Path
import sys,hashlib,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
start=time.time();bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for name in ['DATUMS','DOCK','KEEP_OUT','COUPONS']:COLS[name].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
modules={
    'front':['Body_Front','Frame_Insert_0','Frame_Insert_1','Speaker','Speaker_Gasket',
             'Speaker_Insert_-1','Speaker_Insert_1','Speaker_Screw_-1','Speaker_Screw_1'],
    'rear':['Body_Rear','Frame_Insert_2','Frame_Insert_3','Power_Switch',
            'Rear_Interface_Insert_0','Rear_Interface_Insert_1','Rear_Interface_PCB',
            'Rear_Interface_Screw_0','Rear_Interface_Screw_1','USB_Receptacle']}
paths=[]
for side,direction in [('front',1),('rear',-1)]:
    names=set(modules[side]);assert names<=set(ss)
    fixed={n:s for n,s in ss.items() if n not in names and not n.startswith('Frame_Screw_')}
    hits=[];checks=0
    for distance in np.linspace(0,220,275):
        shift=np.array([0,direction*distance,0])
        for name in names:
            a=ss[name];lo=a.lo+shift;hi=a.hi+shift
            candidates={n:b for n,b in fixed.items() if np.all(hi>=b.lo-1e-5) and np.all(b.hi>=lo-1e-5)}
            if not candidates:continue
            moved=a.m.translate(shift)
            for target,b in candidates.items():
                checks+=1;volume=(moved^b.m).volume()
                if volume>P['validation']['collision_volume_tolerance_mm3']:
                    hits.append(dict(moving=name,target=target,distance_mm=float(distance),volume_mm3=volume))
        if len(hits)>10:break
    paths.append(dict(module=side,positions=275,travel_mm=220,wheels='present',opposite_shell='closed',
        native_solid_checks=checks,status='FAIL' if hits else 'PASS',hits=hits))
    print('CURRENT_BODY_MODULE',side,checks,hits[:2],flush=True)
report=dict(status='FAIL' if any(r['status']=='FAIL' for r in paths) else 'PASS',revision=P['revision'],
    source_blend_sha256=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),
    scope='Native rigid parts only, 275 sampled translations per shell module; frame screws installed later. No mating-allocation, flexible-wire, human/tool or continuous-sweep qualification.',
    modules=modules,paths=paths,mating_plugs='NOT_TESTED',complete_wired_assembly='BLOCKED',
    frame_tool_access='NOT_TESTED_THIS_RUN',physical_fit='NOT_TESTED',manufacturing_release=False,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),elapsed_s=time.time()-start)
save_json(ROOT/'reports/body_split_validation.json',report)
if report['status']!='PASS':raise RuntimeError('Native body module path failed')
