"""Current-main sections of the unresolved reaction-link assembly interface."""
from pathlib import Path
import sys,json,hashlib,argparse
HERE=Path(__file__).resolve().parent;M=HERE.parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',default='reaction_service_sections.json')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
sys.path.insert(0,str(M/'scripts'))
from common import *
from validate import Solid
from validate_head_retention import hit
from interface_completion import axial
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
bolt=ss['Yaw_Reaction_Clamp_Screw'];c=(bolt.lo+bolt.hi)/2
start=np.array([c[0],bolt.hi[1]+.05,c[2]])
tool=axial(1.25,30,start+[0,15,0],[0,1,0])
fixed=ss['Pitch_Yoke'].m
link=ss['Yaw_Reaction_Link'].m
tr=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float)
rows=[]
specs=[('clamp_tool',7,{'yoke':fixed,'link':link,'screw':bolt.m,'tool':tool,'intersection':fixed^tool}),
       ('straight_entry',0,{'yoke':fixed,'link':link.translate((0,0,2)),'intersection':fixed^link.translate((0,0,2))})]
for label,x,parts in specs:
 rows.append(dict(id=label,x_mm=x,layers={n:[p.tolist() for p in m.transform(tr).slice(x).to_polygons()] for n,m in parts.items()}))
out=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
 sections=rows,tool_intersection_mm3=hit(tool,fixed),straight_lift_2mm_intersection_mm3=hit(link.translate((0,0,2)),fixed),
 scope=P['revision']+' current-main local sections; no geometry edits, two explicit failed approaches only',
 limits=['2.5x30mm tool is a provisional allocation','Sections show specific failed approaches, not proof all possible routes fail','SCS0009 matching horn/shaft design remains pending'])
(HERE/args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('REACTION_SECTIONS',out['tool_intersection_mm3'],out['straight_lift_2mm_intersection_mm3'],flush=True)
