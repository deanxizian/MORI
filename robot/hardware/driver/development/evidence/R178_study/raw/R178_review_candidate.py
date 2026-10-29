"""Create source-bound metrics and native local geometry views for review."""
import importlib.util,json,math,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
rev=sys.argv[1];out=b/(rev+'-views');out.mkdir(exist_ok=False)
source=dev/'native/MORI_Interface_C3.kicad_pcb';board=b/rev/'MORI_Interface_C3.kicad_pcb'
s=importlib.util.spec_from_file_location('render',b/'R152_render_highlight.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for ly in LAYERS:m.render(str(board),ly,(.3,18,9,26),str(out/(ly+'.svg')),'/FAULT_N')
for pre,path in [('source',source),('new',board)]:
    m.render(str(path),'B.Cu',(23,5.5,29,11.5),str(out/(pre+'-old-position-B.svg')),'/CLR_N')
m.render(str(source),'F.Cu',(.3,18,9,26),str(out/'source-F.Cu.svg'),'/FAULT_N')
a=Copper(str(source));c=Copper(str(board));plan=json.loads((b/(rev+'-plan.json')).read_text())
assert a.sha==plan['board_sha256']
ag=a.pad_groups();cg=c.pad_groups()
def pose(c):
    f=next(f for f in c.footprints if f.GetReference()=='D302')
    return dict(face=c.board.GetLayerName(f.GetLayer()),position_mm=xy(f.GetPosition()),rotation_deg=f.GetOrientationDegrees(),
                pads={p.GetNumber():dict(net=p.GetNetname(),position_mm=xy(p.GetPosition())) for p in f.Pads()})
new_by_net={n:unary_union([c.shapes[uid(t),'F.Cu'] for t in c.segments if uid(t) not in a.by_id and t.GetNetname()==n]) for n in ['/CLR_N','/FAULT_N']}
gnd=c.copper['GND','In1.Cu'].union(c.copper['GND','In4.Cu'])
coupling=[]
for n,stroke in new_by_net.items():
    for (other,ly),g in c.copper.items():
        if ly!='B.Cu' or other in ['GND',n]:continue
        ov=stroke.intersection(g)
        if ov.area>1e-8:coupling.append(dict(new_net=n,opposite_net=other,overlap_mm2=ov.area,unshielded_by_both_mm2=ov.difference(gnd).area))
r=dict(source_sha256=a.sha,board_sha256=c.sha,
       counts=dict(segments=len(c.segments),vias=len(c.vias),footprints=len(c.footprints),new_segments=len([t for t in c.segments if uid(t) not in a.by_id]),removed_segments=len(plan['delete_copper'])),
       routes=[dict(net=x['net'],layer=x['layer'],length_mm=sum(math.dist(p,q) for p,q in zip(x['points_mm'],x['points_mm'][1:])),points_mm=x['points_mm']) for x in plan['routes']],
       group_count_changes=[dict(net=n,before=len(ag[n]),after=len(cg[n])) for n in ag if len(ag[n])!=len(cg[n])],
       D302_old=pose(a),D302_new=pose(c),remaining_FAULT_groups=cg['/FAULT_N'],
       opposite_foreign_copper_projections=coupling,manufacturing_release=False,physical='NOT_TESTED')
(b/(rev+'-metrics.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
