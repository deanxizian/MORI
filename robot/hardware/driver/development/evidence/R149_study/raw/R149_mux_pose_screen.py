"""Compare small U1001 translations and rotations against actual copper and courtyards; proposals only."""
import ast, json, sys
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R149-mux-poses.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
f=next(f for f in c.footprints if f.GetReference()=='U1001');origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees();pads=list(f.Pads());mine={uid(p) for p in pads};court=polyset(f.GetCourtyard(pcb.B_CrtYd));body=fab(f)
rows=[]
for dx,dy,angle in [(0,y,90) for y in [0,.15,.25,.3,.35,.4,.5,.6]]+[(0,0,x) for x in [0,180,270]]:
    tr=lambda g:translate(rotate(g,-(angle-angle0),origin=origin),xoff=dx,yoff=dy)
    courthits=[o.GetReference() for o in c.footprints if o!=f and o.GetLayer()==pcb.B_Cu and tr(court).intersection(polyset(o.GetCourtyard(pcb.B_CrtYd))).area>1e-7]
    spacing=[]; retained=[]
    for p in pads:
        g=tr(c.shapes[uid(p),'B.Cu'])
        for (u,ly),s in c.shapes.items():
            if ly!='B.Cu' or u in mine:continue
            o=c.by_id[u]
            if (o.GetNetname()!=p.GetNetname() or isinstance(o,pcb.PCB_VIA)) and g.distance(s)<.199999:
                spacing.append(dict(pad=c.pad_name(p),other=u,other_type=type(o).__name__,other_net=o.GetNetname(),distance_mm=g.distance(s)))
        old_contacts=[uid(t) for t in c.segments if t.GetLayer()==pcb.B_Cu and t.GetNetname()==p.GetNetname() and c.shapes[uid(p),'B.Cu'].intersects(c.shapes[uid(t),'B.Cu'])]
        retained.append(dict(pad=c.pad_name(p),old_trace_contacts=len(old_contacts),remaining=sum(g.intersects(c.shapes[u,'B.Cu']) for u in old_contacts)))
    old_lands=unary_union([c.shapes[uid(p),'B.Cu'] for p in pads]);new_lands=unary_union([tr(c.shapes[uid(p),'B.Cu']) for p in pads]);bg=tr(body)
    bodyhits=[dict(uuid=uid(t),net=t.GetNetname(),area_mm2=c.shapes[uid(t),'B.Cu'].intersection(bg).difference(new_lands).area) for t in c.segments if t.GetLayer()==pcb.B_Cu and c.shapes[uid(t),'B.Cu'].intersection(bg).difference(new_lands).area>1e-6 and c.shapes[uid(t),'B.Cu'].intersection(body).difference(old_lands).area<=1e-6]
    rows.append(dict(delta_mm=[dx,dy],angle_deg=angle,courtyard_hits=courthits,pad_spacing_hits=spacing,lost_all_old_trace_contacts=[r for r in retained if r['old_trace_contacts'] and not r['remaining']],new_body_hits=bodyhits))
data=dict(scope=__doc__,source_sha256=c.sha,rows=rows);out.write_text(json.dumps(data,indent=2)+'\n')
for r in rows:print(json.dumps(dict(delta=r['delta_mm'],angle=r['angle_deg'],courts=r['courtyard_hits'],spacing=len(r['pad_spacing_hits']),lost=r['lost_all_old_trace_contacts'],body=r['new_body_hits'])))
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
