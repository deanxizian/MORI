"""Read-only locations for current-main retention work; no old script execution."""
from pathlib import Path
import sys, json
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context, np, sha
from mathutils import Vector
ctx=Context()
result=ctx.evidence()
result['selected_parts']={n:dict(group=s.group,low_mm=s.lo.tolist(),high_mm=s.hi.tolist())
 for n,s in ctx.ss.items() if n in ['Load_Frame','Yaw_Base','Pitch_Yoke','Pitch_Cradle','MCU_Carrier','MCU_Motion','Yaw_Reaction_Link'] or 'CAM' in n}
pins=ctx.port_pins['motion_J5']['pins']
result['body_J5_pins']={n:p.tolist() for n,p in pins.items()}
points={f'J5_{n}':p+[0,0,2.5] for n,p in pins.items()}
result['nearest_hosts']={name:sorted([dict(part=n,distance_mm=float(s['tree'].find_nearest(Vector(p))[3]),
 point_mm=list(s['tree'].find_nearest(Vector(p))[0])) for n,s in ctx.targets.items()
 if n in ['Load_Frame','Yaw_Base','Pitch_Yoke']], key=lambda r:r['distance_mm']) for name,p in points.items()}
result['script_sha256']=sha(__file__)
ctx.assert_unchanged()
(HERE/'retention_inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['selected_parts','body_J5_pins','nearest_hosts']},indent=2),flush=True)
